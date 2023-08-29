from typing import Any

import sqlalchemy as sa
import structlog
from asyncpg import UniqueViolationError
from sqlalchemy.exc import IntegrityError

from awesome_rss_reader.core.entity.feed import (
    Feed,
    FeedFiltering,
    FeedOrdering,
    FeedUpdates,
    NewFeed,
)
from awesome_rss_reader.core.repository.feed import (
    FeedNotFoundError,
    FeedRepository,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository

logger = structlog.get_logger()


class _FeedAlreadyExistsError(Exception):
    """This an internal exception used for conflict handling."""


class PostgresFeedRepository(BasePostgresRepository, FeedRepository):
    async def get_by_id(self, feed_id: int) -> Feed:
        return await self._get_by_field("id", feed_id)

    async def get_by_url(self, url: str) -> Feed:
        return await self._get_by_field("url", url)

    async def _get_by_field(self, field: str, value: Any) -> Feed:
        query = sa.select(mdl.Feed).where(sa.column(field) == value)

        async with self.db.connect() as conn:
            result = await conn.execute(query)

            if row := result.mappings().fetchone():
                return Feed.model_validate(dict(row))

        raise FeedNotFoundError(f"Feed with {field} {value} not found")

    async def get_or_create(self, new_feed: NewFeed) -> Feed:
        try:
            return await self.get_by_url(new_feed.url)
        except FeedNotFoundError:
            logger.info("Feed does not exist. Creating a new one", url=new_feed.url)

        try:
            return await self._maybe_create(new_feed)
        except _FeedAlreadyExistsError:
            # a feed with the same url may have been created in the meantime
            return await self.get_by_url(new_feed.url)

    async def _maybe_create(self, new_feed: NewFeed) -> Feed:
        query = sa.insert(mdl.Feed).values(new_feed.model_dump()).returning(mdl.Feed)

        async with self.db.begin() as conn:
            try:
                # the insert may trigger a constraint violation, hence the savepoint
                async with conn.begin_nested():
                    result = await conn.execute(query)
            except IntegrityError as ie:
                logger.warning("Failed to insert feed", url=new_feed.url, error=ie)
                self._handle_integrity_error_on_create(ie)

            row = result.mappings().one()
            return Feed.model_validate(dict(row))

    def _handle_integrity_error_on_create(self, ie: IntegrityError) -> None:
        match ie.orig.__cause__:  # type: ignore[union-attr]
            case UniqueViolationError():
                raise _FeedAlreadyExistsError("Feed already exists") from ie
            case _:
                raise ie

    async def get_list(
        self,
        *,
        filter_by: FeedFiltering | None = None,
        order_by: FeedOrdering = FeedOrdering.id_asc,
        limit: int,
        offset: int,
    ) -> list[Feed]:
        query = sa.select(mdl.Feed)

        if filter_by:
            query = self._apply_filtering(query, filter_by)

        match order_by:
            case FeedOrdering.id_asc:
                query = query.order_by(mdl.Feed.c.id.asc())
            case FeedOrdering.published_at_desc:
                query = query.order_by(mdl.Feed.c.published_at.desc(), mdl.Feed.c.id.desc())
            case _:
                raise ValueError(f"Unknown feed ordering: {order_by}")

        query = query.limit(limit).offset(offset)

        async with self.db.connect() as conn:
            result = await conn.execute(query)

        return [Feed.model_validate(dict(row)) for row in result.mappings()]

    def _apply_filtering(self, query: sa.Select, filter_by: FeedFiltering) -> sa.Select:
        if filter_by.ids:
            query = query.where(mdl.Feed.c.id.in_(filter_by.ids))

        if filter_by.followed_by:
            # fmt: off
            query = (
                query
                .select_from(
                    mdl.Feed
                    .join(mdl.UserFeed, mdl.UserFeed.c.feed_id == mdl.Feed.c.id)
                )
                .where(mdl.UserFeed.c.user_uid == filter_by.followed_by)
            )
            # fmt: on

        return query

    async def update(self, *, feed_id: int, updates: FeedUpdates) -> Feed:
        update_q = (
            sa.update(mdl.Feed)
            .where(mdl.Feed.c.id == feed_id)
            .values(**updates.model_dump(exclude_unset=True))
            .returning(mdl.Feed)
        )

        async with self.db.begin() as conn:
            result = await conn.execute(update_q)

            if row := result.mappings().fetchone():
                return Feed.model_validate(dict(row))

        raise FeedNotFoundError(f"Failed to update feed with {feed_id=}")
