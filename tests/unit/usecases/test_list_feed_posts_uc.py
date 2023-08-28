import uuid
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed_post import FeedPostFiltering, FeedPostOrdering
from awesome_rss_reader.core.usecase.list_feed_posts import (
    ListFeedPostsInput,
    ListFeedPostsOutput,
    ListFeedPostsUseCase,
)
from tests.factories import FeedPostFactory


@pytest.fixture()
def uc(container: Container, post_repository: mock.Mock) -> ListFeedPostsUseCase:
    return container.use_cases.list_feed_posts()


"""
    followed_by: uuid.UUID | None = None
    not_followed_by: uuid.UUID | None = None
    read_by: uuid.UUID | None = None
    not_read_by: uuid.UUID | None = None
    feed_id: int | None = None
    offset: int
    limit: int
"""


@pytest.mark.parametrize(
    "uc_input, get_list_call",
    [
        (
            ListFeedPostsInput(offset=0, limit=100),
            mock.call(
                order_by=FeedPostOrdering.published_at_desc,
                filter_by=FeedPostFiltering(
                    feed_id=None,
                    followed_by=None,
                    not_followed_by=None,
                    read_by=None,
                    not_read_by=None,
                ),
                offset=0,
                limit=100,
            ),
        ),
        (
            ListFeedPostsInput(
                followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                read_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                feed_id=10,
                offset=0,
                limit=20,
            ),
            mock.call(
                order_by=FeedPostOrdering.published_at_desc,
                filter_by=FeedPostFiltering(
                    feed_id=10,
                    followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                    not_followed_by=None,
                    read_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                    not_read_by=None,
                ),
                offset=0,
                limit=20,
            ),
        ),
        (
            ListFeedPostsInput(
                not_followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                not_read_by=None,
                feed_id=10,
                offset=0,
                limit=20,
            ),
            mock.call(
                order_by=FeedPostOrdering.published_at_desc,
                filter_by=FeedPostFiltering(
                    feed_id=10,
                    followed_by=None,
                    not_followed_by=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                    read_by=None,
                    not_read_by=None,
                ),
                offset=0,
                limit=20,
            ),
        ),
    ],
)
async def test_happy_path(
    container: Container,
    post_repository: mock.Mock,
    uc: ListFeedPostsUseCase,
    uc_input: ListFeedPostsInput,
    get_list_call: tuple,
) -> None:
    posts = [
        FeedPostFactory.build(
            title="The Best High DPI Gaming Mice",
            url="https://example.com/1",
            feed_id=1,
        ),
        FeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            url="https://example.com/2",
            feed_id=2,
        ),
    ]
    post_repository.get_list.return_value = posts

    uc_result = await uc.execute(uc_input)
    assert uc_result == ListFeedPostsOutput(posts=posts)

    assert post_repository.get_list.call_args_list == [get_list_call]


async def test_empty_list(
    container: Container,
    post_repository: mock.Mock,
    uc: ListFeedPostsUseCase,
) -> None:
    post_repository.get_list.return_value = []

    uc_input = ListFeedPostsInput(offset=0, limit=100)
    uc_result = await uc.execute(uc_input)

    assert uc_result == ListFeedPostsOutput(posts=[])

    post_repository.get_list.assert_called_once_with(
        order_by=FeedPostOrdering.published_at_desc,
        filter_by=FeedPostFiltering(
            feed_id=None,
            followed_by=None,
            not_followed_by=None,
            read_by=None,
            not_read_by=None,
        ),
        offset=0,
        limit=100,
    )
