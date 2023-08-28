import uuid
from dataclasses import dataclass

from pydantic import BaseModel, model_validator

from awesome_rss_reader.core.entity.feed_post import FeedPost, FeedPostFiltering, FeedPostOrdering
from awesome_rss_reader.core.repository.feed_post import FeedPostRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase


class ListFeedPostsInput(BaseModel):
    followed_by: uuid.UUID | None = None
    not_followed_by: uuid.UUID | None = None
    read_by: uuid.UUID | None = None
    not_read_by: uuid.UUID | None = None
    feed_id: int | None = None
    offset: int
    limit: int

    @model_validator(mode="after")
    def check_mutually_exclusive_fields(self) -> "ListFeedPostsInput":
        if self.followed_by and self.not_followed_by:
            raise ValueError('Only one of "followed_by" or "not_followed_by" can be specified')

        if self.read_by and self.not_read_by:
            raise ValueError('Only one of "read_by" or "not_read_by" can be specified')

        return self


@dataclass
class ListFeedPostsOutput:
    posts: list[FeedPost]


@dataclass
class ListFeedPostsUseCase(BaseUseCase):
    post_repository: FeedPostRepository

    async def execute(self, data: ListFeedPostsInput) -> ListFeedPostsOutput:
        filtering = FeedPostFiltering(
            feed_id=data.feed_id,
            followed_by=data.followed_by,
            not_followed_by=data.not_followed_by,
            read_by=data.read_by,
        )
        posts = await self.post_repository.get_list(
            order_by=FeedPostOrdering.published_at_desc,
            filter_by=filtering,
            limit=data.limit,
            offset=data.offset,
        )
        return ListFeedPostsOutput(posts=posts)
