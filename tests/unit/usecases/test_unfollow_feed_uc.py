import uuid
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.repository import user_feed as user_feed_repo
from awesome_rss_reader.core.usecase.unfollow_feed import (
    FeedNotFoundError,
    UnfollowFeedInput,
    UnfollowFeedUseCase,
)
from tests.factories import FeedFactory, UserFeedFactory


@pytest.fixture()
def uc(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
) -> UnfollowFeedUseCase:
    return container.use_cases.unfollow_feed()


async def test_happy_path(
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: UnfollowFeedUseCase,
) -> None:
    user_uid = uuid.uuid4()

    feed = FeedFactory.build()
    user_feed = UserFeedFactory.build(user_uid=user_uid, feed_id=feed.id)

    feed_repository.get_by_id.return_value = feed
    user_feed_repository.get_for_user_and_feed.return_value = user_feed
    user_feed_repository.delete.return_value = None

    uc_input = UnfollowFeedInput(user_uid=user_uid, feed_id=feed.id)
    await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    user_feed_repository.get_for_user_and_feed.assert_called_once_with(
        user_uid=user_uid, feed_id=feed.id
    )
    user_feed_repository.delete.assert_called_once_with(user_feed.id)


async def test_feed_not_found(
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: UnfollowFeedUseCase,
) -> None:
    feed_repository.get_by_id.side_effect = feed_repo.FeedNotFoundError

    uc_input = UnfollowFeedInput(user_uid=uuid.uuid4(), feed_id=1)
    with pytest.raises(FeedNotFoundError):
        await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(1)
    user_feed_repository.get_for_user_and_feed.assert_not_called()
    user_feed_repository.delete.assert_not_called()


async def test_user_feed_not_found(
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
    uc: UnfollowFeedUseCase,
) -> None:
    user_uid = uuid.uuid4()
    feed = FeedFactory.build()

    feed_repository.get_by_id.return_value = feed
    user_feed_repository.get_for_user_and_feed.side_effect = user_feed_repo.UserFeedNotFoundError

    uc_input = UnfollowFeedInput(user_uid=user_uid, feed_id=feed.id)
    await uc.execute(uc_input)

    feed_repository.get_by_id.assert_called_once_with(feed.id)
    user_feed_repository.get_for_user_and_feed.assert_called_once_with(
        user_uid=user_uid, feed_id=feed.id
    )
    user_feed_repository.delete.assert_not_called()
