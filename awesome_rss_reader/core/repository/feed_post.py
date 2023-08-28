from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed_post import FeedPost, FeedPostFiltering, FeedPostOrdering


class FeedPostRepository(ABC):
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
