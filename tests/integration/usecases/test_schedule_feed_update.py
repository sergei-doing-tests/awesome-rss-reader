from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJobState, NewFeedRefreshJob
from awesome_rss_reader.core.usecase.schedule_feed_update import (
    ScheduleFeedUpdateInput,
    ScheduleFeedUpdateUseCase,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    InsertFeedsFixtureT,
    InsertRefreshJobsFixtureT,
)


@pytest.fixture()
def uc(container: Container, postgres_database: AsyncEngine) -> ScheduleFeedUpdateUseCase:
    return container.use_cases.schedule_feed_update()


async def test_schedule_feed_update_happy_path(
    db: AsyncEngine,
    uc: ScheduleFeedUpdateUseCase,
    insert_feeds: InsertFeedsFixtureT,
    insert_refresh_jobs: InsertRefreshJobsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    now = now_aware()
    then = now - timedelta(minutes=15)

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

    job1, job2, job3 = await insert_refresh_jobs(
        NewFeedRefreshJob(
            feed_id=feed1.id,
            state=FeedRefreshJobState.complete,
            execute_after=now + timedelta(minutes=10),
        ),
        NewFeedRefreshJob(
            feed_id=feed2.id,
            state=FeedRefreshJobState.in_progress,
            execute_after=now,
        ),
        NewFeedRefreshJob(
            feed_id=feed3.id,
            state=FeedRefreshJobState.complete,
            execute_after=now - timedelta(minutes=20),
        ),
    )

    async with db.begin() as conn:
        await conn.execute(
            sa.update(mdl.FeedRefreshJob)
            .where(mdl.FeedRefreshJob.c.id.in_([job1.id, job2.id]))
            .values(state_changed_at=then)
        )

    uc_input = ScheduleFeedUpdateInput(batch_size=50)
    await uc.execute(uc_input)

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.FeedRefreshJob).order_by(mdl.FeedRefreshJob.c.id)
    )

    assert db_row1["state"] == FeedRefreshJobState.pending
    assert db_row1["state_changed_at"] > job1.state_changed_at

    assert db_row2["state"] == FeedRefreshJobState.in_progress
    assert db_row2["state_changed_at"] == then

    assert db_row3["state"] == FeedRefreshJobState.complete
    assert db_row3["state_changed_at"] == job3.state_changed_at


async def test_schedule_feed_update_no_jobs(uc: ScheduleFeedUpdateUseCase) -> None:
    uc_input = ScheduleFeedUpdateInput(batch_size=50)
    # no exception
    await uc.execute(uc_input)
