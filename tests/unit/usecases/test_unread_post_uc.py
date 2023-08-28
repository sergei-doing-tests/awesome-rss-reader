import uuid
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository import feed_post as post_repo
from awesome_rss_reader.core.repository import user_post as user_post_repo
from awesome_rss_reader.core.usecase.unread_post import (
    PostNotFoundError,
    UnreadPostInput,
    UnreadPostUseCase,
)
from tests.factories import FeedPostFactory, UserPostFactory


@pytest.fixture()
def uc(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
) -> UnreadPostUseCase:
    return container.use_cases.unread_post()


async def test_happy_path(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: UnreadPostUseCase,
) -> None:
    user_uid = uuid.uuid4()
    post = FeedPostFactory.build()
    user_post = UserPostFactory.build(user_uid=user_uid, post_id=post.id)

    post_repository.get_by_id.return_value = post
    user_post_repository.get_for_user_and_post.return_value = user_post
    user_post_repository.delete.return_value = None

    uc_input = UnreadPostInput(user_uid=user_uid, post_id=post.id)
    await uc.execute(uc_input)

    post_repository.get_by_id.assert_called_once_with(post.id)
    user_post_repository.get_for_user_and_post.assert_called_once_with(
        user_uid=user_uid, post_id=post.id
    )
    user_post_repository.delete.assert_called_once_with(user_post.id)


async def test_post_not_found(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: UnreadPostUseCase,
) -> None:
    post_repository.get_by_id.side_effect = post_repo.PostNotFoundError

    uc_input = UnreadPostInput(user_uid=uuid.uuid4(), post_id=1)
    with pytest.raises(PostNotFoundError):
        await uc.execute(uc_input)

    post_repository.get_by_id.assert_called_once_with(1)
    user_post_repository.get_for_user_and_post.assert_not_called()
    user_post_repository.delete.assert_not_called()


async def test_user_post_not_found(
    container: Container,
    post_repository: mock.Mock,
    user_post_repository: mock.Mock,
    uc: UnreadPostUseCase,
) -> None:
    user_uid = uuid.uuid4()
    post = FeedPostFactory.build()

    post_repository.get_by_id.return_value = post
    user_post_repository.get_for_user_and_post.side_effect = user_post_repo.UserPostNotFoundError

    uc_input = UnreadPostInput(user_uid=user_uid, post_id=post.id)
    await uc.execute(uc_input)

    post_repository.get_by_id.assert_called_once_with(post.id)
    user_post_repository.get_for_user_and_post.assert_called_once_with(
        user_uid=user_uid, post_id=uc_input.post_id
    )
    user_post_repository.delete.assert_not_called()
