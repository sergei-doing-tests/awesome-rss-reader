import uuid

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.repository.user import UserRepository


class NoopUserRepository(UserRepository):
    """
    A noop user repository that generates a random user entity without persisting it.
    """

    async def create(self) -> User:
        return User(uid=uuid.uuid4())
