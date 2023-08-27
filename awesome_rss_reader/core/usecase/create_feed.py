import uuid
from dataclasses import dataclass
from uuid import UUID

import structlog

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJobState, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed
from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.core.repository.feed import FeedRepository
from awesome_rss_reader.core.repository.feed_refresh_job import (
    FeedRefreshJobRepository,
    RefreshJobStateTransitionError,
)
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
            feed = await self._create_feed(data.url)
            await self._create_feed_refresh_job(feed)
            await self._subscribe_user_to_feed(feed, data.user_uid)
        return CreateFeedOutput(feed=feed)

    async def _create_feed(self, url: str) -> Feed:
        new_feed = NewFeed(url=url)
        feed = await self.feed_repository.get_or_create(new_feed)
        logger.debug("Obtained a feed", feed_id=feed.id, feed_url=feed.url)
        return feed

    async def _create_feed_refresh_job(self, feed: Feed) -> None:
        new_refresh_job = NewFeedRefreshJob(feed_id=feed.id)
        refresh_job = await self.job_repository.get_or_create(new_refresh_job)

        logger.debug(
            "Obtained a refresh job for feed",
            feed_id=feed.id,
            job_id=refresh_job.id,
            job_state=refresh_job.state,
        )

        # Don't trigger a job refresh if it's already in progress
        if refresh_job.state in {FeedRefreshJobState.pending, FeedRefreshJobState.in_progress}:
            return

        try:
            await self.job_repository.transit_state(
                job_id=refresh_job.id,
                old_state=refresh_job.state,
                new_state=FeedRefreshJobState.pending,
            )
        # Wow, this is a race. Someone else has already started the job. Well this is fine
        # Because that's what we wanted ourselves, we don't care about this race condition
        except RefreshJobStateTransitionError:
            logger.info(
                "Feed refresh job is already in progress",
                feed_id=feed.id,
                job_id=refresh_job.id,
                job_state=refresh_job.state,
            )

    async def _subscribe_user_to_feed(self, feed: Feed, user_uid: uuid.UUID) -> UserFeed:
        new_user_feed = NewUserFeed(user_uid=user_uid, feed_id=feed.id)
        user_feed = await self.user_feed_repository.get_or_create(new_user_feed)

        # fmt: off
        logger.info(
            "Subscribed user to feed",
            user_uid=user_uid, feed_id=feed.id, feed_url=feed.url, user_feed_id=user_feed.id,
        )
        # fmt: on

        return user_feed
