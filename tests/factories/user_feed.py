from faker import Faker
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.utils import dtime

faker = Faker()


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
