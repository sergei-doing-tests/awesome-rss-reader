import uuid
from dataclasses import dataclass

import structlog

from awesome_rss_reader.core.entity.feed_post import FeedPost
from awesome_rss_reader.core.repository import feed_post as post_repo
from awesome_rss_reader.core.repository import user_post as user_post_repo
from awesome_rss_reader.core.usecase.base import BaseUseCase

logger = structlog.get_logger()


@dataclass
class UnreadPostInput:
    post_id: int
    user_uid: uuid.UUID


class PostNotFoundError(Exception):
    ...


@dataclass
class UnreadPostUseCase(BaseUseCase):
    post_repository: post_repo.FeedPostRepository
    user_post_repository: user_post_repo.UserPostRepository

    async def execute(self, data: UnreadPostInput) -> None:
        post = await self._get_post(data.post_id)
        await self._unread_post(post_id=post.id, user_uid=data.user_uid)

    async def _get_post(self, post_id: int) -> FeedPost:
        try:
            return await self.post_repository.get_by_id(post_id)
        except post_repo.FeedPostNotFoundError:
            logger.info("Requested post to unread not found", post_id=post_id)
            raise PostNotFoundError(f"Post with {post_id=} not found in repository")

    async def _unread_post(self, *, post_id: int, user_uid: uuid.UUID) -> None:
        try:
            user_post = await self.user_post_repository.get_for_user_and_post(
                user_uid=user_uid, post_id=post_id
            )
        except user_post_repo.UserPostNotFoundError:
            # because the unread operation is idempotent, we don't need to raise an error here
            # fmt: off
            logger.info(
                "Requested post to unread not found for user",
                user_uid=user_uid, post_id=post_id,
            )
            # fmt: on
        else:
            await self.user_post_repository.delete(user_post.id)
