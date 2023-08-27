from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

import sqlalchemy as sa
from mypy_extensions import VarArg

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJob, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed

FetchOneFixtureT: TypeAlias = Callable[[sa.Select], Awaitable[dict[str, Any] | None]]
FetchManyFixtureT: TypeAlias = Callable[[sa.Select], Awaitable[list[dict[str, Any]]]]
InsertManyFixtureT: TypeAlias = Callable[[sa.Insert], Awaitable[list[dict[str, Any]]]]

InsertFeedsFixtureT: TypeAlias = Callable[[VarArg(NewFeed)], Awaitable[list[Feed]]]
InsertUserFeedsFixtureT: TypeAlias = Callable[[VarArg(NewUserFeed)], Awaitable[list[UserFeed]]]
InsertRefreshJobsFixtureT: TypeAlias = Callable[
    [VarArg(NewFeedRefreshJob)], Awaitable[list[FeedRefreshJob]]
]
