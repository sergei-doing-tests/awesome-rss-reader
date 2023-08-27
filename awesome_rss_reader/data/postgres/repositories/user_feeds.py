import uuid

import sqlalchemy as sa
import structlog
from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy.exc import IntegrityError

from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.core.repository.user_feed import (
    UserFeedNoFeedError,
    UserFeedNotFoundError,
    UserFeedRepository,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository

logger = structlog.get_logger()


class UserFeedAlreadyExistsError(Exception):
    ...


class PostgresUserFeedRepository(BasePostgresRepository, UserFeedRepository):
    async def get_by_id(self, user_feed_id: int) -> UserFeed:
        query = sa.select(mdl.UserFeed).where(mdl.UserFeed.c.id == user_feed_id)

        async with self.db.connect() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return UserFeed.model_validate(dict(row))

        raise UserFeedNotFoundError(f"UserFeed with id {user_feed_id} not found")

    async def get_for_user_and_feed(self, *, user_uid: uuid.UUID, feed_id: int) -> UserFeed:
        query = sa.select(mdl.UserFeed).where(
            sa.and_(
                mdl.UserFeed.c.user_uid == user_uid,
                mdl.UserFeed.c.feed_id == feed_id,
            )
        )

        async with self.db.connect() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return UserFeed.model_validate(dict(row))

        raise UserFeedNotFoundError(f"UserFeed for user {user_uid} and feed {feed_id} not found")

    async def get_or_create(self, new_user_feed: NewUserFeed) -> UserFeed:
        try:
            return await self.get_for_user_and_feed(
                user_uid=new_user_feed.user_uid,
                feed_id=new_user_feed.feed_id,
            )
        except UserFeedNotFoundError:
            # fmt: off
            logger.info(
                "User feed does not exist. Creating a new one",
                user_uid=new_user_feed.user_uid, feed_id=new_user_feed.feed_id,
            )
            # fmt: on

        try:
            return await self._maybe_create(new_user_feed)
        except UserFeedAlreadyExistsError:
            return await self.get_for_user_and_feed(
                user_uid=new_user_feed.user_uid,
                feed_id=new_user_feed.feed_id,
            )

    async def _maybe_create(self, new_user_feed: NewUserFeed) -> UserFeed:
        query = sa.insert(mdl.UserFeed).values(new_user_feed.model_dump()).returning(mdl.UserFeed)

        async with self.db.begin() as conn:
            try:
                # the insert may trigger a constraint violation, hence the savepoint
                async with conn.begin_nested():
                    result = await conn.execute(query)
            except IntegrityError as ie:
                logger.warning(
                    "Failed to insert user feed",
                    user_uid=new_user_feed.user_uid,
                    feed_id=new_user_feed.feed_id,
                    error=ie,
                )
                self._handle_integrity_error_on_create(ie)

            row = result.mappings().one()
            return UserFeed.model_validate(dict(row))

    def _handle_integrity_error_on_create(self, ie: IntegrityError) -> None:
        match ie.orig.__cause__:  # type: ignore[union-attr]
            case ForeignKeyViolationError():
                raise UserFeedNoFeedError("Referenced feed does not exist") from ie
            case UniqueViolationError():
                raise UserFeedAlreadyExistsError("User feed already exists") from ie
            case _:
                raise ie

    async def delete(self, user_feed_id: int) -> None:
        query = sa.delete(mdl.UserFeed).where(mdl.UserFeed.c.id == user_feed_id)
        async with self.db.begin() as conn:
            await conn.execute(query)
