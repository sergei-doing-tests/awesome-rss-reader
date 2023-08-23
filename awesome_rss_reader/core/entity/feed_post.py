from enum import Enum, auto

from pydantic import AwareDatetime, BaseModel, Field


class FeedPost(BaseModel):
    id: int  # noqa: A003
    feed_id: int
    title: str
    summary: str | None
    url: str = Field(description="URL of the post that users can follow")
    guid: str = Field(description="Unique identifier of the post")
    created_at = AwareDatetime
    published_at: AwareDatetime | None = Field(
        description="Date of publication of the post as reported by the feed"
    )


class UserFeedPostReadState(Enum):
    read = auto()
    unread = auto()


class FeedPostOrdering(Enum):
    published_at = auto()
