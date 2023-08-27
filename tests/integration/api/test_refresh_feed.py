from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJobState
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories.feed import NewFeedFactory
from tests.factories.feed_refresh_job import NewFeedRefreshJobFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
)


async def test_refresh_feed_happy_path(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    fetchone: FetchOneFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
) -> None:
    now = now_aware()
    future = now + timedelta(hours=1)

    feed, other_feed = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/other_feed.xml"),
    )
    refresh_job, other_refresh_job = await insert_refresh_jobs(
        NewFeedRefreshJobFactory.build(
            feed_id=feed.id,
            state=FeedRefreshJobState.failed,
            execute_after=future,
            retries=5,
        ),
        NewFeedRefreshJobFactory.build(
            feed_id=other_feed.id,
            state=FeedRefreshJobState.in_progress,
            execute_after=future,
            retries=2,
        ),
    )

    resp = user_api_client.post(f"/api/feeds/{feed.id}/refresh")

    assert resp.status_code == 202
    assert resp.json() is None

    # existing refresh job is updated in the database
    db_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == refresh_job.id)
    )
    assert db_job["state"] == FeedRefreshJobState.pending.value
    assert db_job["retries"] == 0
    assert now <= db_job["execute_after"] < future

    # the other refresh job is not affected
    db_other_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.id == other_refresh_job.id)
    )
    assert db_other_job["state"] == FeedRefreshJobState.in_progress.value
    assert db_other_job["retries"] == 2
    assert db_other_job["execute_after"] == future


async def test_refresh_feed_refresh_job_is_created(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    fetchone: FetchOneFixtureT,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    now = now_aware()

    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )

    resp = user_api_client.post(f"/api/feeds/{feed.id}/refresh")
    assert resp.status_code == 202
    assert resp.json() is None

    # refresh job is created in the database
    db_job = await fetchone(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == feed.id)
    )
    assert db_job["state"] == FeedRefreshJobState.pending.value
    assert db_job["retries"] == 0
    assert db_job["execute_after"] >= now


@pytest.mark.parametrize(
    "current_state, new_state, job_is_reset",
    [
        (FeedRefreshJobState.pending, FeedRefreshJobState.pending, False),
        (FeedRefreshJobState.in_progress, FeedRefreshJobState.in_progress, False),
        (FeedRefreshJobState.complete, FeedRefreshJobState.pending, True),
        (FeedRefreshJobState.failed, FeedRefreshJobState.pending, True),
    ],
)
async def test_refresh_feed_refresh_job_is_queued(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
    current_state: FeedRefreshJobState,
    new_state: FeedRefreshJobState,
    job_is_reset: bool,
) -> None:
    now = now_aware()
    future = now + timedelta(hours=1)

    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    refresh_job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJobFactory.build(
            feed_id=feed.id,
            state=current_state,
            execute_after=future,
            retries=1,
        ),
    )

    resp = user_api_client.post(f"/api/feeds/{feed.id}/refresh")
    assert resp.status_code == 202

    db_refresh_jobs = await fetchmany(
        sa.select(mdl.FeedRefreshJob).where(mdl.FeedRefreshJob.c.feed_id == feed.id)
    )
    # no duplicate refresh job is created in the database
    assert len(db_refresh_jobs) == 1

    db_refresh_job = db_refresh_jobs[0]

    if job_is_reset:
        assert db_refresh_job["retries"] == 0
        assert now < db_refresh_job["execute_after"] < future
    else:
        assert db_refresh_job["retries"] == 1
        assert db_refresh_job["execute_after"] == refresh_job.execute_after

    assert db_refresh_job["state"] == new_state.value


async def test_refresh_feed_feed_does_not_exist(
    postgres_database: AsyncEngine,
    user_api_client: TestClient,
) -> None:
    resp = user_api_client.post("/api/feeds/1/refresh")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Feed not found"}


async def test_refresh_feed_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )

    resp = api_client.post(f"/api/feeds/{feed.id}/refresh")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
