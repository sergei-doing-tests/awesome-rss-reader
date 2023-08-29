import asyncio
from datetime import datetime
from io import BytesIO

import dateutil.parser
import feedparser
import httpx
import pydantic
import structlog

from awesome_rss_reader.core.entity.feed_content import (
    FeedContentBatchRequest,
    FeedContentBatchResult,
    FeedContentResult,
    FeedContentResultItem,
)
from awesome_rss_reader.core.repository.feed_content import (
    FeedContentFetchError,
    FeedContentParseError,
    FeedContentRepository,
)

logger = structlog.get_logger()


class ExternalFeedContentRepository(FeedContentRepository):
    async def fetch_many(self, request: FeedContentBatchRequest) -> FeedContentBatchResult:
        request_id_per_url = {
            request.url: request_id for request_id, request in request.requests.items()
        }
        published_since_per_url = {
            request.url: request.published_since for request in request.requests.values()
        }
        feed_urls = list(request_id_per_url)
        fetch_responses = await self._fetch_feeds(urls=feed_urls, timeout=request.timeout)

        errors = {}
        results = {}

        for resp_or_ex, url in zip(fetch_responses, feed_urls, strict=True):
            request_id = request_id_per_url[url]
            published_since = published_since_per_url[url]

            if isinstance(resp_or_ex, Exception):
                errors[request_id] = resp_or_ex
                continue

            try:
                feed_content = self._parse_rss_feed(resp_or_ex, ignore_before=published_since)
            except FeedContentParseError as exc:
                errors[request_id] = exc
                continue

            results[request_id] = feed_content

        return FeedContentBatchResult(
            results=results,
            errors=errors,
        )

    async def _fetch_feed_by_url(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            logger.warning("Failed to fetch feed", url=url, error=exc)
            raise FeedContentFetchError(f"failed to fetch {url=}") from exc
        return resp

    async def _fetch_feeds(
        self,
        *,
        urls: list[str],
        timeout: int,
    ) -> list[httpx.Response | Exception]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            coros = [self._fetch_feed_by_url(client, url) for url in urls]
            return await asyncio.gather(*coros, return_exceptions=True)

    def _parse_rss_feed(
        self,
        response: httpx.Response,
        *,
        ignore_before: datetime | None = None,
    ) -> FeedContentResult:
        try:
            rss = feedparser.parse(BytesIO(response.content))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse feed", url=response.url, error=exc)
            raise FeedContentParseError(f"failed to parse contents of {response.url=}") from exc

        if parsed_exc := rss.get("bozo_exception"):
            err_msg = f"failed to parse contents of {response.url=}"
            raise FeedContentParseError(err_msg) from parsed_exc

        try:
            channel_title = rss["feed"]["title"]
        except KeyError:
            err_msg = f"{response.url=} feed has no channel info"
            raise FeedContentParseError(err_msg)

        feed_items = self._parse_rss_feed_items(rss["entries"], ignore_before=ignore_before)

        return FeedContentResult(
            title=channel_title,
            published_at=feed_items[-1].published_at if feed_items else None,
            items=feed_items,
        )

    def _parse_rss_feed_items(
        self,
        raw_items: list[dict[str, str]],
        *,
        ignore_before: datetime | None = None,
    ) -> list[FeedContentResultItem]:
        items = []

        for raw_item in raw_items:
            title = raw_item.get("title")
            guid = raw_item.get("id") or raw_item.get("guid")
            url = raw_item.get("link")
            summary = raw_item.get("summary")

            try:
                published_at = dateutil.parser.parse(raw_item["published"])
            except (KeyError, dateutil.parser.ParserError) as exc:
                logger.warning("Failed to parse feed item publication date", url=url, error=exc)
                continue

            if ignore_before and published_at < ignore_before:
                # fmt: off
                logger.debug(
                    "Ignoring outdated feed item",
                    url=url, ignore_before=ignore_before, published_at=published_at
                )
                # fmt: on
                continue

            try:
                item = FeedContentResultItem(
                    title=title,  # type: ignore[arg-type]
                    summary=summary,
                    url=url,  # type: ignore[arg-type]
                    guid=guid,  # type: ignore[arg-type]
                    published_at=published_at,
                )
            except pydantic.ValidationError as exc:
                logger.warning("Failed to parse feed item", error=exc)
                continue

            items.append(item)

        # sort the items by published_at, so the latest item is the last one
        items.sort(key=lambda it: it.published_at)

        return items
