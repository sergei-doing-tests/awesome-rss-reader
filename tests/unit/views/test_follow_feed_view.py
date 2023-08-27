from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.follow_feed import (
    FeedNotFoundError,
    FollowFeedInput,
    FollowFeedOutput,
    FollowFeedUseCase,
)
from tests.factories.user_feed import UserFeedFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=FollowFeedUseCase)

    with container.use_cases.follow_feed.override(uc):
        yield uc


async def test_follow_feed_happy_path(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    user_feed = UserFeedFactory.build(
        user_uid=user.uid,
        feed_id=1,
    )
    uc.execute.return_value = FollowFeedOutput(user_feed=user_feed)

    resp = user_api_client.put("/api/feeds/1/follow")
    assert resp.status_code == 204

    uc.execute.assert_called_once_with(FollowFeedInput(user_uid=user.uid, feed_id=1))


async def test_follow_feed_feed_not_found(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.side_effect = FeedNotFoundError

    resp = user_api_client.put("/api/feeds/1/follow")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Feed not found"}

    uc.execute.assert_called_once_with(FollowFeedInput(user_uid=user.uid, feed_id=1))
