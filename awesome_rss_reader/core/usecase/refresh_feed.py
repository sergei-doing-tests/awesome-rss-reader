from dataclasses import dataclass

import structlog

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import feed_refresh_job as job_repo
from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.core.usecase.base import BaseUseCase
from awesome_rss_reader.utils.dtime import now_aware

logger = structlog.get_logger()


@dataclass
class RefreshFeedInput:
    feed_id: int


@dataclass
class RefreshFeedOutput:
    refresh_job: FeedRefreshJob


class FeedNotFoundError(Exception):
    ...


@dataclass
class RefreshFeedUseCase(BaseUseCase):
    feed_repository: feed_repo.FeedRepository
    job_repository: job_repo.FeedRefreshJobRepository
    atomic: AtomicProvider

    async def execute(self, data: RefreshFeedInput) -> RefreshFeedOutput:
        feed = await self._get_feed(data.feed_id)

        async with self.atomic.transaction():
            refresh_job = await self._refresh_feed(feed.id)

        return RefreshFeedOutput(refresh_job=refresh_job)

    async def _get_feed(self, feed_id: int) -> Feed:
        try:
            return await self.feed_repository.get_by_id(feed_id)
        except feed_repo.FeedNotFoundError:
            logger.info("Requested feed to unfollow not found", feed_id=feed_id)
            raise FeedNotFoundError(f"Feed with {feed_id=} not found in repository")

    async def _refresh_feed(self, feed_id: int) -> FeedRefreshJob:
        new_refresh_job = NewFeedRefreshJob(feed_id=feed_id)
        refresh_job = await self.job_repository.get_or_create(new_refresh_job)

        # Don't trigger a job refresh if it's already in progress
        if refresh_job.state in {FeedRefreshJobState.pending, FeedRefreshJobState.in_progress}:
            return refresh_job

        try:
            await self.job_repository.transit_state(
                job_id=refresh_job.id,
                old_state=refresh_job.state,
                new_state=FeedRefreshJobState.pending,
            )
        except job_repo.RefreshJobStateTransitionError:
            # fmt: off
            logger.info(
                "Feed refresh job is already in progress",
                feed_id=feed_id, job_id=refresh_job.id, job_state=refresh_job.state,
            )
            # fmt: on
            return refresh_job

        return await self.job_repository.update(
            job_id=refresh_job.id,
            updates=FeedRefreshJobUpdates(
                retries=0,
                execute_after=now_aware(),
            ),
        )
