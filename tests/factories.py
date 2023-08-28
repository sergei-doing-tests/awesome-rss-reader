from uuid import uuid4

from faker import Faker
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_post import FeedPost, NewFeedPost, NewUserPost
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.utils import dtime

faker = Faker()


class NewFeedFactory(ModelFactory[NewFeed]):
    __model__ = NewFeed

    title = faker.text(max_nb_chars=64)
    refreshed_at = Use(dtime.now_aware)


class FeedFactory(ModelFactory[Feed]):
    __model__ = Feed

    id = faker.pyint()  # noqa: A003
    url = faker.url()
    title = faker.text(max_nb_chars=64)
    refreshed_at = Use(dtime.now_aware)
    created_at = Use(dtime.now_aware)


class NewUserFeedFactory(ModelFactory[NewUserFeed]):
    __model__ = NewUserFeed

    user_uid = faker.uuid4()
    feed_id = faker.pyint()


class UserFeedFactory(ModelFactory[UserFeed]):
    __model__ = UserFeed

    id = faker.pyint()  # noqa: A003
    user_uid = faker.uuid4()
    feed_id = faker.pyint()
    created_at = Use(dtime.now_aware)


class NewFeedPostFactory(ModelFactory[NewFeedPost]):
    __model__ = NewFeedPost

    feed_id = faker.pyint()
    title = faker.text(max_nb_chars=64)
    summary = faker.paragraph(nb_sentences=4)
    url = faker.url()
    guid = faker.url()
    published_at = Use(dtime.now_aware)


class FeedPostFactory(ModelFactory[FeedPost]):
    __model__ = FeedPost

    id = faker.pyint()  # noqa: A003
    title = faker.text(max_nb_chars=64)
    summary = faker.paragraph(nb_sentences=4)
    url = faker.url()
    feed_id = faker.pyint()
    guid = faker.url()
    created_at = Use(dtime.now_aware)
    published_at = Use(dtime.now_aware)


class NewUserPostFactory(ModelFactory[NewUserPost]):
    __model__ = NewUserPost

    user_uid = faker.uuid4()
    post_id = faker.pyint()
    read_at = Use(dtime.now_aware)


class UserPostFactory(ModelFactory[NewUserPost]):
    __model__ = NewUserPost

    id = faker.pyint()  # noqa: A003
    user_uid = faker.uuid4()
    post_id = faker.pyint()
    read_at = Use(dtime.now_aware)


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


class UserFactory(ModelFactory[User]):
    __model__ = User

    uid = Use(uuid4)
