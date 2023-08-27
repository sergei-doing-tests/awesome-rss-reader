import uuid
from datetime import UTC, datetime
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed import NewFeed
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
)
from awesome_rss_reader.core.entity.user_feed import NewUserFeed
from awesome_rss_reader.core.repository.feed_refresh_job import RefreshJobStateTransitionError
from awesome_rss_reader.core.usecase.create_feed import CreateFeedInput, CreateFeedUseCase
from tests.factories.feed import FeedFactory
from tests.factories.feed_refresh_job import FeedRefreshJobFactory
from tests.factories.user_feed import UserFeedFactory


@pytest.fixture()
def uc(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    job_repository: mock.Mock,
) -> CreateFeedUseCase:
    return container.use_cases.create_feed()


async def test_happy_path(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: CreateFeedUseCase,
) -> None:
    user_uid = uuid.uuid4()
    url = "https://example.com/feed.xml"

    feed = FeedFactory.build(url=url)
    user_feed = UserFeedFactory.build(user_uid=user_uid, feed_id=feed.id)
    refresh_job = FeedRefreshJobFactory.build(feed_id=feed.id)

    feed_repository.get_or_create.return_value = feed
    user_feed_repository.get_or_create.return_value = user_feed
    job_repository.get_or_create.return_value = refresh_job

    uc_input = CreateFeedInput(user_uid=user_uid, url=url)
    uc_result = await uc.execute(uc_input)

    assert uc_result.feed == feed

    feed_repository.get_or_create.assert_called_once_with(NewFeed(url=url))
    user_feed_repository.get_or_create.assert_called_once_with(
        NewUserFeed(user_uid=user_uid, feed_id=feed.id)
    )
    job_repository.get_or_create.assert_called_once()
    created_job = job_repository.get_or_create.call_args[0][0]
    assert created_job.feed_id == feed.id
    assert created_job.state == FeedRefreshJobState.pending

    job_repository.transit_state.assert_not_called()
    job_repository.update.assert_not_called()


@pytest.mark.parametrize(
    "job_state, has_transition",
    [
        (FeedRefreshJobState.pending, False),
        (FeedRefreshJobState.in_progress, False),
        (FeedRefreshJobState.complete, True),
        (FeedRefreshJobState.failed, True),
    ],
)
@mock.patch(
    "awesome_rss_reader.core.usecase.create_feed.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_refresh_job_for_existing_feeds(
    now_aware_mock: mock.Mock,
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: CreateFeedUseCase,
    job_state: FeedRefreshJobState,
    has_transition: bool,
) -> None:
    feed = FeedFactory.build(url="https://example.com/feed.xml")
    user_feed = UserFeedFactory.build(feed_id=feed.id)
    refresh_job = FeedRefreshJobFactory.build(feed_id=feed.id, state=job_state)

    feed_repository.get_or_create.return_value = feed
    user_feed_repository.get_or_create.return_value = user_feed
    job_repository.get_or_create.return_value = refresh_job
    job_repository.transit_state.return_value = refresh_job
    job_repository.update.return_value = refresh_job

    await uc.execute(
        CreateFeedInput(
            user_uid=user_feed.user_uid,
            url=feed.url,
        )
    )

    if has_transition:
        job_repository.transit_state.assert_called_once_with(
            job_id=refresh_job.id,
            old_state=job_state,
            new_state=FeedRefreshJobState.pending,
        )
        job_repository.update.assert_called_once_with(
            job_id=refresh_job.id,
            updates=FeedRefreshJobUpdates(
                retries=0,
                execute_after=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
            ),
        )
    else:
        job_repository.transit_state.assert_not_called()
        job_repository.update.assert_not_called()


async def test_job_state_transition_error_is_handled(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    job_repository: mock.Mock,
    uc: CreateFeedUseCase,
) -> None:
    feed = FeedFactory.build(url="https://example.com/feed.xml")
    user_feed = UserFeedFactory.build(feed_id=feed.id)
    refresh_job = FeedRefreshJobFactory.build(feed_id=feed.id, state=FeedRefreshJobState.complete)

    feed_repository.get_or_create.return_value = feed
    user_feed_repository.get_or_create.return_value = user_feed
    job_repository.get_or_create.return_value = refresh_job

    job_repository.transit_state.side_effect = RefreshJobStateTransitionError()

    await uc.execute(CreateFeedInput(user_uid=user_feed.user_uid, url=feed.url))

    job_repository.transit_state.assert_called_once_with(
        job_id=refresh_job.id,
        old_state=FeedRefreshJobState.complete,
        new_state=FeedRefreshJobState.pending,
    )
    job_repository.update.assert_not_called()
