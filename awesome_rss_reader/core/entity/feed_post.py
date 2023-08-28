import uuid
from enum import Enum, auto

from pydantic import AwareDatetime, BaseModel, Field


class NewFeedPost(BaseModel):
    feed_id: int
    title: str
    summary: str | None
    url: str = Field(description="URL of the post that users can follow")
    guid: str = Field(description="Unique identifier of the post")
    published_at: AwareDatetime = Field(
        description="Publication date of the post as reported by the feed"
    )


class FeedPost(NewFeedPost):
    id: int  # noqa: A003
    created_at: AwareDatetime


class NewUserPost(BaseModel):
    user_uid: uuid.UUID
    post_id: int
    read_at: AwareDatetime


class UserPost(NewUserPost):
    id: int  # noqa: A003


class FeedPostFiltering(BaseModel):
    feed_id: int | None = None
    followed_by: uuid.UUID | None = None
    not_followed_by: uuid.UUID | None = None
    read_by: uuid.UUID | None = None
    not_read_by: uuid.UUID | None = None


class FeedPostOrdering(Enum):
    published_at_desc = auto()
