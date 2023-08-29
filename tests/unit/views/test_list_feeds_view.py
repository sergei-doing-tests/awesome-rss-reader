from datetime import UTC, datetime
from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.list_user_feeds import (
    ListUserFeedsInput,
    ListUserFeedsOutput,
    ListUserFollowedFeedsUseCase,
)
from tests.factories import FeedFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=ListUserFollowedFeedsUseCase)

    with container.use_cases.list_followed_feeds.override(uc):
        yield uc


async def test_list_feeds_happy_path(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    feeds = [
        FeedFactory.build(
            id=1,
            url="https://example.com/feed.xml",
            title=None,
            published_at=None,
            created_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
        FeedFactory.build(
            id=2,
            url="https://example.com/feed.rss",
            title="Example Feed",
            published_at=datetime(2006, 1, 2, 20, 20, 20, 999999, tzinfo=UTC),
            created_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
    ]
    uc.execute.return_value = ListUserFeedsOutput(feeds=feeds)

    resp = user_api_client.get("/api/feeds")
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": 1,
            "url": "https://example.com/feed.xml",
            "title": None,
            "created_at": "2006-01-02T15:04:05.999999Z",
            "published_at": None,
        },
        {
            "id": 2,
            "url": "https://example.com/feed.rss",
            "title": "Example Feed",
            "created_at": "2006-01-02T15:04:05.999999Z",
            "published_at": "2006-01-02T20:20:20.999999Z",
        },
    ]

    uc.execute.assert_called_once_with(ListUserFeedsInput(user_uid=user.uid, offset=0, limit=100))


async def test_list_feeds_pagination(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    feeds = [
        FeedFactory.build(
            id=1,
            url="https://example.com/feed.xml",
            title=None,
            published_at=None,
            created_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
    ]
    uc.execute.return_value = ListUserFeedsOutput(feeds=feeds)

    resp = user_api_client.get("/api/feeds", params={"offset": 1, "limit": 1})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": 1,
            "url": "https://example.com/feed.xml",
            "title": None,
            "created_at": "2006-01-02T15:04:05.999999Z",
            "published_at": None,
        },
    ]

    uc.execute.assert_called_once_with(ListUserFeedsInput(user_uid=user.uid, offset=1, limit=1))


async def test_list_feeds_empty(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.return_value = ListUserFeedsOutput(feeds=[])

    resp = user_api_client.get("/api/feeds")
    assert resp.status_code == 200
    assert resp.json() == []

    uc.execute.assert_called_once_with(ListUserFeedsInput(user_uid=user.uid, offset=0, limit=100))
