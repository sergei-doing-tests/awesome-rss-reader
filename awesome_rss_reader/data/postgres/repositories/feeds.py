from uuid import UUID

from awesome_rss_reader.core.entity.feed import Feed, FeedOrdering, NewFeed
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository
from awesome_rss_reader.utils.dtime import now_aware


class PostgresFeedRepository(BasePostgresRepository, FeedRepository):
    async def get_by_id(self, feed_id: int) -> Feed:
        return Feed(id=1, url="https://example.com/feed.xml", created_at=now_aware())

    async def get_by_url(self, url: str) -> Feed:
        return Feed(id=1, url="https://example.com/feed.xml", created_at=now_aware())

    async def get_or_create(self, new_feed: NewFeed) -> Feed:
        return Feed(id=1, url="https://example.com/feed.xml", created_at=now_aware())

    async def get_list(
        self,
        *,
        limit: int,
        offset: int,
        followed_by_user: UUID | None = None,
        order_by: FeedOrdering | None = None,
    ) -> list[Feed]:
        return []
