import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl


class FeedContentRequest(BaseModel):
    request_id: uuid.UUID
    url: str
    published_since: AwareDatetime | None


class FeedContentResultItem(BaseModel):
    title: str = Field(..., min_length=1)
    summary: str | None
    url: HttpUrl
    guid: str
    published_at: AwareDatetime


class FeedContentResult(BaseModel):
    title: str = Field(..., min_length=1)
    published_at: AwareDatetime | None
    items: list[FeedContentResultItem]


class FeedContentBatchRequest(BaseModel):
    timeout_s: int
    max_body_size_b: int
    requests: list[FeedContentRequest]


class FeedContentBatchResponse(BaseModel):
    results: dict[uuid.UUID, FeedContentResult]
    errors: dict[uuid.UUID, Exception]

    model_config = ConfigDict(arbitrary_types_allowed=True)
