from datetime import UTC, datetime
from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.create_feed import (
    CreateFeedInput,
    CreateFeedOutput,
    CreateFeedUseCase,
)
from tests.factories import FeedFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=CreateFeedUseCase)

    with container.use_cases.create_feed.override(uc):
        yield uc


async def test_create_feed_happy_path(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    feed = FeedFactory.build(
        id=1,
        url="https://example.com/feed.xml",
        title="Example Feed",
        refreshed_at=None,
        created_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
    )
    uc.execute.return_value = CreateFeedOutput(feed=feed)

    payload = {"url": "https://example.com/feed.xml"}
    resp = user_api_client.post("/api/feeds", json=payload)
    assert resp.status_code == 202

    resp_json = resp.json()
    assert resp_json == {
        "id": 1,
        "url": "https://example.com/feed.xml",
        "title": "Example Feed",
        "created_at": "2006-01-02T15:04:05.999999Z",
        "refreshed_at": None,
    }

    uc.execute.assert_called_once_with(
        CreateFeedInput(
            user_uid=user.uid,
            url="https://example.com/feed.xml",
        )
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/feed.xml",
        "https://example.com/feed.rss",
        "https://feeds.simplecast.com/54nAGcIl",
        "https://www.makeuseof.com/feed/",
        "https://ultimateclassicrock.com/feed/",
    ],
)
async def test_create_feed_valid_input(
    uc: mock.Mock,
    user_api_client: TestClient,
    url: str,
) -> None:
    feed = FeedFactory.build(
        id=1,
        url=url,
        title="Example Feed",
        refreshed_at=None,
        created_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
    )
    uc.execute.return_value = CreateFeedOutput(feed=feed)

    resp = user_api_client.post("/api/feeds", json={"url": url})
    assert resp.status_code == 202


@pytest.mark.parametrize(
    "url",
    [
        "foobar/",
        "https://",
        "example.com/",
        "ftp://example.com/",
    ],
)
async def test_create_feed_invalid_input(
    uc: mock.Mock,
    user_api_client: TestClient,
    url: str,
) -> None:
    resp = user_api_client.post("/api/feeds", json={"url": url})
    assert resp.status_code == 422

    uc.execute.assert_not_called()
