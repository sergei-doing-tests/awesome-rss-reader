import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_post import FeedPost, NewFeedPost, NewUserPost, UserPost
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJob, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.data.postgres import models as mdl

from .types import (
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertManyFixtureT,
    InsertRefreshJobsFixtureT,
    InsertUserFeedsFixtureT,
    InsertUserPostsFixtureT,
)


@pytest_asyncio.fixture()
async def insert_feeds(db: AsyncEngine, insert_many: InsertManyFixtureT) -> InsertFeedsFixtureT:
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
) -> InsertUserFeedsFixtureT:
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
async def insert_feed_posts(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> InsertFeedPostsFixtureT:
    async def inserter(*new_posts: NewFeedPost) -> list[FeedPost]:
        # fmt: off
        db_rows = await insert_many(
            sa.insert(mdl.FeedPost)
            .values([post.model_dump() for post in new_posts])
            .returning(mdl.FeedPost)
        )
        # fmt: on
        return [FeedPost.model_validate(row) for row in db_rows]

    return inserter


@pytest_asyncio.fixture()
async def insert_user_posts(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> InsertUserPostsFixtureT:
    async def inserter(*new_posts: NewUserPost) -> list[UserPost]:
        # fmt: off
        db_rows = await insert_many(
            sa.insert(mdl.UserPost)
            .values([post.model_dump() for post in new_posts])
            .returning(mdl.UserPost)
        )
        # fmt: on
        return [UserPost.model_validate(row) for row in db_rows]

    return inserter


@pytest_asyncio.fixture()
async def insert_refresh_jobs(
    db: AsyncEngine,
    insert_many: InsertManyFixtureT,
) -> InsertRefreshJobsFixtureT:
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
