import uuid

import sqlalchemy as sa
import structlog
from asyncpg import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy.exc import IntegrityError

from awesome_rss_reader.core.entity.user_post import NewUserPost, UserPost
from awesome_rss_reader.core.repository.user_post import (
    UserPostNoPostError,
    UserPostNotFoundError,
    UserPostRepository,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository

logger = structlog.get_logger()


class _UserPostAlreadyExistsError(Exception):
    ...


class PostgresUserPostRepository(BasePostgresRepository, UserPostRepository):
    async def get_by_id(self, user_post_id: int) -> UserPost:
        query = sa.select(mdl.UserPost).where(mdl.UserPost.c.id == user_post_id)

        async with self.db.connect() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return UserPost.model_validate(dict(row))

        raise UserPostNotFoundError(f"UserPost with id {user_post_id} not found")

    async def get_for_user_and_post(self, *, user_uid: uuid.UUID, post_id: int) -> UserPost:
        query = sa.select(mdl.UserPost).where(
            sa.and_(
                mdl.UserPost.c.user_uid == user_uid,
                mdl.UserPost.c.post_id == post_id,
            )
        )

        async with self.db.connect() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return UserPost.model_validate(dict(row))

        raise UserPostNotFoundError(f"UserPost for {user_uid=} and {post_id=} not found")

    async def get_or_create(self, new_user_post: NewUserPost) -> UserPost:
        try:
            return await self.get_for_user_and_post(
                user_uid=new_user_post.user_uid,
                post_id=new_user_post.post_id,
            )
        except UserPostNotFoundError:
            # fmt: off
            logger.info(
                "User post does not exist. Creating a new one",
                user_uid=new_user_post.user_uid, post_id=new_user_post.post_id,
            )
            # fmt: on

        try:
            return await self._maybe_create(new_user_post)
        except _UserPostAlreadyExistsError:
            return await self.get_for_user_and_post(
                user_uid=new_user_post.user_uid,
                post_id=new_user_post.post_id,
            )

    async def _maybe_create(self, new_user_post: NewUserPost) -> UserPost:
        query = sa.insert(mdl.UserPost).values(new_user_post.model_dump()).returning(mdl.UserPost)

        async with self.db.begin() as conn:
            try:
                # the insert may trigger a constraint violation, hence the savepoint
                async with conn.begin_nested():
                    result = await conn.execute(query)
            except IntegrityError as ie:
                # fmt: off
                logger.warning(
                    "Failed to insert user post",
                    user_uid=new_user_post.user_uid, post_id=new_user_post.post_id, error=ie,
                )
                # fmt: on
                self._handle_integrity_error_on_create(ie)

            row = result.mappings().one()
            return UserPost.model_validate(dict(row))

    def _handle_integrity_error_on_create(self, ie: IntegrityError) -> None:
        match ie.orig.__cause__:  # type: ignore[union-attr]
            case ForeignKeyViolationError():
                raise UserPostNoPostError("Referenced post does not exist") from ie
            case UniqueViolationError():
                raise _UserPostAlreadyExistsError("User post already exists") from ie
            case _:
                raise ie

    async def delete(self, user_post_id: int) -> None:
        query = sa.delete(mdl.UserPost).where(mdl.UserPost.c.id == user_post_id)
        async with self.db.begin() as conn:
            await conn.execute(query)
