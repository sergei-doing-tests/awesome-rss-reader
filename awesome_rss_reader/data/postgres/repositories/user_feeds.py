from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.core.repository.user_feed import UserFeedRepository
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository
from awesome_rss_reader.utils.dtime import now_aware


class PostgresUserFeedRepository(BasePostgresRepository, UserFeedRepository):
    async def get_or_create(self, new_user_feed: NewUserFeed) -> UserFeed:
        return UserFeed(
            id=1,
            user_uid=new_user_feed.user_uid,
            feed_id=new_user_feed.feed_id,
            created_at=now_aware(),
        )
