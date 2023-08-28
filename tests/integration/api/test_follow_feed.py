import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.data.postgres import models as mdl
from tests.factories import NewFeedFactory, NewUserFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
)


async def test_follow_feed_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed, other_feed = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed2.xml"),
    )

    resp = user_api_client.put(f"/api/feeds/{feed.id}/follow")
    assert resp.status_code == 204
    assert resp.content == b""

    # feed is followed, the other feed is not
    db_rows = await fetchmany(sa.select(mdl.UserFeed))
    assert len(db_rows) == 1

    db_row = db_rows[0]
    assert db_row["feed_id"] == feed.id
    assert db_row["user_uid"] == user.uid
    assert db_row["created_at"] is not None


async def test_follow_feed_already_following(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    user_feed, *_ = await insert_user_feeds(
        NewUserFeedFactory.build(
            feed_id=feed.id,
            user_uid=user.uid,
        ),
    )

    resp = user_api_client.put(f"/api/feeds/{feed.id}/follow")
    assert resp.status_code == 204
    assert resp.content == b""

    # no new user feed is created
    db_rows = await fetchmany(sa.select(mdl.UserFeed))
    assert len(db_rows) == 1

    db_row = db_rows[0]
    assert db_row["id"] == user_feed.id
    assert db_row["feed_id"] == feed.id
    assert db_row["user_uid"] == user.uid
    assert db_row["created_at"] == user_feed.created_at


async def test_follow_feed_feed_does_not_exist(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
) -> None:
    resp = user_api_client.put("/api/feeds/1/follow")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Feed not found"}


async def test_follow_feed_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )

    resp = api_client.put(f"/api/feeds/{feed.id}/follow")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
