import uuid
from datetime import UTC, datetime
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository import feed_post as post_repo
from awesome_rss_reader.core.repository import user_post as user_post_repo
from awesome_rss_reader.core.usecase.read_post import (
    PostNotFoundError,
    ReadPostInput,
    ReadPostOutput,
    ReadPostUseCase,
)
from tests.factories import FeedPostFactory, UserPostFactory


@pytest.fixture()
def uc(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
) -> ReadPostUseCase:
    return container.use_cases.read_post()


@mock.patch(
    "awesome_rss_reader.core.usecase.read_post.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_happy_path(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: ReadPostUseCase,
) -> None:
    user_uid = uuid.uuid4()

    post = FeedPostFactory.build()
    user_post = UserPostFactory.build(user_uid=user_uid, post_id=post.id)

    post_repository.get_by_id.return_value = post
    user_post_repository.get_or_create.return_value = user_post

    uc_input = ReadPostInput(user_uid=user_uid, post_id=post.id)
    uc_result = await uc.execute(uc_input)
    assert uc_result == ReadPostOutput(user_post=user_post)

    post_repository.get_by_id.assert_called_once_with(post.id)
    user_post_repository.get_or_create.assert_called_once_with(
        user_post_repo.NewUserPost(
            post_id=post.id,
            user_uid=user_uid,
            read_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        )
    )


async def test_post_not_found(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: ReadPostUseCase,
) -> None:
    post_repository.get_by_id.side_effect = post_repo.PostNotFoundError

    uc_input = ReadPostInput(user_uid=uuid.uuid4(), post_id=1)
    with pytest.raises(PostNotFoundError):
        await uc.execute(uc_input)

    post_repository.get_by_id.assert_called_once_with(uc_input.post_id)
    user_post_repository.get_or_create.assert_not_called()


@mock.patch(
    "awesome_rss_reader.core.usecase.read_post.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
async def test_post_not_found_on_get_or_create(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: ReadPostUseCase,
) -> None:
    post = FeedPostFactory.build()

    post_repository.get_by_id.return_value = post
    user_post_repository.get_or_create.side_effect = user_post_repo.UserPostNoPostError

    uc_input = ReadPostInput(user_uid=uuid.uuid4(), post_id=post.id)
    with pytest.raises(PostNotFoundError):
        await uc.execute(uc_input)

    post_repository.get_by_id.assert_called_once_with(post.id)
    user_post_repository.get_or_create.assert_called_once_with(
        user_post_repo.NewUserPost(
            post_id=post.id,
            user_uid=uc_input.user_uid,
            read_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        )
    )
