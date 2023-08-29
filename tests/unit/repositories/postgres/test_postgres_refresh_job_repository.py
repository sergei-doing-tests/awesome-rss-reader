from collections.abc import Callable
from datetime import timedelta
from typing import Optional

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobFiltering,
    FeedRefreshJobOrdering,
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
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresFeedRefreshJobRepository:
    return PostgresFeedRefreshJobRepository(db=db)


@pytest_asyncio.fixture()
async def feed(insert_feeds: InsertFeedsFixtureT) -> Feed:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    return feed


async def test_get_by_id(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
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
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    feed: Feed,
    job_id: int,
) -> None:
    await insert_refresh_jobs(NewFeedRefreshJob(feed_id=feed.id))

    with pytest.raises(RefreshJobNotFoundError):
        await repo.get_by_id(job_id)


async def test_get_by_feed_id(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
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
    insert_feeds: InsertFeedsFixtureT,
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
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    feed: Feed,
) -> None:
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


@pytest.mark.parametrize(
    "filter_by_factory, order_by, limit, offset, expected_feed_names",
    [
        # order by id
        (
            None,
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            ["Feed 1", "Feed 2", "Feed 3"],
        ),
        # order by execute_after
        (
            None,
            FeedRefreshJobOrdering.execute_after_asc,
            10,
            0,
            ["Feed 3", "Feed 2", "Feed 1"],
        ),
        # order by state_changed_at
        (
            None,
            FeedRefreshJobOrdering.state_changed_at_asc,
            10,
            0,
            ["Feed 3", "Feed 1", "Feed 2"],
        ),
        # limit and offset
        (
            None,
            FeedRefreshJobOrdering.id_asc,
            2,
            1,
            ["Feed 2", "Feed 3"],
        ),
        # filter by state
        (
            lambda now: FeedRefreshJobFiltering(state=FeedRefreshJobState.in_progress),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            ["Feed 2", "Feed 3"],
        ),
        (
            lambda now: FeedRefreshJobFiltering(state=FeedRefreshJobState.failed),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            [],
        ),
        # filter by state, apply limit and offset
        (
            lambda now: FeedRefreshJobFiltering(state=FeedRefreshJobState.in_progress),
            FeedRefreshJobOrdering.id_asc,
            1,
            1,
            ["Feed 3"],
        ),
        # filter by state_changed_before
        (
            lambda now: FeedRefreshJobFiltering(state_changed_before=now - timedelta(minutes=5)),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            ["Feed 3"],
        ),
        # filter by state_changed_before and state
        (
            lambda now: FeedRefreshJobFiltering(
                state=FeedRefreshJobState.in_progress,
                state_changed_before=now - timedelta(minutes=5),
            ),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            ["Feed 3"],
        ),
        # filter by execute_before
        (
            lambda now: FeedRefreshJobFiltering(execute_before=now - timedelta(minutes=5)),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            ["Feed 3"],
        ),
        (
            lambda now: FeedRefreshJobFiltering(execute_before=now + timedelta(seconds=1)),
            FeedRefreshJobOrdering.execute_after_asc,
            10,
            0,
            ["Feed 3", "Feed 2"],
        ),
        (
            lambda now: FeedRefreshJobFiltering(
                state=FeedRefreshJobState.complete,
                state_changed_before=now - timedelta(minutes=5),
            ),
            FeedRefreshJobOrdering.id_asc,
            10,
            0,
            [],
        ),
    ],
)
async def test_get_list(
    db: AsyncEngine,
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    filter_by_factory: Optional[Callable],  # noqa: UP007
    order_by: FeedRefreshJobOrdering,
    limit: int,
    offset: int,
    expected_feed_names: list[str],
) -> None:
    now = now_aware()

    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(
            url="https://example.com/feed.xml",
            title="Feed 1",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.rss",
            title="Feed 2",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.atom",
            title="Feed 3",
        ),
    )
    feed_names = {feed.title: feed.id for feed in [feed1, feed2, feed3]}

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed1.id,
            state=FeedRefreshJobState.pending,
            execute_after=now + timedelta(minutes=5),
        ),
        NewFeedRefreshJob(
            feed_id=feed2.id,
            state=FeedRefreshJobState.in_progress,
            execute_after=now,
        ),
        NewFeedRefreshJob(
            feed_id=feed3.id,
            state=FeedRefreshJobState.in_progress,
            execute_after=now - timedelta(minutes=20),
        ),
    )

    # update the state_changed_at for job3
    async with db.begin() as conn:
        await conn.execute(
            sa.update(mdl.FeedRefreshJob)
            .where(mdl.FeedRefreshJob.c.id == job3.id)
            .values(state_changed_at=now - timedelta(minutes=10))
        )

    jobs = await repo.get_list(
        order_by=order_by,
        filter_by=filter_by_factory(now) if filter_by_factory else None,
        limit=limit,
        offset=offset,
    )

    expected_feed_ids = [feed_names[name] for name in expected_feed_names]
    actual_feed_ids = [job.feed_id for job in jobs]

    assert actual_feed_ids == expected_feed_ids


