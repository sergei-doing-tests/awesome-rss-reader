from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self) -> User:
        ...
