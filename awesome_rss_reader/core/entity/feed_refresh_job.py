from enum import Enum, IntEnum, auto

from pydantic import AwareDatetime, BaseModel, Field

from awesome_rss_reader.utils.dtime import now_aware


class FeedRefreshJobState(IntEnum):
    pending = auto()
    in_progress = auto()
    complete = auto()
    failed = auto()


class NewFeedRefreshJob(BaseModel):
    feed_id: int
    state: FeedRefreshJobState = FeedRefreshJobState.pending
    execute_after: AwareDatetime = Field(
        description="Time at which the job is scheduled to run",
        default_factory=now_aware,
    )
    retries: int = Field(
        description="Number of times the job has been retried so far",
        default=0,
    )


class FeedRefreshJob(NewFeedRefreshJob):
    id: int  # noqa: A003
    state_changed_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime


class FeedRefreshJobUpdates(BaseModel):
    execute_after: AwareDatetime | None = None
    retries: int | None = None


class FeedRefreshJobFiltering(BaseModel):
    state: FeedRefreshJobState | None = None
    state_changed_before: AwareDatetime | None = None
    execute_before: AwareDatetime | None = None


class FeedRefreshJobOrdering(Enum):
    id_asc = auto()
    execute_after_asc = auto()
    state_changed_at_asc = auto()
