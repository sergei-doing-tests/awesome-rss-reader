import uuid

import structlog

from awesome_rss_reader.core.entity.user_post import NewUserPost, UserPost
from awesome_rss_reader.core.repository.user_post import UserPostRepository
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository
from tests.factories import UserPostFactory

logger = structlog.get_logger()


class _UserPostAlreadyExistsError(Exception):
    ...


class PostgresUserPostRepository(BasePostgresRepository, UserPostRepository):
    async def get_by_id(self, user_post_id: int) -> UserPost:
        return UserPostFactory.build()

    async def get_for_user_and_post(self, *, user_uid: uuid.UUID, post_id: int) -> UserPost:
        return UserPostFactory.build()

    async def get_or_create(self, new_user_post: NewUserPost) -> UserPost:
        return UserPostFactory.build()

    async def delete(self, user_post_id: int) -> None:
        ...
