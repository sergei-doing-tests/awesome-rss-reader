from abc import ABC, abstractmethod

from awesome_rss_reader.core.entity.feed_content import (
    FeedContentBatchRequest,
    FeedContentBatchResult,
)


class FeedContentRepositoryError(Exception):
    ...


class FeedContentFetchError(FeedContentRepositoryError):
    ...


class FeedContentParseError(FeedContentRepositoryError):
    ...


class FeedContentRepository(ABC):
    @abstractmethod
    async def fetch_many(self, request: FeedContentBatchRequest) -> FeedContentBatchResult:
        ...
