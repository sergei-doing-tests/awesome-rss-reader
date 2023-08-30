import asyncio
import uuid  # noqa: TCH003
from datetime import datetime
from io import BytesIO

import dateutil.parser
import feedparser
import httpx
import pydantic
import structlog

from awesome_rss_reader.core.entity.feed_content import (
    FeedContentBatchRequest,
    FeedContentBatchResponse,
    FeedContentRequest,
    FeedContentResult,
    FeedContentResultItem,
)
from awesome_rss_reader.core.repository.feed_content import (
    FeedContentFetchError,
    FeedContentParseError,
    FeedContentRepository,
)

logger = structlog.get_logger()


class _FeedPostParseError(Exception):
    """internal exception for handling badly formatted feed posts"""


class ExternalFeedContentRepository(FeedContentRepository):
    async def fetch_many(self, request: FeedContentBatchRequest) -> FeedContentBatchResponse:
        # fmt: off
        request_per_url: dict[str, FeedContentRequest] = {
            req.url: req for req in request.requests
        }
        # fmt: on
        feed_urls = list(request_per_url)
        fetch_responses = await self._fetch_feeds(
            urls=feed_urls,
            timeout=request.timeout_s,
            max_body_size=request.max_body_size_b,
        )

        errors: dict[uuid.UUID, Exception] = {}
        results: dict[uuid.UUID, FeedContentResult] = {}

        for resp_body_or_exc, url in zip(fetch_responses, feed_urls, strict=True):
            req = request_per_url[url]

            if isinstance(resp_body_or_exc, Exception):
                errors[req.request_id] = resp_body_or_exc
                continue

            try:
                feed_content = self._parse_feed_contents(
                    url=url,
                    content=resp_body_or_exc,
                    ignore_before=req.published_since,
                )
            except FeedContentParseError as exc:
                errors[req.request_id] = exc
                continue

            results[req.request_id] = feed_content

        return FeedContentBatchResponse(results=results, errors=errors)

    async def _fetch_feed_contents(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        max_body_size: int,
    ) -> BytesIO:
        try:
            return await self._fetch_feed_contents_chunked(client, url, max_body_size=max_body_size)
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            logger.warning("Failed to fetch feed", url=url, error=exc)
            raise FeedContentFetchError(f"failed to fetch {url=}") from exc

    async def _fetch_feed_contents_chunked(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        max_body_size: int,
    ) -> BytesIO:
        content = BytesIO()

        async with client.stream("GET", url) as resp:
            resp.raise_for_status()

            async for chunk in resp.aiter_bytes():
                content.write(chunk)
                # don't read more than max_body_size
                if content.tell() > max_body_size:
                    raise FeedContentFetchError(f"feed {url=} exceeds {max_body_size=} limit")

        content.seek(0)
        return content

    async def _fetch_feeds(
        self,
        *,
        urls: list[str],
        timeout: int,
        max_body_size: int,
    ) -> list[BytesIO | Exception]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [
                self._fetch_feed_contents(client, url, max_body_size=max_body_size) for url in urls
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

    def _parse_feed_contents(
        self,
        *,
        url: str,
        content: BytesIO,
        ignore_before: datetime | None = None,
    ) -> FeedContentResult:
        try:
            rss = feedparser.parse(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse feed", url=url, error=exc)
            raise FeedContentParseError(f"failed to parse contents of {url=}") from exc

        if parsed_exc := rss.get("bozo_exception"):
            logger.warning("Failed to parse feed contents", url=url, error=parsed_exc)
            raise FeedContentParseError(f"failed to parse contents of {url=}") from parsed_exc

        try:
            channel_title = rss["feed"]["title"]
        except KeyError:
            raise FeedContentParseError(f"feed {url=} has no channel info")

        if not (channel_title := channel_title.strip()):
            raise FeedContentParseError(f"feed {url=} has empty channel title")

        feed_items = self._parse_feed_posts(rss["entries"], ignore_before=ignore_before)

        return FeedContentResult(
            title=channel_title,
            published_at=feed_items[-1].published_at if feed_items else None,
            items=feed_items,
        )

    def _parse_feed_posts(
        self,
        rss_items: list[dict[str, str]],
        *,
        ignore_before: datetime | None = None,
    ) -> list[FeedContentResultItem]:
        feed_posts = []

        for rss_item in rss_items:
            try:
                feed_post = self._parse_feed_post(rss_item)
            except _FeedPostParseError as exc:
                logger.warning("Failed to parse feed post", guid=rss_item.get("guid"), error=exc)
                continue
            # ignore posts that are older than the last update,
            # because it's highly likely that we already have them
            if ignore_before and feed_post.published_at < ignore_before:
                logger.debug(
                    "Ignoring outdated feed post",
                    guid=feed_post.guid,
                    published_at=feed_post.published_at,
                    ignore_before=ignore_before,
                )
                continue

            feed_posts.append(feed_post)

        # sort the items by published_at, so the latest item is the last one
        feed_posts.sort(key=lambda it: it.published_at)

        return feed_posts

    def _parse_feed_post(self, rss_item: dict[str, str]) -> FeedContentResultItem:
        maybe_guid = rss_item.get("guid")

        try:
            published_at = dateutil.parser.parse(rss_item["published"])
        except (KeyError, dateutil.parser.ParserError) as exc:
            logger.debug("Failed to parse feed post publication date", guid=maybe_guid, error=exc)
            raise _FeedPostParseError("failed to parse post publication date") from exc

        try:
            title = rss_item["title"]
            guid = maybe_guid or rss_item["link"]
            url = rss_item["link"]
            summary = rss_item.get("summary")
        except KeyError as exc:
            logger.debug("Required post fields are missing", guid=maybe_guid, error=exc)
            raise _FeedPostParseError("required post fields are missing") from exc

        try:
            return FeedContentResultItem(
                title=title,
                summary=summary,
                url=url,  # type: ignore[arg-type]
                guid=guid,
                published_at=published_at,
            )
        except pydantic.ValidationError as exc:
            logger.debug("Failed to validate feed post fields", error=exc)
            raise _FeedPostParseError("failed to validate feed post fields") from exc
