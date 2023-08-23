from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)


class FeedRefreshJobRepository(ABC):
    @abstractmethod
    async def get_or_create(self, new_job: NewFeedRefreshJob) -> FeedRefreshJob:
        ...

    @abstractmethod
    async def update(self, job_id: int, updates: FeedRefreshJobUpdates) -> FeedRefreshJob:
        ...
