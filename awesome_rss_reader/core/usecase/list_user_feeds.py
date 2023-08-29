import uuid
from dataclasses import dataclass

from awesome_rss_reader.core.entity.feed import Feed, FeedFiltering, FeedOrdering
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase


@dataclass
class ListUserFeedsInput:
    user_uid: uuid.UUID
    offset: int
    limit: int


@dataclass
class ListUserFeedsOutput:
    feeds: list[Feed]


@dataclass
class ListUserFollowedFeedsUseCase(BaseUseCase):
    feed_repository: FeedRepository

    async def execute(self, data: ListUserFeedsInput) -> ListUserFeedsOutput:
        feeds = await self.feed_repository.get_list(
            filter_by=FeedFiltering(
                followed_by=data.user_uid,
            ),
            order_by=FeedOrdering.published_at_desc,
            offset=data.offset,
            limit=data.limit,
        )
        return ListUserFeedsOutput(feeds=feeds)
