from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

import sqlalchemy as sa
from mypy_extensions import VarArg

from awesome_rss_reader.core.entity.feed import Feed, NewFeed
from awesome_rss_reader.core.entity.feed_post import FeedPost, NewFeedPost, NewUserPost, UserPost
from awesome_rss_reader.core.entity.feed_refresh_job import FeedRefreshJob, NewFeedRefreshJob
from awesome_rss_reader.core.entity.user_feed import NewUserFeed, UserFeed

# fmt: off
FetchOneFixtureT: TypeAlias = Callable[[sa.Select], Awaitable[dict[str, Any]]]
FetchManyFixtureT: TypeAlias = Callable[[sa.Select], Awaitable[list[dict[str, Any]]]]
InsertOneFixtureT: TypeAlias = Callable[[sa.Insert], Awaitable[dict[str, Any]]]
InsertManyFixtureT: TypeAlias = Callable[[sa.Insert], Awaitable[list[dict[str, Any]]]]

InsertFeedsFixtureT: TypeAlias = Callable[[VarArg(NewFeed)], Awaitable[list[Feed]]]
InsertUserFeedsFixtureT: TypeAlias = Callable[[VarArg(NewUserFeed)], Awaitable[list[UserFeed]]]
InsertFeedPostsFixtureT: TypeAlias = Callable[[VarArg(NewFeedPost)], Awaitable[list[FeedPost]]]
InsertUserPostsFixtureT: TypeAlias = Callable[[VarArg(NewUserPost)], Awaitable[list[UserPost]]]
InsertRefreshJobsFixtureT: TypeAlias = Callable[[VarArg(NewFeedRefreshJob)], Awaitable[list[FeedRefreshJob]]]  # noqa: E501
# fmt: on
