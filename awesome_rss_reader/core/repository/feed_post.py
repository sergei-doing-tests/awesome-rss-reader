from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed_post import (
    FeedPost,
    FeedPostFiltering,
    FeedPostOrdering,
    NewFeedPost,
)


class FeedPostNotFoundError(Exception):
    ...


class FeedPostRepository(ABC):
    @abstractmethod
    async def get_by_id(self, post_id: int) -> FeedPost:
        ...

    @abstractmethod
    async def get_by_guid(self, guid: str) -> FeedPost:
        ...

    @abstractmethod
    async def create_many(self, posts: list[NewFeedPost]) -> list[FeedPost]:
        ...

    @abstractmethod
    async def get_list(
        self,
        *,
        filter_by: FeedPostFiltering | None = None,
        order_by: FeedPostOrdering = FeedPostOrdering.published_at_desc,
        limit: int,
        offset: int,
    ) -> list[FeedPost]:
        ...
