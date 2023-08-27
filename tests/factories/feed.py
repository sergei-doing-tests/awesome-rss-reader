from faker import Faker
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
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
