from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ApiCreateFeedBody(BaseModel):
    url: HttpUrl = Field(..., description="Public URL of the rss feed")


class ApiFeed(BaseModel):
    id: int  # noqa: A003
    url: str
    title: str | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiPostReadStatus(str, Enum):
    read = "read"
    unread = "unread"


class ApiPostFollowStatus(str, Enum):
    following = "following"
    not_following = "not_following"


class ApiFeedPost(BaseModel):
    id: int  # noqa: A003
    feed_id: int
    title: str
    summary: str | None
    url: str
    created_at: datetime
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)
