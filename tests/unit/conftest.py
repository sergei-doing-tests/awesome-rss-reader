from collections.abc import Iterator
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.core.repository.feed_post import FeedPostRepository
from awesome_rss_reader.core.repository.feed_refresh_job import FeedRefreshJobRepository
from awesome_rss_reader.core.repository.user_feed import UserFeedRepository
from awesome_rss_reader.core.repository.user_post import UserPostRepository


@pytest.fixture(autouse=True)
def atomic(container: Container) -> Iterator[mock.Mock]:
    atomic_mock = mock.AsyncMock(spec=AtomicProvider)

    with container.repositories.atomic.override(atomic_mock):
        yield atomic_mock


@pytest.fixture()
def feed_repository(container: Container) -> Iterator[mock.Mock]:
    repo_mock = mock.Mock(spec=FeedRepository)

    with container.repositories.feeds.override(repo_mock):
        yield repo_mock


@pytest.fixture()
def user_feed_repository(container: Container) -> Iterator[mock.Mock]:
    repo_mock = mock.Mock(spec=UserFeedRepository)

    with container.repositories.user_feeds.override(repo_mock):
        yield repo_mock


@pytest.fixture()
def post_repository(container: Container) -> Iterator[mock.Mock]:
    repo_mock = mock.Mock(spec=FeedPostRepository)

    with container.repositories.feed_posts.override(repo_mock):
        yield repo_mock


@pytest.fixture()
def user_post_repository(container: Container) -> Iterator[mock.Mock]:
    repo_mock = mock.Mock(spec=UserPostRepository)

    with container.repositories.user_posts.override(repo_mock):
        yield repo_mock


@pytest.fixture()
def job_repository(container: Container) -> Iterator[mock.Mock]:
    repo_mock = mock.Mock(spec=FeedRefreshJobRepository)

    with container.repositories.feed_refresh_jobs.override(repo_mock):
        yield repo_mock
