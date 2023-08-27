import uuid
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import user_feed as user_feed_repo
from awesome_rss_reader.core.usecase.follow_feed import (
    FeedNotFoundError,
    FollowFeedInput,
    FollowFeedUseCase,
)
from tests.factories.feed import FeedFactory
from tests.factories.user_feed import UserFeedFactory


@pytest.fixture()
def uc(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
) -> FollowFeedUseCase:
    return container.use_cases.follow_feed()


async def test_happy_path(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: FollowFeedUseCase,
) -> None:
    user_uid = uuid.uuid4()

    feed = FeedFactory.build()
    user_feed = UserFeedFactory.build(user_uid=user_uid, feed_id=feed.id)

    feed_repository.get_by_id.return_value = feed
    user_feed_repository.get_or_create.return_value = user_feed

    uc_input = FollowFeedInput(user_uid=user_uid, feed_id=feed.id)
    uc_result = await uc.execute(uc_input)
    assert uc_result.user_feed == user_feed

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    user_feed_repository.get_or_create.assert_called_once_with(
        user_feed_repo.NewUserFeed(feed_id=feed.id, user_uid=user_uid)
    )


async def test_feed_not_found(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: FollowFeedUseCase,
) -> None:
    feed_repository.get_by_id.side_effect = feed_repo.FeedNotFoundError

    uc_input = FollowFeedInput(user_uid=uuid.uuid4(), feed_id=1)
    with pytest.raises(FeedNotFoundError):
        await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(uc_input.feed_id)
    user_feed_repository.get_or_create.assert_not_called()


async def test_feed_not_found_on_get_or_create(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: FollowFeedUseCase,
) -> None:
    feed = FeedFactory.build()

    feed_repository.get_by_id.return_value = feed
    user_feed_repository.get_or_create.side_effect = user_feed_repo.UserFeedNoFeedError

    uc_input = FollowFeedInput(user_uid=uuid.uuid4(), feed_id=1)
    with pytest.raises(FeedNotFoundError):
        await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(uc_input.feed_id)
    user_feed_repository.get_or_create.assert_called_once_with(
        user_feed_repo.NewUserFeed(feed_id=feed.id, user_uid=uc_input.user_uid)
    )
