from dataclasses import dataclass
from uuid import UUID

import structlog

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_refresh_job import NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed
from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.core.repository.feed_refresh_job import FeedRefreshJobRepository
from awesome_rss_reader.core.repository.user_feed import UserFeedRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase

logger = structlog.get_logger()


@dataclass
class CreateFeedInput:
    url: str
    user_uid: UUID


@dataclass
class CreateFeedOutput:
    feed: Feed


@dataclass
class CreateFeedUseCase(BaseUseCase):
    feed_repository: FeedRepository
    user_feed_repository: UserFeedRepository
    job_repository: FeedRefreshJobRepository
    atomic: AtomicProvider

    async def execute(self, data: CreateFeedInput) -> CreateFeedOutput:
        async with self.atomic.transaction():
            feed = await self._create_feed_for_user(data.url, data.user_uid)
        return CreateFeedOutput(feed=feed)

    async def _create_feed_for_user(self, url: str, user_uid: UUID) -> Feed:
        new_feed = NewFeed(url=url)
        feed = await self.feed_repository.get_or_create(new_feed)
        # fmt: off
        logger.debug(
            "Obtained a feed on request of user",
            feed_id=feed.id, feed_url=feed.url, user_uid=user_uid,
        )
        # fmt: on

        new_refresh_job = NewFeedRefreshJob(feed_id=feed.id)
        refresh_job = await self.job_repository.get_or_create(new_refresh_job)
        # fmt: off
        logger.debug(
            "Obtained a refresh job for feed",
            feed_id=feed.id, job_id=refresh_job.id, job_state=refresh_job.state,
        )
        # fmt: on

        new_user_feed = NewUserFeed(user_uid=user_uid, feed_id=feed.id)
        user_feed = await self.user_feed_repository.get_or_create(new_user_feed)

        # fmt: off
        logger.info(
            "Subscribed user to feed",
            user_uid=user_uid, feed_id=feed.id, feed_url=feed.url, user_feed_id=user_feed.id,
        )
        # fmt: on

        return feed
