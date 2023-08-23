from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed


class UserFeedRepository(ABC):
    @abstractmethod
    async def get_or_create(self, new_user_feed: NewUserFeed) -> UserFeed:
        ...
