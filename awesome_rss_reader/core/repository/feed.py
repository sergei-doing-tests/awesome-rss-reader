from abc import ABC, abstractmethod
from uuid import UUID

from awesome_rss_reader.core.entity.feed import Feed, FeedOrdering, NewFeed


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
        followed_by: UUID | None = None,
        order_by: FeedOrdering = FeedOrdering.id_asc,
        limit: int,
        offset: int,
    ) -> list[Feed]:
        ...
