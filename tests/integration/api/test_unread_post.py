import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_post import FeedPost
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.data.postgres import models as mdl
from tests.factories import NewFeedFactory, NewFeedPostFactory, NewUserPostFactory, UserFactory
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


async def test_unread_post_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    fetchmany: FetchManyFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
    feed: Feed,
) -> None:
    other_user = UserFactory.build()

    post1, post2 = await insert_feed_posts(
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

    user_post1, user_post2, other_user_post = await insert_user_posts(
        NewUserPostFactory.build(user_uid=user.uid, post_id=post1.id),
        NewUserPostFactory.build(user_uid=user.uid, post_id=post2.id),
        NewUserPostFactory.build(user_uid=other_user.uid, post_id=post1.id),
    )

    resp = user_api_client.delete(f"/api/posts/{post1.id}/unread")
    assert resp.status_code == 204
    assert resp.content == b""

    # post is marked as unread, the other user posts are not affected
    db_rows = await fetchmany(sa.select(mdl.UserPost).order_by(mdl.UserPost.c.id))
    assert len(db_rows) == 2

    db_row1, db_row2 = db_rows
    assert db_row1["id"] == user_post2.id
    assert db_row2["id"] == other_user_post.id


async def test_unread_post_not_read(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    post: FeedPost,
) -> None:
    resp = user_api_client.delete(f"/api/posts/{post.id}/unread")
    assert resp.status_code == 204
    assert resp.content == b""


async def test_unread_post_does_not_exist(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
) -> None:
    resp = user_api_client.delete("/api/posts/999/unread")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Post not found"}


async def test_unread_post_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    post: FeedPost,
) -> None:
    resp = api_client.delete(f"/api/posts/{post.id}/unread")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
