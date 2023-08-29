import uuid
from enum import Enum, auto

from pydantic import AwareDatetime, BaseModel, Field


class NewFeed(BaseModel):
    url: str = Field(description="Public URL of the feed")
    title: str | None = None
    published_at: AwareDatetime | None = None


class Feed(NewFeed):
    id: int  # noqa: A003
    created_at: AwareDatetime | None


class FeedUpdates(BaseModel):
    title: str | None = None
    published_at: AwareDatetime | None = None


class FeedFiltering(BaseModel):
    ids: list[int] | None = None
    followed_by: uuid.UUID | None = None


class FeedOrdering(Enum):
    id_asc = auto()
    published_at_desc = auto()
