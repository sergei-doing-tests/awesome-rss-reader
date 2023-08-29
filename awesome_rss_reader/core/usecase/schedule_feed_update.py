from dataclasses import dataclass
from datetime import timedelta

import structlog

from awesome_rss_reader.application.settings import ApplicationSettings
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobFiltering,
    FeedRefreshJobOrdering,
    FeedRefreshJobState,
)
from awesome_rss_reader.core.repository.feed_refresh_job import FeedRefreshJobRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase
from awesome_rss_reader.utils.dtime import now_aware

logger = structlog.get_logger()


@dataclass
class ScheduleFeedUpdateInput:
    batch_size: int


@dataclass
class ScheduleFeedUpdateUseCase(BaseUseCase):
    app_settings: ApplicationSettings
    job_repository: FeedRefreshJobRepository

    async def execute(self, data: ScheduleFeedUpdateInput) -> None:
        jobs_to_schedule = await self._get_jobs_to_schedule(
            threshold=self.app_settings.feed_update_frequency_s,
            batch_size=data.batch_size,
        )
        if not jobs_to_schedule:
            logger.info("No jobs to schedule")
            return

        scheduled_jobs = await self._schedule_jobs(jobs_to_schedule)
        if not scheduled_jobs:
            logger.warning("No jobs were scheduled")
            return

    async def _get_jobs_to_schedule(
        self,
        *,
        threshold: int,
        batch_size: int,
    ) -> list[FeedRefreshJob]:
        state_changed_before = now_aware() - timedelta(seconds=threshold)
        return await self.job_repository.get_list(
            filter_by=FeedRefreshJobFiltering(
                state=FeedRefreshJobState.complete,
                state_changed_before=state_changed_before,
            ),
            # give priority to the jobs completed the longest time ago
            order_by=FeedRefreshJobOrdering.state_changed_at_asc,
            offset=0,
            limit=batch_size,
        )

    async def _schedule_jobs(self, jobs_to_schedule: list[FeedRefreshJob]) -> list[FeedRefreshJob]:
        logger.info("Scheduling jobs", count=len(jobs_to_schedule))

        scheduled_jobs = await self.job_repository.transit_state_batch(
            job_ids=[job.id for job in jobs_to_schedule],
            old_state=FeedRefreshJobState.complete,
            new_state=FeedRefreshJobState.pending,
        )

        if len(scheduled_jobs) != len(jobs_to_schedule):
            logger.warning(
                "Some jobs were not scheduled",
                total=len(jobs_to_schedule),
                count=len(jobs_to_schedule) - len(scheduled_jobs),
            )

        return scheduled_jobs
