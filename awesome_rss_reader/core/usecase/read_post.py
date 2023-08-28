import uuid
from dataclasses import dataclass

import structlog

from awesome_rss_reader.core.entity.feed_post import FeedPost
from awesome_rss_reader.core.entity.user_post import NewUserPost, UserPost
from awesome_rss_reader.core.repository import feed_post as post_repo
from awesome_rss_reader.core.repository import user_post as user_post_repo
from awesome_rss_reader.core.usecase.base import BaseUseCase
from awesome_rss_reader.utils.dtime import now_aware

logger = structlog.get_logger()


@dataclass
class ReadPostInput:
    post_id: int
    user_uid: uuid.UUID


@dataclass
class ReadPostOutput:
    user_post: UserPost


class PostNotFoundError(Exception):
    ...


@dataclass
class ReadPostUseCase(BaseUseCase):
    post_repository: post_repo.FeedPostRepository
    user_post_repository: user_post_repo.UserPostRepository

    async def execute(self, data: ReadPostInput) -> ReadPostOutput:
        post = await self._get_post(data.post_id)
        user_post = await self._read_post(post_id=post.id, user_uid=data.user_uid)
        return ReadPostOutput(user_post=user_post)

    async def _get_post(self, post_id: int) -> FeedPost:
        try:
            return await self.post_repository.get_by_id(post_id)
        except post_repo.FeedPostNotFoundError:
            logger.info("Requested post to read not found", post_id=post_id)
            raise PostNotFoundError(f"Post with {post_id=} not found in repository")

    async def _read_post(self, *, post_id: int, user_uid: uuid.UUID) -> UserPost:
        new_user_post = NewUserPost(post_id=post_id, user_uid=user_uid, read_at=now_aware())
        try:
            return await self.user_post_repository.get_or_create(new_user_post)
        except user_post_repo.UserPostNoPostError:
            # despite the earlier check, the post might have been deleted to this point
            logger.info("Requested post to read not found", post_id=post_id)
            raise PostNotFoundError(f"Post with {post_id=} not found in repository")
