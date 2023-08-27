from collections.abc import Callable

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.repository.feed_refresh_job import (
    RefreshJobNoFeedError,
    RefreshJobNotFoundError,
    RefreshJobStateTransitionError,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.feed_refresh_jobs import (
    PostgresFeedRefreshJobRepository,
)
from tests.factories.feed import NewFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresFeedRefreshJobRepository:
    return PostgresFeedRefreshJobRepository(db=db)


async def test_get_by_id(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
    )

    job1, job2 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed2.id, state=FeedRefreshJobState.complete),
    )

    got1 = await repo.get_by_id(job1.id)
    assert got1.id == job1.id
    assert got1.state == FeedRefreshJobState.pending

    got2 = await repo.get_by_id(job2.id)
    assert got2.id == job2.id
    assert got2.state == FeedRefreshJobState.complete


@pytest.mark.parametrize("job_id", [-1, 0, 999999])
async def test_get_by_id_not_found(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    job_id: int,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    await insert_refresh_jobs(NewFeedRefreshJob(feed_id=feed.id))

    with pytest.raises(RefreshJobNotFoundError):
        await repo.get_by_id(job_id)


async def test_get_by_feed_id(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
    )

    job1, job2 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed2.id, state=FeedRefreshJobState.complete),
    )

    got1 = await repo.get_by_feed_id(feed1.id)
    assert got1.id == job1.id
    assert got1.state == FeedRefreshJobState.pending

    got2 = await repo.get_by_feed_id(feed2.id)
    assert got2.id == job2.id
    assert got2.state == FeedRefreshJobState.complete


async def test_get_by_feed_id_not_found(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
    )
    await insert_refresh_jobs(NewFeedRefreshJob(feed_id=feed1.id))

    with pytest.raises(RefreshJobNotFoundError):
        await repo.get_by_feed_id(feed2.id)

    with pytest.raises(RefreshJobNotFoundError):
        await repo.get_by_feed_id(99999)


async def test_get_or_create_new(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(*NewFeedFactory.batch(2))

    new_refresh_jobs = [
        NewFeedRefreshJob(feed_id=feed1.id),
        NewFeedRefreshJob(feed_id=feed2.id),
    ]

    for new_job in new_refresh_jobs:
        job = await repo.get_or_create(new_job)
        assert job.id is not None
        assert job.feed_id == new_job.feed_id
        assert job.state == FeedRefreshJobState.pending
        assert job.created_at is not None

    db_row1, db_row2 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id.asc())
    )

    assert db_row1["feed_id"] == feed1.id
    assert db_row1["state"] == 1

    assert db_row2["feed_id"] == feed2.id
    assert db_row2["state"] == 1


async def test_get_or_create_feed_job_already_exists(
    repo: PostgresFeedRefreshJobRepository,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    existing_job, *_ = await insert_refresh_jobs(NewFeedRefreshJob(feed_id=feed.id))

    refresh_job = await repo.get_or_create(
        NewFeedRefreshJob(feed_id=feed.id),
    )
    assert refresh_job.id == existing_job.id

    db_rows = await fetchmany(sa.select(mdl.FeedRefreshJob))
    assert len(db_rows) == 1


async def test_get_or_create_create_feed_does_not_exist(
    repo: PostgresFeedRefreshJobRepository,
) -> None:
    with pytest.raises(RefreshJobNoFeedError):
        await repo.get_or_create(NewFeedRefreshJob(feed_id=9999))


async def test_update_ok(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
        NewFeedFactory.build(url="https://example.com/feed.atom"),
    )

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, retries=4),
        NewFeedRefreshJob(feed_id=feed2.id, retries=2),
        NewFeedRefreshJob(feed_id=feed3.id, retries=1),
    )

    updated1 = await repo.update(
        job_id=job1.id,
        updates=FeedRefreshJobUpdates(retries=5),
    )
    assert updated1.id == job1.id
    assert updated1.retries == 5

    updated2 = await repo.update(
        job_id=job2.id,
        updates=FeedRefreshJobUpdates(retries=3),
    )
    assert updated2.id == job2.id
    assert updated2.retries == 3

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id.asc())
    )

    assert db_row1["id"] == job1.id
    assert db_row1["retries"] == 5

    assert db_row2["id"] == job2.id
    assert db_row2["retries"] == 3

    assert db_row3["id"] == job3.id
    assert db_row3["retries"] == 1


async def test_update_invalid_job(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    job, *_ = await insert_refresh_jobs(NewFeedRefreshJob(feed_id=feed.id, retries=1))

    with pytest.raises(RefreshJobNotFoundError):
        await repo.update(
            job_id=99999,
            updates=FeedRefreshJobUpdates(retries=2),
        )

    # Check that the real job wasn't affected
    db_row = await fetchone(sa.select(mdl.FeedRefreshJob))
    assert db_row["retries"] == 1


async def test_transit_state_ok(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed.id, state=FeedRefreshJobState.pending)
    )

    updated = await repo.transit_state(
        job_id=job.id,
        old_state=FeedRefreshJobState.pending,
        new_state=FeedRefreshJobState.complete,
    )
    assert updated.id == job.id
    assert updated.state == FeedRefreshJobState.complete

    db_row = await fetchone(sa.select(mdl.FeedRefreshJob))
    assert db_row["id"] == job.id
    assert db_row["state"] == 3

    updated = await repo.transit_state(
        job_id=job.id,
        old_state=FeedRefreshJobState.complete,
        new_state=FeedRefreshJobState.pending,
    )
    assert updated.id == job.id
    assert updated.state == FeedRefreshJobState.pending

    db_row = await fetchone(sa.select(mdl.FeedRefreshJob))
    assert db_row["id"] == job.id
    assert db_row["state"] == 1


async def test_transit_state_invalid_transition(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed.id, state=FeedRefreshJobState.in_progress)
    )

    with pytest.raises(RefreshJobStateTransitionError):
        await repo.transit_state(
            job_id=job.id,
            old_state=FeedRefreshJobState.pending,
            new_state=FeedRefreshJobState.complete,
        )

    db_row = await fetchone(sa.select(mdl.FeedRefreshJob))
    assert db_row["id"] == job.id
    assert db_row["state"] == 2


async def test_transit_state_invalid_job(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: Callable,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    job, *_ = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed.id, state=FeedRefreshJobState.pending)
    )

    with pytest.raises(RefreshJobStateTransitionError):
        await repo.transit_state(
            job_id=9999,
            old_state=FeedRefreshJobState.pending,
            new_state=FeedRefreshJobState.complete,
        )

    db_row = await fetchone(sa.select(mdl.FeedRefreshJob))
    assert db_row["id"] == job.id
    assert db_row["state"] == 1