async def test_update_ok(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
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
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    feed: Feed,
) -> None:
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
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    feed: Feed,
) -> None:
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
    assert db_row["state_changed_at"] > job.state_changed_at


async def test_transit_state_invalid_transition(
    repo: PostgresFeedRefreshJobRepository,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    feed: Feed,
) -> None:
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
    assert db_row["state_changed_at"] == job.state_changed_at


async def test_transit_state_invalid_job(
    repo: PostgresFeedRefreshJobRepository,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchone: FetchOneFixtureT,
    feed: Feed,
) -> None:
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


async def test_transit_state_batch_ok(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
        NewFeedFactory.build(url="https://example.com/feed.atom"),
    )

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed2.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed3.id, state=FeedRefreshJobState.pending),
    )

    updated_jobs = await repo.transit_state_batch(
        job_ids=[job1.id, job2.id, job3.id],
        old_state=FeedRefreshJobState.pending,
        new_state=FeedRefreshJobState.in_progress,
    )
    assert [j.id for j in updated_jobs] == [job1.id, job2.id, job3.id]

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id.asc())
    )
    assert db_row1["state"] == 2
    assert db_row1["state_changed_at"] > job1.state_changed_at

    assert db_row2["state"] == 2
    assert db_row2["state_changed_at"] > job2.state_changed_at

    assert db_row3["state"] == 2
    assert db_row3["state_changed_at"] > job3.state_changed_at


async def test_transit_state_batch_partial(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
        NewFeedFactory.build(url="https://example.com/feed.atom"),
    )

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed2.id, state=FeedRefreshJobState.in_progress),
        NewFeedRefreshJob(feed_id=feed3.id, state=FeedRefreshJobState.in_progress),
    )

    updated_jobs = await repo.transit_state_batch(
        job_ids=[job1.id, job2.id, job3.id],
        old_state=FeedRefreshJobState.in_progress,
        new_state=FeedRefreshJobState.complete,
    )
    assert [j.id for j in updated_jobs] == [job2.id, job3.id]

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id.asc())
    )
    assert db_row1["state"] == 1
    assert db_row1["state_changed_at"] == job1.state_changed_at

    assert db_row2["state"] == 3
    assert db_row2["state_changed_at"] > job2.state_changed_at

    assert db_row3["state"] == 3
    assert db_row3["state_changed_at"] > job3.state_changed_at


async def test_transit_state_batch_no_transitions(
    repo: PostgresFeedRefreshJobRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
        NewFeedFactory.build(url="https://example.com/feed.atom"),
    )

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(feed_id=feed1.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed2.id, state=FeedRefreshJobState.pending),
        NewFeedRefreshJob(feed_id=feed3.id, state=FeedRefreshJobState.complete),
    )

    updated_jobs = await repo.transit_state_batch(
        job_ids=[job1.id, job2.id, job3.id],
        old_state=FeedRefreshJobState.failed,
        new_state=FeedRefreshJobState.in_progress,
    )
    assert updated_jobs == []

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id.asc())
    )
    assert db_row1["state"] == 1
    assert db_row1["state_changed_at"] == job1.state_changed_at

    assert db_row2["state"] == 1
    assert db_row2["state_changed_at"] == job2.state_changed_at

    assert db_row3["state"] == 3
    assert db_row3["state_changed_at"] == job3.state_changed_at
