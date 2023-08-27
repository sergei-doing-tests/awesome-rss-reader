from collections.abc import Awaitable, Callable

import pytest_asyncio
import sqlalchemy as sa
from mypy_extensions import VarArg
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJob, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.data.postgres import models as mdl

from .types import InsertManyFixtureT


@pytest_asyncio.fixture()
async def insert_feeds(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> Callable[[VarArg(NewFeed)], Awaitable[list[Feed]]]:
    async def inserter(*new_feeds: NewFeed) -> list[Feed]:
        db_rows = await insert_many(
            sa.insert(mdl.Feed).values([f.model_dump() for f in new_feeds]).returning(mdl.Feed)
        )
        return [Feed.model_validate(row) for row in db_rows]

    return inserter


@pytest_asyncio.fixture()
async def insert_user_feeds(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> Callable[[VarArg(NewUserFeed)], Awaitable[list[UserFeed]]]:
    async def inserter(*new_user_feeds: NewUserFeed) -> list[UserFeed]:
        # fmt: off
        db_rows = await insert_many(
            sa.insert(mdl.UserFeed)
            .values([uf.model_dump() for uf in new_user_feeds])
            .returning(mdl.UserFeed)
        )
        # fmt: on
        return [UserFeed.model_validate(row) for row in db_rows]

    return inserter


@pytest_asyncio.fixture()
async def insert_refresh_jobs(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> Callable[[VarArg(NewFeedRefreshJob)], Awaitable[list[FeedRefreshJob]]]:
    async def inserter(*new_jobs: NewFeedRefreshJob) -> list[FeedRefreshJob]:
        # fmt: off
        db_rows = await insert_many(
            sa.insert(mdl.FeedRefreshJob)
            .values([job.model_dump() for job in new_jobs])
            .returning(mdl.FeedRefreshJob)
        )
        # fmt: on
        return [FeedRefreshJob.model_validate(row) for row in db_rows]

    return inserter
