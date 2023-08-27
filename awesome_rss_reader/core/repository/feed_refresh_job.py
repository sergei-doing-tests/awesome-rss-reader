from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)


class RefreshJobNotFoundError(Exception):
    ...


class RefreshJobNoFeedError(Exception):
    ...


class RefreshJobStateTransitionError(Exception):
    ...


class FeedRefreshJobRepository(ABC):
    @abstractmethod
    async def get_by_id(self, job_id: int) -> FeedRefreshJob:
        ...

    @abstractmethod
    async def get_by_feed_id(self, feed_id: int) -> FeedRefreshJob:
        ...

    @abstractmethod
    async def get_or_create(self, new_job: NewFeedRefreshJob) -> FeedRefreshJob:
        ...

    @abstractmethod
    async def update(self, *, job_id: int, updates: FeedRefreshJobUpdates) -> FeedRefreshJob:
        ...

    @abstractmethod
    async def transit_state(
        self,
        job_id: int,
        old_state: FeedRefreshJobState,
        new_state: FeedRefreshJobState,
    ) -> FeedRefreshJob:
        ...
