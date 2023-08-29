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
class UpdateFeedContentInput:
    batch_size: int


@dataclass
class UpdateFeedContentUseCase(BaseUseCase):
    app_settings: ApplicationSettings
    job_repository: FeedRefreshJobRepository
    feed_repository: FeedRepository
    content_repository: FeedContentRepository
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

        await self._process_jobs(received_jobs)

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
                ids=feed_ids,
            ),
            limit=len(feed_ids),
            offset=0,
        )

    async def _process_jobs(self, jobs: list[FeedRefreshJob]) -> None:
        job_per_feed_id = {job.feed_id: job for job in jobs}
        feeds = await self._get_feeds(feed_ids=list(job_per_feed_id))

        feed_per_request_id = {uuid.uuid4(): feed for feed in feeds}
        requests = {
            request_id: FeedContentRequest(
                url=feed.url,
                published_since=feed.published_at,
            )
            for request_id, feed in feed_per_request_id.items()
        }

        batch_request = FeedContentBatchRequest(
            timeout=self.app_settings.feed_update_fetch_timeout_s,
            requests=requests,
        )
        batch_result = await self.content_repository.fetch_many(batch_request)

        coros = []
        # handle successful results
        for request_id, result in batch_result.results.items():
            feed = feed_per_request_id[request_id]
            job = job_per_feed_id[feed.id]
            coros.append(self._handle_job_success(result=result, feed=feed, job=job))

        # handle errors
        for request_id, error in batch_result.errors.items():
            feed = feed_per_request_id[request_id]
            job = job_per_feed_id[feed.id]
            coros.append(self._handle_job_error(error=error, job=job))

        await asyncio.gather(*coros)

    async def _handle_job_success(
        self,
        *,
        result: FeedContentResult,
        feed: Feed,
        job: FeedRefreshJob,
    ) -> None:
        logger.info("Update feed content job succeeded", feed=job.feed_id, job=job.id)

        async with self.atomic.transaction():
            await self.job_repository.transit_state(
                job_id=job.id,
                old_state=job.state,
                new_state=FeedRefreshJobState.complete,
            )

            if not result.items:
                # fmt: off
                logger.info("Feed has no new content", feed=job.feed_id, job=job.id)
                # fmt: on
                return

            await self.feed_repository.update(
                feed_id=feed.id,
                updates=FeedUpdates(
                    title=result.title,
                    published_at=result.published_at,
                ),
            )

            new_posts = [
                NewFeedPost(
                    feed_id=feed.id,
                    title=feed_item.title,
                    summary=feed_item.summary,
                    url=feed_item.url,
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

    async def _handle_job_error(
        self,
        *,
        error: Exception,
        job: FeedRefreshJob,
    ) -> None:
        # fmt: off
        logger.warning(
            "Feed content update failed",
            error=error, feed_id=job.feed_id, job_id=job.id,
        )
        # fmt: on

        # calculate backoff for the next retry
        try:
            backoff_m = self.app_settings.feed_update_retry_delay_m[job.retries]
        except IndexError:
            # fmt: off
            logger.warning(
                "Update feed content job has no more retries available",
                feed_id=job.feed_id, job_id=job.id, retries=job.retries,
            )
            # fmt: on
            await self._fail_job(job=job)
        # otherwise, schedule a retry
        else:
            new_execute_after = now_aware() + timedelta(minutes=backoff_m)
            await self._reschedule_job(
                job=job, new_execute_after=new_execute_after, new_retries=job.retries + 1
            )

    async def _fail_job(self, job: FeedRefreshJob) -> None:
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

    async def _reschedule_job(
        self,
        job: FeedRefreshJob,
        new_execute_after: datetime,
        new_retries: int,
    ) -> None:
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
