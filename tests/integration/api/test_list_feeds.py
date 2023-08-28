import uuid
from collections.abc import Callable
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory, NewUserFeedFactory, UserFactory
from tests.pytest_fixtures.types import (
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
)


@pytest.mark.parametrize(
    "user_uid, expected_titles",
    [
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), ["Feed 1", "Feed 3", "Feed 2"]),
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), ["Feed 5", "Feed 4"]),
        (uuid.uuid4(), []),
    ],
)
async def test_list_user_followed_feeds(
    postgres_database: AsyncEngine,
    api_client_factory: Callable[[User | None], TestClient],
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    user_uid: uuid.UUID,
    expected_titles: list[str],
) -> None:
    now = now_aware()

    user1 = UserFactory.build(uid=uuid.UUID("facade00-0000-4000-a000-000000000000"))
    user2 = UserFactory.build(uid=uuid.UUID("decade00-0000-4000-a000-000000000000"))

    feeds = [
        NewFeedFactory.build(title="Feed 1", refreshed_at=now),
        NewFeedFactory.build(title="Feed 2", refreshed_at=now - timedelta(hours=6)),
        NewFeedFactory.build(title="Feed 3", refreshed_at=now - timedelta(hours=1)),
        NewFeedFactory.build(title="Feed 4", refreshed_at=now - timedelta(hours=24)),
        NewFeedFactory.build(title="Feed 5", refreshed_at=now),
    ]
    feed1, feed2, feed3, feed4, feed5 = await insert_feeds(*feeds)

    user_feeds = [
        # user1 feeds
        NewUserFeedFactory.build(
            feed_id=feed2.id,
            user_uid=user1.uid,
        ),
        NewUserFeedFactory.build(
            feed_id=feed1.id,
            user_uid=user1.uid,
        ),
        NewUserFeedFactory.build(
            feed_id=feed3.id,
            user_uid=user1.uid,
        ),
        # user2 feeds
        NewUserFeedFactory.build(
            feed_id=feed4.id,
            user_uid=user2.uid,
        ),
        NewUserFeedFactory.build(
            feed_id=feed5.id,
            user_uid=user2.uid,
        ),
    ]
    await insert_user_feeds(*user_feeds)

    api_user = UserFactory.build(uid=user_uid)
    api_client = api_client_factory(api_user)

    resp = api_client.get("/api/feeds")
    assert resp.status_code == 200

    resp_json = resp.json()
    feed_titles = [feed["title"] for feed in resp_json]

    assert feed_titles == expected_titles


@pytest.mark.parametrize(
    "limit, offset, expected_titles",
    [
        (0, 0, []),
        (0, 10, []),
        (10, 10, []),
        (10, 0, ["Feed 5", "Feed 1", "Feed 3", "Feed 2", "Feed 4"]),
        (1, 0, ["Feed 5"]),
        (2, 3, ["Feed 2", "Feed 4"]),
    ],
)
async def test_get_user_followed_feeds_pagination(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    limit: int,
    offset: int,
    expected_titles: list[str],
) -> None:
    now = now_aware()

    feeds = [
        NewFeedFactory.build(title="Feed 1", refreshed_at=now),
        NewFeedFactory.build(title="Feed 2", refreshed_at=now - timedelta(hours=6)),
        NewFeedFactory.build(title="Feed 3", refreshed_at=now - timedelta(hours=1)),
        NewFeedFactory.build(title="Feed 4", refreshed_at=now - timedelta(hours=24)),
        NewFeedFactory.build(title="Feed 5", refreshed_at=now),
    ]
    feed1, feed2, feed3, feed4, feed5 = await insert_feeds(*feeds)

    user_feeds = [
        NewUserFeedFactory.build(
            feed_id=feed.id,
            user_uid=user.uid,
        )
        for feed in [feed1, feed2, feed3, feed4, feed5]
    ]
    await insert_user_feeds(*user_feeds)

    resp = user_api_client.get("/api/feeds", params={"limit": limit, "offset": offset})
    assert resp.status_code == 200

    resp_json = resp.json()
    feed_titles = [feed["title"] for feed in resp_json]

    assert feed_titles == expected_titles
