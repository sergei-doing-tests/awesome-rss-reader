from enum import Enum, auto

from pydantic import AwareDatetime, BaseModel, Field


class NewFeed(BaseModel):
    url: str = Field(description="Public URL of the feed")
    title: str | None = None
    refreshed_at: AwareDatetime | None = Field(
        description="Date of last refresh of the feed",
        default=None,
    )


class Feed(NewFeed):
    id: int  # noqa: A003
    created_at: AwareDatetime = Field(description="Date of feed creation in the service")


class FeedOrdering(Enum):
    refreshed_at = auto()
