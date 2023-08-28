from datetime import UTC, datetime
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
)
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import feed_refresh_job as job_repo
from awesome_rss_reader.core.usecase.refresh_feed import (
    FeedNotFoundError,
    RefreshFeedInput,
    RefreshFeedOutput,
    RefreshFeedUseCase,
)
from tests.factories import FeedFactory, FeedRefreshJobFactory


@pytest.fixture()
def uc(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
) -> RefreshFeedUseCase:
    return container.use_cases.refresh_feed()


@mock.patch(
    "awesome_rss_reader.core.usecase.refresh_feed.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_happy_path(
    container: Container,
    feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: RefreshFeedUseCase,
) -> None:
    feed = FeedFactory.build()
    refresh_job = FeedRefreshJobFactory.build(
        feed_id=feed.id,
        state=FeedRefreshJobState.failed,
    )

    feed_repository.get_by_id.return_value = feed
    job_repository.get_or_create.return_value = refresh_job
    job_repository.transit_state.return_value = refresh_job
    job_repository.update.return_value = refresh_job

    uc_input = RefreshFeedInput(feed_id=feed.id)
    uc_result = await uc.execute(uc_input)

    assert uc_result == RefreshFeedOutput(refresh_job=refresh_job)

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    job_repository.get_or_create.assert_called_once()
    created_job = job_repository.get_or_create.call_args[0][0]
    assert created_job.feed_id == feed.id
    assert created_job.state == FeedRefreshJobState.pending

    job_repository.transit_state.assert_called_once_with(
        job_id=refresh_job.id,
        old_state=FeedRefreshJobState.failed,
        new_state=FeedRefreshJobState.pending,
    )
    job_repository.update.assert_called_once_with(
        job_id=refresh_job.id,
        updates=FeedRefreshJobUpdates(
            retries=0, execute_after=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC)
        ),
    )


@pytest.mark.parametrize(
    "state",
    [
        FeedRefreshJobState.pending,
        FeedRefreshJobState.in_progress,
    ],
)
async def test_skip_refresh_if_job_in_progress(
    container: Container,
    feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: RefreshFeedUseCase,
    state: FeedRefreshJobState,
) -> None:
    feed = FeedFactory.build()
    refresh_job = FeedRefreshJobFactory.build(
        feed_id=feed.id,
        state=state,
    )

    feed_repository.get_by_id.return_value = feed
    job_repository.get_or_create.return_value = refresh_job

    uc_input = RefreshFeedInput(feed_id=feed.id)
    uc_result = await uc.execute(uc_input)

    assert uc_result == RefreshFeedOutput(refresh_job=refresh_job)

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    job_repository.get_or_create.assert_called_once()
    job_repository.transit_state.assert_not_called()
    job_repository.update.assert_not_called()


async def test_feed_not_found(
    container: Container,
    feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: RefreshFeedUseCase,
) -> None:
    feed_repository.get_by_id.side_effect = feed_repo.FeedNotFoundError

    uc_input = RefreshFeedInput(feed_id=1)
    with pytest.raises(FeedNotFoundError):
        await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(uc_input.feed_id)
    job_repository.get_or_create.assert_not_called()
    job_repository.transit_state.assert_not_called()
    job_repository.update.assert_not_called()


async def test_state_transition_failed(
    container: Container,
    feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: RefreshFeedUseCase,
) -> None:
    feed = FeedFactory.build()
    refresh_job = FeedRefreshJobFactory.build(
        feed_id=feed.id,
        state=FeedRefreshJobState.failed,
    )

    feed_repository.get_by_id.return_value = feed
    job_repository.get_or_create.return_value = refresh_job
    job_repository.transit_state.side_effect = job_repo.RefreshJobStateTransitionError
    job_repository.update.return_value = refresh_job

    uc_input = RefreshFeedInput(feed_id=feed.id)
    uc_result = await uc.execute(uc_input)

    assert uc_result == RefreshFeedOutput(refresh_job=refresh_job)

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    job_repository.get_or_create.assert_called_once()
    job_repository.transit_state.assert_called_once_with(
        job_id=refresh_job.id,
        old_state=FeedRefreshJobState.failed,
        new_state=FeedRefreshJobState.pending,
    )
    job_repository.update.assert_not_called()
