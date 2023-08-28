from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.usecase.refresh_feed import (
    FeedNotFoundError,
    RefreshFeedInput,
    RefreshFeedOutput,
    RefreshFeedUseCase,
)
from tests.factories import FeedRefreshJobFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=RefreshFeedUseCase)

    with container.use_cases.refresh_feed.override(uc):
        yield uc


async def test_refresh_feed_happy_path(
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    refresh_job = FeedRefreshJobFactory.build(
        feed_id=1,
    )
    uc.execute.return_value = RefreshFeedOutput(refresh_job=refresh_job)

    resp = user_api_client.post("/api/feeds/1/refresh")
    assert resp.status_code == 202

    uc.execute.assert_called_once_with(RefreshFeedInput(feed_id=1))


async def test_refreshed_feed_does_not_exist(
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.side_effect = FeedNotFoundError

    resp = user_api_client.post("/api/feeds/1/refresh")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Feed not found"}

    uc.execute.assert_called_once_with(RefreshFeedInput(feed_id=1))
