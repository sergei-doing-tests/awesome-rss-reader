import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict


class FeedContentRequest(BaseModel):
    url: str
    published_since: AwareDatetime | None


class FeedContentResultItem(BaseModel):
    title: str
    summary: str | None
    url: str
    guid: str
    published_at: AwareDatetime


class FeedContentResult(BaseModel):
    title: str
    published_at: AwareDatetime | None
    items: list[FeedContentResultItem]


class FeedContentBatchRequest(BaseModel):
    timeout: int
    requests: dict[uuid.UUID, FeedContentRequest]


class FeedContentBatchResult(BaseModel):
    results: dict[uuid.UUID, FeedContentResult]
    errors: dict[uuid.UUID, Exception]

    model_config = ConfigDict(arbitrary_types_allowed=True)
