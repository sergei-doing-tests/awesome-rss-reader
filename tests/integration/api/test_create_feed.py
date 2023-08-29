from datetime import timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from dateutil.parser import isoparse
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJobState, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory, NewFeedRefreshJobFactory, NewUserFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
    InsertUserFeedsFixtureT,
)


@pytest_asyncio.fixture()
async def feed(insert_feeds: InsertFeedsFixtureT) -> Feed:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    return feed


async def test_create_feed_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    fetchone: FetchOneFixtureT,
) -> None:
    resp = user_api_client.post("/api/feeds", json={"url": "https://example.com/feed.xml"})

    assert resp.status_code == 202
    resp_json = resp.json()
    assert resp_json.keys() == {"id", "url", "title", "created_at", "published_at"}
    assert resp_json["id"] is not None
    assert resp_json["created_at"] is not None
    assert resp_json["url"] == "https://example.com/feed.xml"
    assert resp_json["title"] is None
    assert resp_json["published_at"] is None

    # feed is created in the database
    db_feed = await fetchone(sa.select(mdl.Feed).where(mdl.Feed.c.id == resp_json["id"]))
    assert db_feed["id"] == resp_json["id"]
    assert db_feed["url"] == "https://example.com/feed.xml"
    assert db_feed["title"] is None
    assert db_feed["published_at"] is None
    assert db_feed["created_at"] == isoparse(resp_json["created_at"])

    # user feed is created in the database
    db_user_feed = await fetchone(
        sa.select(mdl.UserFeed).where(mdl.UserFeed.c.feed_id == resp_json["id"])
    )
    assert db_user_feed["user_uid"] == user.uid
    assert db_user_feed["feed_id"] == resp_json["id"]

    # feed refresh job is created in the database
    db_refresh_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == resp_json["id"])
    )
    assert db_refresh_job["feed_id"] == resp_json["id"]
    assert db_refresh_job["state"] == FeedRefreshJobState.pending.value


@pytest.mark.parametrize("job_exists", [True, False])
async def test_create_feed_already_exists(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    feed: Feed,
    job_exists: bool,
) -> None:
    # feeds always come with a refresh job, and we never delete the latter,
    # but we need to test the case when the refresh job is missing, just in case
    if job_exists:
        await insert_refresh_jobs(
            NewFeedRefreshJob(
                feed_id=feed.id,
                state=FeedRefreshJobState.complete,
            ),
        )

    resp = user_api_client.post("/api/feeds", json={"url": "https://example.com/feed.xml"})
    assert resp.status_code == 202

    # user feed is created in the database
    db_user_feed = await fetchone(sa.select(mdl.UserFeed).where(mdl.UserFeed.c.feed_id == feed.id))
    assert db_user_feed["user_uid"] == user.uid
    assert db_user_feed["feed_id"] == feed.id

    # feed refresh job is created/updated in the database
    db_refresh_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == feed.id)
    )
    assert db_refresh_job["feed_id"] == feed.id
    assert db_refresh_job["state"] == FeedRefreshJobState.pending.value


async def test_create_feed_user_feed_already_exists(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    feed: Feed,
    insert_user_feeds: InsertUserFeedsFixtureT,
    fetchone: FetchOneFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    user_feed, *_ = await insert_user_feeds(
        NewUserFeedFactory.build(
            user_uid=user.uid,
            feed_id=feed.id,
        ),
    )

    resp = user_api_client.post("/api/feeds", json={"url": "https://example.com/feed.xml"})
    assert resp.status_code == 202

    # no duplicate user feed is created in the database
    db_user_feeds = await fetchmany(
        sa.select(mdl.UserFeed).where(mdl.UserFeed.c.feed_id == feed.id)
    )
    assert len(db_user_feeds) == 1

    db_refresh_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == feed.id)
    )
    assert db_refresh_job["feed_id"] == feed.id
    assert db_refresh_job["state"] == FeedRefreshJobState.pending.value


@pytest.mark.parametrize(
    "current_state, new_state, job_is_reset",
    [
        (FeedRefreshJobState.pending, FeedRefreshJobState.pending, False),
        (FeedRefreshJobState.in_progress, FeedRefreshJobState.in_progress, False),
        (FeedRefreshJobState.complete, FeedRefreshJobState.pending, True),
        (FeedRefreshJobState.failed, FeedRefreshJobState.pending, True),
    ],
)
async def test_create_feed_refresh_job_already_exists(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
    feed: Feed,
    current_state: FeedRefreshJobState,
    new_state: FeedRefreshJobState,
    job_is_reset: bool,
) -> None:
    now = now_aware()
    future = now + timedelta(hours=1)

    refresh_job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJobFactory.build(
            feed_id=feed.id,
            state=current_state,
            execute_after=future,
            retries=1,
        )
    )

    resp = user_api_client.post("/api/feeds", json={"url": "https://example.com/feed.xml"})
    assert resp.status_code == 202

    # no duplicate refresh job is created in the database
    db_refresh_jobs = await fetchmany(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == feed.id)
    )
    assert len(db_refresh_jobs) == 1

    db_refresh_job = db_refresh_jobs[0]

    if job_is_reset:
        assert db_refresh_job["retries"] == 0
        assert now < db_refresh_job["execute_after"] < future
    else:
        assert db_refresh_job["retries"] == 1
        assert db_refresh_job["execute_after"] == refresh_job.execute_after

    assert db_refresh_job["state"] == new_state.value


@pytest.mark.parametrize(
    "url, error_msg",
    [
        ("foobar/", "Input should be a valid URL, relative URL without a base"),
        ("https://", "Input should be a valid URL, empty host"),
        ("example.com/", "Input should be a valid URL, relative URL without a base"),
        ("ftp://example.com/", "URL scheme should be 'http' or 'https'"),
    ],
)
async def test_create_feed_invalid_url(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    url: str,
    error_msg: str,
) -> None:
    resp = user_api_client.post("/api/feeds", json={"url": url})
    assert resp.status_code == 422

    resp_json = resp.json()
    assert resp_json.keys() == {"detail"}
    assert resp_json["detail"][0]["msg"] == error_msg


async def test_create_feed_requires_auth(api_client: TestClient) -> None:
    response = api_client.post("/api/feeds", json={"url": "https://example.com/feed.xml"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
