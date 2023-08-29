import uuid
from enum import Enum, auto
from typing import Any

import sqlalchemy as sa
import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert

from awesome_rss_reader.core.entity.feed_post import (
    FeedPost,
    FeedPostFiltering,
    FeedPostOrdering,
    NewFeedPost,
)
from awesome_rss_reader.core.repository.feed_post import FeedPostNotFoundError, FeedPostRepository
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository

logger = structlog.get_logger()


class _PostFollowStatus(Enum):
    following = auto()
    not_following = auto()


class _PostReadStatus(Enum):
    read = auto()
    unread = auto()


class PostgresFeedPostRepository(BasePostgresRepository, FeedPostRepository):
    async def get_by_id(self, post_id: int) -> FeedPost:
        return await self._get_by_field("id", post_id)

    async def get_by_guid(self, guid: str) -> FeedPost:
        return await self._get_by_field("guid", guid)

    async def _get_by_field(self, field: str, value: Any) -> FeedPost:
        query = sa.select(mdl.FeedPost).where(sa.column(field) == value)

        async with self.db.connect() as conn:
            result = await conn.execute(query)

            if row := result.mappings().fetchone():
                return FeedPost.model_validate(dict(row))

        raise FeedPostNotFoundError(f"Post with {field} {value} not found")

    async def create_many(self, posts: list[NewFeedPost]) -> list[FeedPost]:
        insert_q = (
            pg_insert(mdl.FeedPost)
            .values([post.model_dump() for post in posts])
            .on_conflict_do_nothing(constraint="feed_post_feed_id_guid_key")
            .returning(mdl.FeedPost)
        )

        async with self.db.begin() as conn:
            result = await conn.execute(insert_q)

        return [FeedPost.model_validate(dict(row)) for row in result.mappings()]

    async def get_list(
        self,
        *,
        filter_by: FeedPostFiltering | None = None,
        order_by: FeedPostOrdering = FeedPostOrdering.published_at_desc,
        limit: int,
        offset: int,
    ) -> list[FeedPost]:
        query = sa.select(mdl.FeedPost)

        if filter_by:
            query = self._apply_filtering(query, filter_by)

        match order_by:
            case FeedPostOrdering.published_at_desc:
                query = query.order_by(mdl.FeedPost.c.published_at.desc(), mdl.FeedPost.c.id.desc())
            case _:
                raise ValueError(f"Unknown feed post ordering: {order_by}")

        query = query.limit(limit).offset(offset)

        async with self.db.connect() as conn:
            result = await conn.execute(query)

        return [FeedPost.model_validate(dict(row)) for row in result.mappings()]

    def _apply_filtering(
        self,
        query: sa.Select,
        filter_by: FeedPostFiltering,
    ) -> sa.Select:
        if filter_by.feed_id:
            query = query.where(mdl.FeedPost.c.feed_id == filter_by.feed_id)

        if filter_by.followed_by:
            query = self._filter_by_followed_by(
                query, filter_by.followed_by, _PostFollowStatus.following
            )
        elif filter_by.not_followed_by:
            query = self._filter_by_followed_by(
                query, filter_by.not_followed_by, _PostFollowStatus.not_following
            )

        if filter_by.read_by:
            query = self._filter_by_read_by(query, filter_by.read_by, _PostReadStatus.read)
        elif filter_by.not_read_by:
            query = self._filter_by_read_by(query, filter_by.not_read_by, _PostReadStatus.unread)

        return query

    def _filter_by_followed_by(
        self,
        query: sa.Select,
        user_uid: uuid.UUID,
        follow_status: _PostFollowStatus,
    ) -> sa.Select:
        # fmt: off
        subq = (
            sa.select(mdl.UserFeed.c.id)
            .where(
                sa.and_(
                    mdl.UserFeed.c.feed_id == mdl.Feed.c.id,
                    mdl.UserFeed.c.user_uid == user_uid,
                )
            )
            .exists()
        )
        return (
            query
            .select_from(
                mdl.FeedPost
                .join(mdl.Feed, mdl.Feed.c.id == mdl.FeedPost.c.feed_id)
            )
            .where(
                subq if follow_status is _PostFollowStatus.following else ~subq
            )
        )
        # fmt: on

    def _filter_by_read_by(
        self,
        query: sa.Select,
        user_uid: uuid.UUID,
        read_status: _PostReadStatus,
    ) -> sa.Select:
        # fmt: off
        subq = (
            sa.select(mdl.UserPost.c.id)
            .where(
                sa.and_(
                    mdl.UserPost.c.post_id == mdl.FeedPost.c.id,
                    mdl.UserPost.c.user_uid == user_uid
                )
            )
            .exists()
        )

        return (
            query
            .select_from(mdl.FeedPost)
            .where(
                subq if read_status is _PostReadStatus.read else ~subq
            )
        )
        # fmt: on
