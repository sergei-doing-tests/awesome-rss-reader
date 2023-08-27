from uuid import uuid4

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from awesome_rss_reader.core.entity.user import User


class UserFactory(ModelFactory[User]):
    __model__ = User

    uid = Use(uuid4)
