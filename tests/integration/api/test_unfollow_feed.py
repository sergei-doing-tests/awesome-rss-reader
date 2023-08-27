import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.data.postgres import models as mdl
from tests.factories.feed import NewFeedFactory
from tests.factories.user import UserFactory
from tests.factories.user_feed import NewUserFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
)


async def test_unfollow_feed_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    other_user = UserFactory.build()

    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed2.xml"),
    )
    user_feed1, user_feed2, other_user_feed = await insert_user_feeds(
        NewUserFeedFactory.build(user_uid=user.uid, feed_id=feed1.id),
        NewUserFeedFactory.build(user_uid=user.uid, feed_id=feed2.id),
        NewUserFeedFactory.build(user_uid=other_user.uid, feed_id=feed1.id),
    )

    resp = user_api_client.delete(f"/api/feeds/{feed1.id}/unfollow")
    assert resp.status_code == 204
    assert resp.content == b""

    # feed is unfollowed, the other user feeds are not affected
    db_rows = await fetchmany(sa.select(mdl.UserFeed).order_by(mdl.UserFeed.c.id))
    assert len(db_rows) == 2

    db_row1, db_row2 = db_rows
    assert db_row1["id"] == user_feed2.id
    assert db_row2["id"] == other_user_feed.id


async def test_unfollow_feed_not_following(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )

    resp = user_api_client.delete(f"/api/feeds/{feed.id}/unfollow")
    assert resp.status_code == 204
    assert resp.content == b""


async def test_unfollow_feed_feed_does_not_exist(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
) -> None:
    resp = user_api_client.delete("/api/feeds/1/unfollow")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Feed not found"}


async def test_unfollow_feed_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )

    resp = api_client.delete(f"/api/feeds/{feed.id}/unfollow")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
