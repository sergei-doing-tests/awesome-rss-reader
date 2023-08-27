import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed import FeedOrdering, NewFeed
from awesome_rss_reader.core.entity.user_feed import NewUserFeed
from awesome_rss_reader.core.repository.feed import FeedNotFoundError
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.feeds import PostgresFeedRepository
from tests.factories.feed import NewFeedFactory
from tests.factories.user import UserFactory
from tests.pytest_fixtures.types import (
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresFeedRepository:
    return PostgresFeedRepository(db=db)


@pytest_asyncio.fixture()
async def _setup_feeds(
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
) -> None:
    now = datetime.now(tz=UTC)
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(
            url="https://example.com/feed.xml",
            title="Example Feed",
            refreshed_at=now - timedelta(days=1),
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.rss",
            title="Example RSS",
            refreshed_at=now - timedelta(days=1),
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.atom",
            title="Example Atom",
            refreshed_at=now - timedelta(hours=1),
        ),
    )

    user_uids = [
        uuid.UUID("decade00-0000-4000-a000-000000000000"),
        uuid.UUID("facade00-0000-4000-a000-000000000000"),
        uuid.UUID("c0c0a000-0000-4000-a000-000000000000"),
    ]
    user1, user2, user3 = (UserFactory.build(uid=uid) for uid in user_uids)

    # feeds followed by user1
    for feed_id in [feed1.id, feed2.id, feed3.id]:
        await insert_user_feeds(
            NewUserFeed(
                user_uid=user1.uid,
                feed_id=feed_id,
            ),
        )

    # feeds followed by user2
    for feed_id in [feed3.id]:
        await insert_user_feeds(
            NewUserFeed(
                user_uid=user2.uid,
                feed_id=feed_id,
            ),
        )


async def test_get_by_id(repo: PostgresFeedRepository, insert_feeds: InsertFeedsFixtureT) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(
            url="https://example.com/feed.xml",
            title="Example Feed",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.rss",
            title="Example RSS",
        ),
    )

    got1 = await repo.get_by_id(feed1.id)
    assert got1.title == "Example Feed"

    got2 = await repo.get_by_id(feed2.id)
    assert got2.title == "Example RSS"


@pytest.mark.parametrize("feed_id", [-1, 0, 999999])
async def test_get_by_id_not_found(
    repo: PostgresFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    feed_id: int,
) -> None:
    # have some feeds in the db
    feeds = [
        NewFeedFactory.build(url=feed_url)
        for feed_url in ("https://example.com/feed.xml", "https://example.com/feed.rss")
    ]
    await insert_feeds(*feeds)

    with pytest.raises(FeedNotFoundError):
        await repo.get_by_id(feed_id)


async def test_get_by_url(repo: PostgresFeedRepository, insert_feeds: InsertFeedsFixtureT) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(
            url="https://example.com/feed.xml",
            title="Example Feed",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.rss",
            title="Example RSS",
        ),
    )

    got1 = await repo.get_by_url(feed1.url)
    assert got1.title == "Example Feed"

    got2 = await repo.get_by_url(feed2.url)
    assert got2.title == "Example RSS"


@pytest.mark.parametrize(
    "test_url",
    [
        "https://www.makeuseof.com/feed/",
        "https://ultimateclassicrock.com/feed/",
    ],
)
async def test_get_by_url_not_found(
    repo: PostgresFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    test_url: str,
) -> None:
    # have some feeds in the db
    feeds = [
        NewFeedFactory.build(url=url)
        for url in ("https://example.com/feed.xml", "https://example.com/feed.rss")
    ]
    await insert_feeds(*feeds)

    with pytest.raises(FeedNotFoundError):
        await repo.get_by_url(test_url)


async def test_get_or_create_new(repo: PostgresFeedRepository, fetchone: FetchOneFixtureT) -> None:
    new_feed = NewFeed(url="https://example.com/feed.xml")
    feed = await repo.get_or_create(new_feed=new_feed)

    assert feed.id is not None
    assert feed.url == new_feed.url
    assert feed.title is None
    assert feed.refreshed_at is None
    assert feed.created_at is not None

    query = sa.select(mdl.Feed).where(mdl.Feed.c.id == feed.id)
    db_row = await fetchone(query)
    assert db_row is not None
    assert db_row["id"] == feed.id
    assert db_row["url"] == feed.url
    assert db_row["title"] is None
    assert db_row["refreshed_at"] is None
    assert db_row["created_at"] == feed.created_at


