from unittest import mock

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.read_post import (
    PostNotFoundError,
    ReadPostInput,
    ReadPostOutput,
    ReadPostUseCase,
)
from tests.factories import UserPostFactory


@pytest.fixture()
def uc(container: Container) -> mock.Mock:
    uc = mock.Mock(spec=ReadPostUseCase)

    with container.use_cases.read_post.override(uc):
        yield uc


async def test_read_post_happy_path(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    user_post = UserPostFactory.build(
        user_uid=user.uid,
        post_id=1,
    )
    uc.execute.return_value = ReadPostOutput(user_post=user_post)

    resp = user_api_client.put("/api/posts/1/read")
    assert resp.status_code == 204

    uc.execute.assert_called_once_with(ReadPostInput(user_uid=user.uid, post_id=1))


async def test_read_post_post_not_found(
    user: User,
    user_api_client: TestClient,
    uc: mock.Mock,
) -> None:
    uc.execute.side_effect = PostNotFoundError

    resp = user_api_client.put("/api/posts/1/read")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Post not found"}

    uc.execute.assert_called_once_with(ReadPostInput(user_uid=user.uid, post_id=1))
