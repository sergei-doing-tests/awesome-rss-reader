from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.repository.feed_refresh_job import FeedRefreshJobRepository
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository
from awesome_rss_reader.utils.dtime import now_aware


class PostgresFeedRefreshJobRepository(BasePostgresRepository, FeedRefreshJobRepository):
    async def get_or_create(self, new_job: NewFeedRefreshJob) -> FeedRefreshJob:
        return FeedRefreshJob(
            id=1,
            feed_id=1,
            state=FeedRefreshJobState.pending,
            execute_after=now_aware(),
            retries=0,
            created_at=now_aware(),
            updated_at=now_aware(),
        )

    async def update(self, job_id: int, updates: FeedRefreshJobUpdates) -> FeedRefreshJob:
        return FeedRefreshJob(
            id=1,
            feed_id=1,
            state=FeedRefreshJobState.pending,
            execute_after=now_aware(),
            retries=0,
            created_at=now_aware(),
            updated_at=now_aware(),
        )
