from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ApiCreateFeedBody(BaseModel):
    url: HttpUrl = Field(..., description="Public URL of the rss feed")


class ApiFeed(BaseModel):
    id: int  # noqa: A003
    url: str
    title: str | None = None
    refreshed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
