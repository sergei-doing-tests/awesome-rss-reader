import uuid
from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed


class UserFeedRepositoryError(Exception):
    ...


class UserFeedNotFoundError(UserFeedRepositoryError):
    ...


class UserFeedAlreadyExistsError(UserFeedRepositoryError):
    ...


class UserFeedNoFeedError(UserFeedRepositoryError):
    ...


class UserFeedRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_feed_id: int) -> UserFeed:
        ...

    @abstractmethod
    async def get_for_user_and_feed(self, *, user_uid: uuid.UUID, feed_id: int) -> UserFeed:
        ...

    @abstractmethod
    async def get_or_create(self, new_user_feed: NewUserFeed) -> UserFeed:
        ...

    @abstractmethod
    async def delete(self, user_feed_id: int) -> None:
        ...
