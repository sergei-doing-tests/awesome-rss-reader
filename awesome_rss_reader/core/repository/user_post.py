import uuid
from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.user_post import NewUserPost, UserPost


class UserPostNotFoundError(Exception):
    ...


class UserPostNoPostError(Exception):
    ...


class UserPostRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_post_id: int) -> UserPost:
        ...

    @abstractmethod
    async def get_for_user_and_post(self, *, user_uid: uuid.UUID, post_id: int) -> UserPost:
        ...

    @abstractmethod
    async def get_or_create(self, new_user_post: NewUserPost) -> UserPost:
        ...

    @abstractmethod
    async def delete(self, user_post_id: int) -> None:
        ...
