import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.user_feed import NewUserFeed
from awesome_rss_reader.core.repository.user_feed import UserFeedNoFeedError, UserFeedNotFoundError
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.user_feeds import PostgresUserFeedRepository
from tests.factories import NewFeedFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresUserFeedRepository:
    return PostgresUserFeedRepository(db=db)


async def test_get_by_id(
    repo: PostgresUserFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
        NewFeedFactory.build(url="https://example.com/feed.rss"),
    )

    uf1, uf2 = await insert_user_feeds(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed1.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            feed_id=feed2.id,
        ),
    )

    got1 = await repo.get_by_id(uf1.id)
    assert got1.feed_id == feed1.id
    assert got1.user_uid == uuid.UUID("decade00-0000-4000-a000-000000000000")

    got2 = await repo.get_by_id(uf2.id)
    assert got2.feed_id == feed2.id
    assert got2.user_uid == uuid.UUID("facade00-0000-4000-a000-000000000000")


@pytest.mark.parametrize("user_feed_id", [-1, 0, 999999])
async def test_get_by_id_not_found(
    repo: PostgresUserFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    user_feed_id: int,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    await insert_user_feeds(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed.id,
        ),
    )

    with pytest.raises(UserFeedNotFoundError):
        await repo.get_by_id(user_feed_id)


@pytest.mark.parametrize(
    "user_uid, feed_name, found",
    [
        # user1
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Example Feed", True),
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Example RSS", True),
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Example Atom", False),
        # user2
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Example Feed", False),
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Example RSS", False),
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Example Atom", True),
        # unrecognized user
        (uuid.uuid4(), "Example Feed", False),
    ],
)
async def test_get_for_user_and_feed(
    repo: PostgresUserFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    user_uid: uuid.UUID,
    feed_name: str,
    found: bool,
) -> None:
    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(
            url="https://example.com/feed.xml",
            title="Example Feed",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.rss",
            title="Example RSS",
        ),
        NewFeedFactory.build(
            url="https://example.com/feed.atom",
            title="Example Atom",
        ),
    )
    await insert_user_feeds(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed1.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed2.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            feed_id=feed3.id,
        ),
    )

    feed_id = {
        "Example Feed": feed1.id,
        "Example RSS": feed2.id,
        "Example Atom": feed3.id,
    }[feed_name]

    if found:
        got = await repo.get_for_user_and_feed(user_uid=user_uid, feed_id=feed_id)
        assert got.user_uid == user_uid
        assert got.feed_id == feed_id
    else:
        with pytest.raises(UserFeedNotFoundError):
            await repo.get_for_user_and_feed(user_uid=user_uid, feed_id=feed_id)


async def test_get_or_create_new(
    repo: PostgresUserFeedRepository,
    insert_feeds: InsertFeedsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed1, feed2 = await insert_feeds(*NewFeedFactory.batch(2))

    new_user_feeds = [
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed1.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed2.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            feed_id=feed1.id,
        ),
    ]

    for new_uf in new_user_feeds:
        user_feed = await repo.get_or_create(new_uf)
        assert user_feed.id is not None
        assert user_feed.user_uid == new_uf.user_uid
        assert user_feed.feed_id == new_uf.feed_id
        assert user_feed.created_at is not None

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.UserFeed).order_by(mdl.UserFeed.c.id.asc())
    )

    assert db_row1["user_uid"] == uuid.UUID("decade00-0000-4000-a000-000000000000")
    assert db_row1["feed_id"] == feed1.id

    assert db_row2["user_uid"] == uuid.UUID("decade00-0000-4000-a000-000000000000")
    assert db_row2["feed_id"] == feed2.id

    assert db_row3["user_uid"] == uuid.UUID("facade00-0000-4000-a000-000000000000")
    assert db_row3["feed_id"] == feed1.id


async def test_get_or_create_user_feed_already_exists(
    repo: PostgresUserFeedRepository,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    existing_user_feed, *_ = await insert_user_feeds(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed.id,
        ),
    )

    user_feed = await repo.get_or_create(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed.id,
        ),
    )
    assert user_feed.id == existing_user_feed.id

    db_rows = await fetchmany(sa.select(mdl.UserFeed))
    assert len(db_rows) == 1


async def test_get_or_create_feed_not_found(repo: PostgresUserFeedRepository) -> None:
    with pytest.raises(UserFeedNoFeedError):
        await repo.get_or_create(
            NewUserFeed(
                user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                feed_id=9999,
            )
        )


async def test_delete(
    repo: PostgresUserFeedRepository,
    fetchone: FetchOneFixtureT,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(NewFeedFactory.build(url="https://example.com/feed.xml"))
    uf1, uf2 = await insert_user_feeds(
        NewUserFeed(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            feed_id=feed.id,
        ),
        NewUserFeed(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            feed_id=feed.id,
        ),
    )

    await repo.delete(uf1.id)
    # the specified user feed should be deleted
    no_rows = await fetchmany(sa.select(mdl.UserFeed).where(mdl.UserFeed.c.id == uf1.id))
    assert no_rows == []

    # the other user feed should not be deleted
    other_row = await fetchone(sa.select(mdl.UserFeed).where(mdl.UserFeed.c.id == uf2.id))
    assert other_row["id"] == uf2.id

    # the delete operation is idempotent
    await repo.delete(uf1.id)
