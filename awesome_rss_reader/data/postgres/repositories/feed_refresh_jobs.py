from typing import Any

import sqlalchemy as sa
import structlog
from asyncpg import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy.exc import IntegrityError

from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJob,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
    NewFeedRefreshJob,
)
from awesome_rss_reader.core.repository.feed_refresh_job import (
    FeedRefreshJobRepository,
    RefreshJobNoFeedError,
    RefreshJobNotFoundError,
    RefreshJobStateTransitionError,
)
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository

logger = structlog.get_logger()


class _RefreshJobAlreadyExistsError(Exception):
    """Internal exception to handle unique constraint conflicts."""

    ...


class PostgresFeedRefreshJobRepository(BasePostgresRepository, FeedRefreshJobRepository):
    async def get_by_id(self, job_id: int) -> FeedRefreshJob:
        return await self._get_by_field(field="id", value=job_id)

    async def get_by_feed_id(self, feed_id: int) -> FeedRefreshJob:
        return await self._get_by_field(field="feed_id", value=feed_id)

    async def _get_by_field(self, *, field: str, value: Any) -> FeedRefreshJob:
        query = sa.select(mdl.FeedRefreshJob).where(sa.column(field) == value)

        async with self.db.connect() as conn:
            result = await conn.execute(query)

            if row := result.mappings().fetchone():
                return FeedRefreshJob.model_validate(dict(row))

        raise RefreshJobNotFoundError(f"Refresh job with {field} {value} not found")

    async def get_or_create(self, new_job: NewFeedRefreshJob) -> FeedRefreshJob:
        try:
            return await self.get_by_feed_id(new_job.feed_id)
        except RefreshJobNotFoundError:
            logger.info("Job for feed does not exist. Creating a new one", feed_id=new_job.feed_id)

        try:
            return await self._maybe_create(new_job)
        except _RefreshJobAlreadyExistsError:
            return await self.get_by_feed_id(feed_id=new_job.feed_id)

    async def _maybe_create(self, new_job: NewFeedRefreshJob) -> FeedRefreshJob:
        # fmt: off
        query = (
            sa.insert(mdl.FeedRefreshJob)
            .values(new_job.model_dump())
            .returning(mdl.FeedRefreshJob)
        )
        # fmt: on

        async with self.db.begin() as conn:
            try:
                async with conn.begin_nested():
                    result = await conn.execute(query)
            except IntegrityError as ie:
                logger.warning("Failed to insert refresh job", feed_id=new_job.feed_id, error=ie)
                self._handle_integrity_error_on_create(ie)

            row = result.mappings().one()
            return FeedRefreshJob.model_validate(dict(row))

    def _handle_integrity_error_on_create(self, ie: IntegrityError) -> None:
        match ie.orig.__cause__:  # type: ignore[union-attr]
            case ForeignKeyViolationError():
                raise RefreshJobNoFeedError("Referenced feed does not exist") from ie
            case UniqueViolationError():
                raise _RefreshJobAlreadyExistsError("Refresh job already exists") from ie
            case _:
                raise ie

    async def update(self, *, job_id: int, updates: FeedRefreshJobUpdates) -> FeedRefreshJob:
        query = (
            sa.update(mdl.FeedRefreshJob)
            .where(mdl.FeedRefreshJob.c.id == job_id)
            .values(**updates.model_dump(exclude_unset=True))
            .returning(mdl.FeedRefreshJob)
        )

        async with self.db.begin() as conn:
            result = await conn.execute(query)

            if row := result.mappings().fetchone():
                return FeedRefreshJob.model_validate(dict(row))

        raise RefreshJobNotFoundError(f"Failed to update refresh job with {job_id=}")

    async def transit_state(
        self,
        job_id: int,
        old_state: FeedRefreshJobState,
        new_state: FeedRefreshJobState,
    ) -> FeedRefreshJob:
        select_for_update_q = (
            sa.select(mdl.FeedRefreshJob).with_for_update().where(mdl.FeedRefreshJob.c.id == job_id)
        )

        update_q = (
            sa.update(mdl.FeedRefreshJob)
            .where(
                sa.and_(
                    mdl.FeedRefreshJob.c.id == job_id,
                    mdl.FeedRefreshJob.c.state == old_state,
                )
            )
            .values(state=new_state)
            .returning(mdl.FeedRefreshJob)
        )

        async with self.db.begin() as conn:
            # lock the row to prevent concurrent state transitions
            await conn.execute(select_for_update_q)

            result = await conn.execute(update_q)
            if row := result.mappings().fetchone():
                return FeedRefreshJob.model_validate(dict(row))

        raise RefreshJobStateTransitionError(
            f"Failed to transit refresh job with {job_id=} from {old_state=} to {new_state=}"
        )
