from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.unread_post import (
    PostNotFoundError,
    UnreadPostInput,
    UnreadPostUseCase,
)


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=UnreadPostUseCase)

    with container.use_cases.unread_post.override(uc):
        yield uc


async def test_unread_post_happy_path(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.return_value = None

    resp = user_api_client.delete("/api/posts/1/unread")
    assert resp.status_code == 204

    uc.execute.assert_called_once_with(UnreadPostInput(user_uid=user.uid, post_id=1))


async def test_unread_post_does_not_exist(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.side_effect = PostNotFoundError

    resp = user_api_client.delete("/api/posts/1/unread")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Post not found"}

    uc.execute.assert_called_once_with(UnreadPostInput(user_uid=user.uid, post_id=1))
