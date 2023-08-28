import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.list_feed_posts import (
    ListFeedPostsInput,
    ListFeedPostsOutput,
    ListFeedPostsUseCase,
)
from tests.factories import FeedPostFactory, UserFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=ListFeedPostsUseCase)

    with container.use_cases.list_feed_posts.override(uc):
        yield uc


async def test_list_posts_happy_path(user_api_client: TestClient, uc: mock.Mock) -> None:
    posts = [
        FeedPostFactory.build(
            id=1,
            title="The Best High DPI Gaming Mice",
            summary=(
                "Make sure you've got what it takes to beat your competitors "
                "with a high DPI gaming mouse designed for quick responses."
            ),
            url="https://example.com/1",
            feed_id=10,
            created_at=datetime(2021, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
            published_at=datetime(2021, 1, 2, 9, 8, 7, 999999, tzinfo=UTC),
        ),
        FeedPostFactory.build(
            id=2,
            title="Can ChatGPT Transform Healthcare?",
            summary=(
                "With so much potential across many industries, "
                "here's how ChatGPT might deliver transformative improvements in healthcare."
            ),
            feed_id=15,
            url="https://example.com/2",
            created_at=datetime(2020, 1, 1, 1, 1, 1, 999999, tzinfo=UTC),
            published_at=datetime(2019, 12, 31, 1, 1, 1, 999999, tzinfo=UTC),
        ),
    ]
    uc.execute.return_value = ListFeedPostsOutput(posts=posts)

    resp = user_api_client.get("/api/posts")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": 1,
            "title": "The Best High DPI Gaming Mice",
            "summary": (
                "Make sure you've got what it takes to beat your competitors "
                "with a high DPI gaming mouse designed for quick responses."
            ),
            "url": "https://example.com/1",
            "feed_id": 10,
            "created_at": "2021-01-02T15:04:05.999999Z",
            "published_at": "2021-01-02T09:08:07.999999Z",
        },
        {
            "id": 2,
            "title": "Can ChatGPT Transform Healthcare?",
            "summary": (
                "With so much potential across many industries, here's how "
                "ChatGPT might deliver transformative improvements in healthcare."
            ),
            "url": "https://example.com/2",
            "feed_id": 15,
            "created_at": "2020-01-01T01:01:01.999999Z",
            "published_at": "2019-12-31T01:01:01.999999Z",
        },
    ]

    uc.execute.assert_called_once_with(
        ListFeedPostsInput(
            followed_by=None,
            not_followed_by=None,
            read_by=None,
            not_read_by=None,
            feed_id=None,
            offset=0,
            limit=100,
        )
    )


@pytest.mark.parametrize(
    "query_params, expected_input",
    [
        (
            {},
            ListFeedPostsInput(
                followed_by=None,
                not_followed_by=None,
                read_by=None,
                not_read_by=None,
                feed_id=None,
                offset=0,
                limit=100,
            ),
        ),
        (
            {"offset": 10, "limit": 5},
            ListFeedPostsInput(
                followed_by=None,
                not_followed_by=None,
                read_by=None,
                not_read_by=None,
                feed_id=None,
                offset=10,
                limit=5,
            ),
        ),
        (
            {"read_status": "read"},
            ListFeedPostsInput(
                followed_by=None,
                not_followed_by=None,
                read_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                not_read_by=None,
                feed_id=None,
                offset=0,
                limit=100,
            ),
        ),
        (
            {"read_status": "unread", "limit": 20, "offset": 10},
            ListFeedPostsInput(
                followed_by=None,
                not_followed_by=None,
                read_by=None,
                not_read_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                feed_id=None,
                offset=10,
                limit=20,
            ),
        ),
        (
            {"follow_status": "following", "feed_id": 1000},
            ListFeedPostsInput(
                followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                not_followed_by=None,
                read_by=None,
                not_read_by=None,
                feed_id=1000,
                offset=0,
                limit=100,
            ),
        ),
        (
            {"follow_status": "not_following", "feed_id": 1000},
            ListFeedPostsInput(
                followed_by=None,
                not_followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                read_by=None,
                not_read_by=None,
                feed_id=1000,
                offset=0,
                limit=100,
            ),
        ),
    ],
)
async def test_list_posts_params(
    api_client_factory: Callable[[User], TestClient],
    uc: mock.Mock,
    query_params: dict[str, Any],
    expected_input: ListFeedPostsInput,
) -> None:
    user = UserFactory.build(uid=uuid.UUID("facade00-0000-4000-a000-000000000000"))
    api_client = api_client_factory(user)

    posts = FeedPostFactory.batch(2)
    uc.execute.return_value = ListFeedPostsOutput(posts=posts)

    resp = api_client.get("/api/posts", params=query_params)

    assert resp.status_code == 200
    assert len(resp.json()) == 2

    uc.execute.assert_called_once_with(expected_input)


@pytest.mark.parametrize(
    "query_params, error_detail",
    [
        # fmt: off
        (
            {"read_status": "reading"},
            "Input should be 'read' or 'unread'",
        ),
        (
            {"follow_status": "yes"},
            "Input should be 'following' or 'not_following'"),
        (
            {"feed_id": "yes"},
            "Input should be a valid integer, unable to parse string as an integer",
        ),
        # fmt: on
    ],
)
async def test_list_posts_validate_params(
    user_api_client: TestClient,
    uc: mock.Mock,
    query_params: dict[str, Any],
    error_detail: str,
) -> None:
    resp = user_api_client.get("/api/posts", params=query_params)

    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == error_detail


async def test_list_posts_empty(user_api_client: TestClient, uc: mock.Mock) -> None:
    uc.execute.return_value = ListFeedPostsOutput(posts=[])

    resp = user_api_client.get("/api/posts")
    assert resp.status_code == 200
    assert resp.json() == []

    uc.execute.assert_called_once_with(
        ListFeedPostsInput(
            followed_by=None,
            not_followed_by=None,
            read_by=None,
            not_read_by=None,
            feed_id=None,
            offset=0,
            limit=100,
        )
    )
