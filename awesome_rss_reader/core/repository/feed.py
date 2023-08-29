from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed import (
    Feed,
    FeedFiltering,
    FeedOrdering,
    FeedUpdates,
    NewFeed,
)


class FeedNotFoundError(Exception):
    ...


class FeedRepository(ABC):
    @abstractmethod
    async def get_by_id(self, feed_id: int) -> Feed:
        ...

    @abstractmethod
    async def get_by_url(self, url: str) -> Feed:
        ...

    @abstractmethod
    async def get_or_create(self, new_feed: NewFeed) -> Feed:
        ...

    @abstractmethod
    async def get_list(
        self,
        *,
        filter_by: FeedFiltering | None = None,
        order_by: FeedOrdering = FeedOrdering.id_asc,
        limit: int,
        offset: int,
    ) -> list[Feed]:
        ...

    @abstractmethod
    async def update(self, *, feed_id: int, updates: FeedUpdates) -> Feed:
        ...
