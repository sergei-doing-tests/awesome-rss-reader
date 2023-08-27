import uuid
from dataclasses import dataclass

import structlog

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import user_feed as user_feed_repo
from awesome_rss_reader.core.usecase.base import BaseUseCase

logger = structlog.get_logger()


@dataclass
class FollowFeedInput:
    feed_id: int
    user_uid: uuid.UUID


@dataclass
class FollowFeedOutput:
    user_feed: UserFeed


class FeedNotFoundError(Exception):
    ...


@dataclass
class FollowFeedUseCase(BaseUseCase):
    feed_repository: feed_repo.FeedRepository
    user_feed_repository: user_feed_repo.UserFeedRepository

    async def execute(self, data: FollowFeedInput) -> FollowFeedOutput:
        feed = await self._get_feed(data.feed_id)
        user_feed = await self._follow_feed(feed_id=feed.id, user_uid=data.user_uid)
        return FollowFeedOutput(user_feed=user_feed)

    async def _get_feed(self, feed_id: int) -> Feed:
        try:
            return await self.feed_repository.get_by_id(feed_id)
        except feed_repo.FeedNotFoundError:
            logger.info("Requested feed to follow not found", feed_id=feed_id)
            raise FeedNotFoundError(f"Feed with {feed_id=} not found in repository")

    async def _follow_feed(self, *, feed_id: int, user_uid: uuid.UUID) -> UserFeed:
        new_user_feed = NewUserFeed(feed_id=feed_id, user_uid=user_uid)
        try:
            return await self.user_feed_repository.get_or_create(new_user_feed)
        except user_feed_repo.UserFeedNoFeedError:
            # despite the earlier check, the feed might have been deleted to this point
            logger.info("Requested feed to follow not found", feed_id=feed_id)
            raise FeedNotFoundError(f"Feed with {feed_id=} not found in repository")
