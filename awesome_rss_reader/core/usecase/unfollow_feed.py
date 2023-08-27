import uuid
from dataclasses import dataclass

import structlog

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import user_feed as user_feed_repo
from awesome_rss_reader.core.usecase.base import BaseUseCase

logger = structlog.get_logger()


@dataclass
class UnfollowFeedInput:
    feed_id: int
    user_uid: uuid.UUID


class FeedNotFoundError(Exception):
    ...


@dataclass
class UnfollowFeedUseCase(BaseUseCase):
    feed_repository: feed_repo.FeedRepository
    user_feed_repository: user_feed_repo.UserFeedRepository

    async def execute(self, data: UnfollowFeedInput) -> None:
        feed = await self._get_feed(data.feed_id)
        await self._unfollow_feed(feed_id=feed.id, user_uid=data.user_uid)

    async def _get_feed(self, feed_id: int) -> Feed:
        try:
            return await self.feed_repository.get_by_id(feed_id)
        except feed_repo.FeedNotFoundError:
            logger.info("Requested feed to unfollow not found", feed_id=feed_id)
            raise FeedNotFoundError(f"Feed with {feed_id=} not found in repository")

    async def _unfollow_feed(self, *, feed_id: int, user_uid: uuid.UUID) -> None:
        try:
            user_feed = await self.user_feed_repository.get_for_user_and_feed(
                user_uid=user_uid, feed_id=feed_id
            )
        except user_feed_repo.UserFeedNotFoundError:
            # because the unfollow operation is idempotent, we don't need to raise an error here
            # fmt: off
            logger.info(
                "Requested feed to unfollow not found for user",
                user_uid=user_uid, feed_id=feed_id,
            )
            # fmt: on
        else:
            await self.user_feed_repository.delete(user_feed.id)
