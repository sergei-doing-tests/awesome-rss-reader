from datetime import UTC, datetime
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobFiltering,
    FeedRefreshJobOrdering,
    FeedRefreshJobState,
)
from awesome_rss_reader.core.usecase.schedule_feed_update import (
    ScheduleFeedUpdateInput,
    ScheduleFeedUpdateUseCase,
)
from tests.factories import FeedRefreshJobFactory


@pytest.fixture()
def uc(container: Container, job_repository: mock.Mock) -> ScheduleFeedUpdateUseCase:
    return container.use_cases.schedule_feed_update()


@mock.patch(
    "awesome_rss_reader.core.usecase.schedule_feed_update.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_happy_path(
    now_aware_mock: mock.Mock,
    job_repository: mock.Mock,
    uc: ScheduleFeedUpdateUseCase,
) -> None:
    jobs = [
        FeedRefreshJobFactory.build(
            id=i,
            state=FeedRefreshJobState.complete,
        )
        for i in range(1, 6)
    ]

    job_repository.get_list.return_value = jobs
    job_repository.transit_state_batch.return_value = jobs

    uc_input = ScheduleFeedUpdateInput(batch_size=100)
    await uc.execute(uc_input)

    job_repository.get_list.assert_called_once_with(
        filter_by=FeedRefreshJobFiltering(
            state=FeedRefreshJobState.complete,
            state_changed_before=datetime(2006, 1, 2, 14, 59, 5, 999999, tzinfo=UTC),
        ),
        order_by=FeedRefreshJobOrdering.state_changed_at_asc,
        offset=0,
        limit=100,
    )
    job_repository.transit_state_batch.assert_called_once_with(
        job_ids=[1, 2, 3, 4, 5],
        old_state=FeedRefreshJobState.complete,
        new_state=FeedRefreshJobState.pending,
    )


@mock.patch(
    "awesome_rss_reader.core.usecase.schedule_feed_update.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_no_jobs_to_schedule(
    now_aware_mock: mock.Mock,
    job_repository: mock.Mock,
    uc: ScheduleFeedUpdateUseCase,
) -> None:
    job_repository.get_list.return_value = []

    uc_input = ScheduleFeedUpdateInput(batch_size=100)
    await uc.execute(uc_input)

    job_repository.get_list.assert_called_once_with(
        filter_by=FeedRefreshJobFiltering(
            state=FeedRefreshJobState.complete,
            state_changed_before=datetime(2006, 1, 2, 14, 59, 5, 999999, tzinfo=UTC),
        ),
        order_by=FeedRefreshJobOrdering.state_changed_at_asc,
        offset=0,
        limit=100,
    )
    job_repository.transit_state_batch.assert_not_called()


@mock.patch(
    "awesome_rss_reader.core.usecase.schedule_feed_update.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_no_jobs_scheduled(
    now_aware_mock: mock.Mock,
    job_repository: mock.Mock,
    uc: ScheduleFeedUpdateUseCase,
) -> None:
    jobs = [
        FeedRefreshJobFactory.build(
            id=i,
            state=FeedRefreshJobState.complete,
        )
        for i in range(1, 6)
    ]

    job_repository.get_list.return_value = jobs
    job_repository.transit_state_batch.return_value = []

    uc_input = ScheduleFeedUpdateInput(batch_size=100)
    await uc.execute(uc_input)

    job_repository.get_list.assert_called_once_with(
        filter_by=FeedRefreshJobFiltering(
            state=FeedRefreshJobState.complete,
            state_changed_before=datetime(2006, 1, 2, 14, 59, 5, 999999, tzinfo=UTC),
        ),
        order_by=FeedRefreshJobOrdering.state_changed_at_asc,
        offset=0,
        limit=100,
    )
    job_repository.transit_state_batch.assert_called_once_with(
        job_ids=[1, 2, 3, 4, 5],
        old_state=FeedRefreshJobState.complete,
        new_state=FeedRefreshJobState.pending,
    )