async def test_get_or_create_existing(
    repo: PostgresFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    existing_feed, *_ = await insert_feeds(
        NewFeed(
            url="https://example.com/feed.xml",
            title="Example Feed",
            refreshed_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        )
    )

    new_feed = NewFeed(url="https://example.com/feed.xml", title="New Title")
    feed = await repo.get_or_create(new_feed=new_feed)

    assert feed.id == existing_feed.id
    assert feed.url == "https://example.com/feed.xml"
    assert feed.title == "Example Feed"
    assert feed.refreshed_at == datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC)
    assert feed.created_at is not None


async def test_get_or_create_feed_with_same_title(
    repo: PostgresFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
) -> None:
    neighbor_feed, *_ = await insert_feeds(
        NewFeed(
            url="https://example.com/feed.xml",
            title="Example Feed",
            refreshed_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        )
    )

    new_feed = NewFeed(
        url="https://example.com/feed.rss",
        title="Example Feed",
    )
    feed = await repo.get_or_create(new_feed=new_feed)

    assert feed.id != neighbor_feed.id

    assert feed.url == "https://example.com/feed.rss"
    assert feed.title == "Example Feed"


@pytest.mark.usefixtures("_setup_feeds")
@pytest.mark.parametrize(
    "offset, limit, expected",
    [
        (0, 10, ["Example Feed", "Example RSS", "Example Atom"]),
        (1, 10, ["Example RSS", "Example Atom"]),
        (1, 1, ["Example RSS"]),
        (3, 1, []),
        (3, 10, []),
    ],
)
async def test_get_list_default_ordering(
    repo: PostgresFeedRepository,
    offset: int,
    limit: int,
    expected: list[str],
) -> None:
    feeds = await repo.get_list(limit=limit, offset=offset)
    assert [f.title for f in feeds] == expected


@pytest.mark.usefixtures("_setup_feeds")
@pytest.mark.parametrize(
    "offset, limit, expected",
    [
        (0, 10, ["Example Atom", "Example RSS", "Example Feed"]),
        (1, 10, ["Example RSS", "Example Feed"]),
        (3, 10, []),
    ],
)
async def test_get_list_order_by_refreshed_at_desc(
    repo: PostgresFeedRepository,
    offset: int,
    limit: int,
    expected: list[str],
) -> None:
    feeds = await repo.get_list(limit=limit, offset=offset, order_by=FeedOrdering.refreshed_at_desc)
    assert [f.title for f in feeds] == expected


@pytest.mark.usefixtures("_setup_feeds")
@pytest.mark.parametrize(
    "user_uid, ordering, offset, limit, expected",
    [
        # user1 follows all feeds
        (
            uuid.UUID("decade00-0000-4000-a000-000000000000"),
            FeedOrdering.id_asc,
            0,
            10,
            ["Example Feed", "Example RSS", "Example Atom"],
        ),
        (
            uuid.UUID("decade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            0,
            10,
            ["Example Atom", "Example RSS", "Example Feed"],
        ),
        (
            uuid.UUID("decade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            1,
            1,
            ["Example RSS"],
        ),
        (
            uuid.UUID("decade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            10,
            10,
            [],
        ),
        # user2 follows only one feed
        (
            uuid.UUID("facade00-0000-4000-a000-000000000000"),
            FeedOrdering.id_asc,
            0,
            10,
            ["Example Atom"],
        ),
        (
            uuid.UUID("facade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            0,
            10,
            ["Example Atom"],
        ),
        (
            uuid.UUID("facade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            1,
            1,
            [],
        ),
        (
            uuid.UUID("facade00-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            10,
            20,
            [],
        ),
        # user3 follows no feeds
        (
            uuid.UUID("c0c0a000-0000-4000-a000-000000000000"),
            FeedOrdering.id_asc,
            0,
            10,
            [],
        ),
        (
            uuid.UUID("c0c0a000-0000-4000-a000-000000000000"),
            FeedOrdering.refreshed_at_desc,
            0,
            10,
            [],
        ),
    ],
)
async def test_get_list_followed_by_user(
    repo: PostgresFeedRepository,
    user_uid: uuid.UUID,
    ordering: FeedOrdering,
    offset: int,
    limit: int,
    expected: list[str],
) -> None:
    feeds = await repo.get_list(
        limit=limit,
        offset=offset,
        followed_by=user_uid,
        order_by=ordering,
    )
    assert [f.title for f in feeds] == expected
