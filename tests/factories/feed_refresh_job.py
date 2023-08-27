from faker import Faker
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    NewFeedRefreshJob,
)
from awesome_rss_reader.utils import dtime

faker = Faker()


class NewFeedRefreshJobFactory(ModelFactory[NewFeedRefreshJob]):
    __model__ = NewFeedRefreshJob

    feed_id = faker.pyint()
    state = FeedRefreshJobState.pending
    execute_after = Use(dtime.now_aware)
    retries = 0


class FeedRefreshJobFactory(ModelFactory[FeedRefreshJob]):
    __model__ = FeedRefreshJob

    id = faker.pyint()  # noqa: A003
    feed_id = faker.pyint()
    state = FeedRefreshJobState.pending
    execute_after = Use(dtime.now_aware)
    retries = 0
    created_at = Use(dtime.now_aware)
    updated_at = Use(dtime.now_aware)
