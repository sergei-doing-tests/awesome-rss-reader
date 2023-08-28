import uuid
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository import feed as feed_repo
from awesome_rss_reader.core.usecase.list_user_feeds import (
    ListUserFeedsInput,
    ListUserFollowedFeedsUseCase,
)
from tests.factories import FeedFactory


@pytest.fixture()
def uc(
    container: Container,
    feed_repository: mock.Mock,
    user_feed_repository: mock.Mock,
) -> ListUserFollowedFeedsUseCase:
    return container.use_cases.list_followed_feeds()


async def test_happy_path(
    container: Container,
    feed_repository: mock.Mock,
    uc: ListUserFollowedFeedsUseCase,
) -> None:
    user_uid = uuid.uuid4()
    feeds = FeedFactory.batch(5)

    feed_repository.get_list.return_value = feeds

    uc_input = ListUserFeedsInput(user_uid=user_uid, offset=0, limit=100)
    uc_result = await uc.execute(uc_input)
    assert uc_result.feeds == feeds

    feed_repository.get_list.assert_called_once_with(
        followed_by=user_uid,
        order_by=feed_repo.FeedOrdering.refreshed_at_desc,
        offset=0,
        limit=100,
    )


async def test_empty_list(
    container: Container,
    feed_repository: mock.Mock,
    uc: ListUserFollowedFeedsUseCase,
) -> None:
    user_uid = uuid.uuid4()

    feed_repository.get_list.return_value = []

    uc_input = ListUserFeedsInput(user_uid=user_uid, offset=0, limit=100)
    uc_result = await uc.execute(uc_input)

    assert uc_result.feeds == []

    feed_repository.get_list.assert_called_once_with(
        followed_by=user_uid,
        order_by=feed_repo.FeedOrdering.refreshed_at_desc,
        offset=0,
        limit=100,
    )
