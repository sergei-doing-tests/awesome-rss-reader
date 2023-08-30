import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from awesome_rss_reader.application.settings import ApplicationSettings
from awesome_rss_reader.core.entity.feed import Feed, FeedFiltering, FeedUpdates
from awesome_rss_reader.core.entity.feed_content import (
    FeedContentBatchRequest,
    FeedContentRequest,
    FeedContentResult,
)
from awesome_rss_reader.core.entity.feed_post import NewFeedPost
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobFiltering,
    FeedRefreshJobOrdering,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
)
from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.core.repository.feed_content import FeedContentRepository
from awesome_rss_reader.core.repository.feed_post import FeedPostRepository
from awesome_rss_reader.core.repository.feed_refresh_job import FeedRefreshJobRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase
from awesome_rss_reader.utils.dtime import now_aware

logger = structlog.get_logger()


@dataclass
class _FetchResult:
    job: FeedRefreshJob
    result: FeedContentResult | None = None
    error: Exception | None = None


@dataclass
class UpdateFeedContentInput:
    batch_size: int


@dataclass
class UpdateFeedContentUseCase(BaseUseCase):
    app_settings: ApplicationSettings
    job_repository: FeedRefreshJobRepository
    feed_repository: FeedRepository
    feed_content_repository: FeedContentRepository
    post_repository: FeedPostRepository
    atomic: AtomicProvider

    async def execute(self, data: UpdateFeedContentInput) -> None:
        jobs_to_process = await self._get_available_jobs(batch_size=data.batch_size)
        if not jobs_to_process:
            logger.info("No jobs to process")
            return

        received_jobs = await self._receive_jobs(jobs_to_process)
        if not received_jobs:
            logger.warning("No jobs were received")
            return

        await self._process_received_jobs(received_jobs)

    async def _get_available_jobs(self, *, batch_size: int) -> list[FeedRefreshJob]:
        return await self.job_repository.get_list(
            filter_by=FeedRefreshJobFiltering(
                state=FeedRefreshJobState.pending,
                execute_before=now_aware(),
            ),
            order_by=FeedRefreshJobOrdering.state_changed_at_asc,
            offset=0,
            limit=batch_size,
        )

    async def _receive_jobs(self, available_jobs: list[FeedRefreshJob]) -> list[FeedRefreshJob]:
        logger.info("Receiving jobs", count=len(available_jobs))

        received_jobs = await self.job_repository.transit_state_batch(
            job_ids=[job.id for job in available_jobs],
            old_state=FeedRefreshJobState.pending,
            new_state=FeedRefreshJobState.in_progress,
        )

        if len(received_jobs) != len(available_jobs):
            logger.warning(
                "Some jobs were not received",
                total=len(available_jobs),
                count=len(available_jobs) - len(received_jobs),
            )

        return received_jobs

    async def _get_feeds(self, feed_ids: list[int]) -> list[Feed]:
        return await self.feed_repository.get_list(
            filter_by=FeedFiltering(
                feed_ids=feed_ids,
            ),
            limit=len(feed_ids),
            offset=0,
        )

    async def _process_received_jobs(self, jobs: list[FeedRefreshJob]) -> None:
        logger.info("Processing jobs", count=len(jobs))

        fetch_results = await self._fetch_content_for_jobs(jobs)
        process_result_tasks = []

        for fr in fetch_results:
            if fr.error is not None:
                process_result_tasks.append(self._process_job_exception(exc=fr.error, job=fr.job))
            elif fr.result is not None:
                process_result_tasks.append(self._process_job_result(result=fr.result, job=fr.job))

        maybe_errors = await asyncio.gather(*process_result_tasks, return_exceptions=True)
        # log unhandled exceptions that occurred in the gather call
        for maybe_err in maybe_errors:
            if not isinstance(maybe_err, Exception):
                continue
            logger.error("Failed to process job result", error=maybe_err)

    async def _fetch_content_for_jobs(self, jobs: list[FeedRefreshJob]) -> list[_FetchResult]:
        # fmt: off
        job_per_feed_id = {
            job.feed_id: job for job in jobs
        }
        job_per_request_id = {
            uuid.uuid4(): job for job in jobs
        }
        request_id_per_job_id = {
            job.id: request_id
            for request_id, job in job_per_request_id.items()
        }
        # fmt: on

        feeds = await self._get_feeds(feed_ids=list(job_per_feed_id))

        requests = [
            FeedContentRequest(
                request_id=request_id_per_job_id[job_per_feed_id[feed.id].id],
                url=feed.url,
                published_since=feed.published_at,
            )
            for feed in feeds
        ]

        request = FeedContentBatchRequest(
            timeout_s=self.app_settings.feed_update_fetch_timeout_s,
            max_body_size_b=self.app_settings.feed_max_size_b,
            requests=requests,
        )
        response = await self.feed_content_repository.fetch_many(request)

        fetch_results = []

        for request_id, result in response.results.items():
            job = job_per_request_id[request_id]
            fetch_results.append(_FetchResult(job=job, result=result))

        for request_id, exception in response.errors.items():
            job = job_per_request_id[request_id]
            fetch_results.append(_FetchResult(job=job, error=exception))

        return fetch_results

    async def _process_job_result(self, *, result: FeedContentResult, job: FeedRefreshJob) -> None:
        logger.info("Update feed content job succeeded", feed=job.feed_id, job=job.id)

        async with self.atomic.transaction():
            await self.job_repository.transit_state(
                job_id=job.id,
                old_state=job.state,
                new_state=FeedRefreshJobState.complete,
            )
            await self.job_repository.update(
                job_id=job.id,
                updates=FeedRefreshJobUpdates(
                    retries=0,
                ),
            )

            if not result.items:
                logger.info("Feed has no new content", feed=job.feed_id, job=job.id)
                return

            await self.feed_repository.update(
                feed_id=job.feed_id,
                updates=FeedUpdates(
                    title=result.title,
                    published_at=result.published_at,
                ),
            )

            new_posts = [
                NewFeedPost(
                    feed_id=job.feed_id,
                    title=feed_item.title,
                    summary=feed_item.summary,
                    url=str(feed_item.url),
                    guid=feed_item.guid,
                    published_at=feed_item.published_at,
                )
                for feed_item in result.items
            ]
            posts = await self.post_repository.create_many(new_posts)

        # fmt: off
        logger.info(
            "Feed content updated",
            feed_id=job.feed_id, job_id=job.id, new_posts=len(posts),
        )
        # fmt: on

    async def _process_job_exception(self, *, exc: Exception, job: FeedRefreshJob) -> None:
        logger.warning("Feed content update failed", error=exc, feed_id=job.feed_id, job_id=job.id)

        # calculate backoff for the next retry
        try:
            backoff_m = self.app_settings.feed_update_retry_delay_m[job.retries]
        # ran out of retries, have to mark the job as failed
        except IndexError:
            # fmt: off
            logger.warning(
                "Update feed content job has no more retries available",
                feed_id=job.feed_id, job_id=job.id, retries=job.retries,
            )
            # fmt: on
            await self._mark_job_failed(job=job)
        # otherwise, schedule a retry
        else:
            await self._schedule_job_for_retry(
                job=job,
                new_execute_after=now_aware() + timedelta(minutes=backoff_m),
                new_retries=job.retries + 1,
            )

    async def _mark_job_failed(self, job: FeedRefreshJob) -> None:
        """Mark a job as failed, so it won't be retried anymore until manually reset."""
        await self.job_repository.transit_state(
            job_id=job.id,
            old_state=job.state,
            new_state=FeedRefreshJobState.failed,
        )
        # fmt: off
        logger.info(
            "Marked job as failed",
            feed_id=job.feed_id, job_id=job.id, retries=job.retries,
        )
        # fmt: on

    async def _schedule_job_for_retry(
        self,
        job: FeedRefreshJob,
        new_execute_after: datetime,
        new_retries: int,
    ) -> None:
        """
        Reschedule a job to be retried at another time.
        """
        async with self.atomic.transaction():
            job = await self.job_repository.transit_state(
                job_id=job.id,
                old_state=job.state,
                new_state=FeedRefreshJobState.pending,
            )
            await self.job_repository.update(
                job_id=job.id,
                updates=FeedRefreshJobUpdates(
                    retries=new_retries,
                    execute_after=new_execute_after,
                ),
            )

        # fmt: off
        logger.info(
            "Feed update job scheduled for retry",
            feed_id=job.feed_id, job_id=job.id, after=new_execute_after, retries=new_retries,
        )
        # fmt: on
