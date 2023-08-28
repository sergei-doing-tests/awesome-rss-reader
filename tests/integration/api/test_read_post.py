from datetime import UTC, datetime

import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_post import FeedPost
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.entity.user_post import NewUserPost
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory, NewFeedPostFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertUserPostsFixtureT,
)


@pytest_asyncio.fixture()
async def feed(insert_feeds: InsertFeedsFixtureT) -> Feed:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    return feed


@pytest_asyncio.fixture()
async def post(insert_feed_posts: InsertFeedPostsFixtureT, feed: Feed) -> FeedPost:
    post, *_ = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )
    return post


async def test_read_post_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    feed: Feed,
    insert_feed_posts: InsertFeedPostsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    then = now_aware()

    post, other_post = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
        NewFeedPostFactory.build(
            title="How to Use the New Google Chrome Memories Feature",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/how-to-use-google-chrome-memories/",
        ),
    )

    resp = user_api_client.put(f"/api/posts/{post.id}/read")
    assert resp.status_code == 204
    assert resp.content == b""

    # specified post is marked as read, the other post is not
    db_rows = await fetchmany(sa.select(mdl.UserPost))
    assert len(db_rows) == 1

    db_row = db_rows[0]
    assert db_row["user_uid"] == user.uid
    assert db_row["post_id"] == post.id
    assert db_row["read_at"] >= then


async def test_read_post_already_read(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    post: FeedPost,
    insert_user_posts: InsertUserPostsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    user_post, *_ = await insert_user_posts(
        NewUserPost(
            user_uid=user.uid,
            post_id=post.id,
            read_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
    )

    resp = user_api_client.put(f"/api/posts/{post.id}/read")
    assert resp.status_code == 204
    assert resp.content == b""

    # user post is not updated and no new user post is created
    db_rows = await fetchmany(sa.select(mdl.UserPost))
    assert len(db_rows) == 1

    db_row = db_rows[0]
    assert db_row["id"] == user_post.id
    assert db_row["user_uid"] == user.uid
    assert db_row["post_id"] == post.id
    assert db_row["read_at"] == datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC)


async def test_read_post_does_not_exist(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
) -> None:
    resp = user_api_client.put("/api/posts/1/read")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Post not found"}


async def test_read_post_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    post: FeedPost,
) -> None:
    resp = api_client.put(f"/api/posts/{post.id}/read")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
