import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Optional

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.feed import Feed
from awesome_rss_reader.core.entity.feed_post import FeedPostFiltering, FeedPostOrdering
from awesome_rss_reader.core.repository.feed_post import FeedPostNotFoundError
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.feed_posts import PostgresFeedPostRepository
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import (
    NewFeedFactory,
    NewFeedPostFactory,
    NewUserFeedFactory,
    NewUserPostFactory,
    UserFactory,
)
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
    InsertUserPostsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresFeedPostRepository:
    return PostgresFeedPostRepository(db=db)


@pytest_asyncio.fixture()
async def feed(insert_feeds: InsertFeedsFixtureT) -> Feed:
    feed, *_ = await insert_feeds(NewFeedFactory.build())
    return feed


async def test_get_by_id(
    repo: PostgresFeedPostRepository,
    insert_feed_posts: InsertFeedPostsFixtureT,
    feed: Feed,
) -> None:
    post1, post2 = await insert_feed_posts(
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="The Best High DPI Gaming Mice",
            guid="https://www.makeuseof.com/best-high-dpi-gaming-mice/",
        ),
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="Can ChatGPT Transform Healthcare?",
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )

    post = await repo.get_by_id(post1.id)
    assert post.title == "The Best High DPI Gaming Mice"

    post = await repo.get_by_id(post2.id)
    assert post.title == "Can ChatGPT Transform Healthcare?"

    with pytest.raises(FeedPostNotFoundError):
        await repo.get_by_id(99999)


async def test_get_by_guid(
    repo: PostgresFeedPostRepository,
    insert_feed_posts: InsertFeedPostsFixtureT,
    feed: Feed,
) -> None:
    post1, post2 = await insert_feed_posts(
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="The Best High DPI Gaming Mice",
            guid="https://www.makeuseof.com/best-high-dpi-gaming-mice/",
        ),
        NewFeedPostFactory.build(
            feed_id=feed.id,
            title="Can ChatGPT Transform Healthcare?",
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )

    post = await repo.get_by_guid(post1.guid)
    assert post.title == "The Best High DPI Gaming Mice"

    post = await repo.get_by_guid(post2.guid)
    assert post.title == "Can ChatGPT Transform Healthcare?"

    with pytest.raises(FeedPostNotFoundError):
        await repo.get_by_guid("https://www.makeuseof.com/not-existing/")


@pytest.mark.parametrize(
    "filter_by_factory, limit, offset, expected_titles",
    # fmt: off
    [
        # no filters
        (
            None,
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # no filters, has limit
        (
            None,
            3, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
            ],
        ),
        # no filters, has limit and offset
        (
            None,
            3, 2,
            [
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
            ],
        ),
        # no filters, offset beyond the end
        (None, 20, 10, []),
        # filter by feed_id
        (
            lambda f1, *_: FeedPostFiltering(feed_id=f1.id),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by feed with no posts
        (lambda f1, f2, f3: FeedPostFiltering(feed_id=f3.id), 20, 0, []),
        # filter by feed_id, has limit
        (
            lambda f1, *_: FeedPostFiltering(feed_id=f1.id),
            1, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
            ],
        ),
        # filter by followed_by by user1
        (
            lambda *_: FeedPostFiltering(
                followed_by=uuid.UUID("decade00-0000-4000-a000-000000000000")
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by followed_by by user1 and by feed_id
        (
            lambda f1, *_: FeedPostFiltering(
                feed_id=f1.id, followed_by=uuid.UUID("decade00-0000-4000-a000-000000000000")
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by followed_by by user1 and by feed_id with no posts
        (
            lambda f1, f2, f3: FeedPostFiltering(
                feed_id=f3.id, followed_by=uuid.UUID("decade00-0000-4000-a000-000000000000")
            ),
            20, 0,
            [],
        ),
        # filter by followed_by by user2
        (
            lambda *_: FeedPostFiltering(
                followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001")
            ),
            20, 0,
            [
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
            ],
        ),
        # filter by followed_by by user2 and by not followed feed_id
        (
            lambda f1, *_: FeedPostFiltering(
                feed_id=f1.id, followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001")
            ),
            20, 0,
            [],
        ),
        # filter by not_followed_by by user1
        (
            lambda *_: FeedPostFiltering(
                not_followed_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            ),
            20, 0,
            [],
        ),
        # filter by not_followed_by by user2
        (
            lambda *_: FeedPostFiltering(
                not_followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001")
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by not_followed_by by user2, but also limited by feed_id
        (
            lambda f1, f2, f3: FeedPostFiltering(
                not_followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
                feed_id=f2.id,
            ),
            20, 0,
            [],
        ),
        # filter by read_by by user1
        (
            lambda *_: FeedPostFiltering(
                read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            ),
            20, 0,
            [
                "5 Wellness Practices for Standing Desk Users",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by read_by by user1, but also limited by feed_id
        (
            lambda f1, *_: FeedPostFiltering(
                read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                feed_id=f1.id,
            ),
            20, 0,
            [
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by read_by by user1, but also limited by feed_id with no posts
        (
            lambda f1, f2, f3: FeedPostFiltering(
                read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                feed_id=f3.id,
            ),
            20, 0,
            [],
        ),
        # filter by read_by by user2
        (
            lambda *_: FeedPostFiltering(
                read_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
            ),
            20, 0,
            [],
        ),
        # filter by not_read_by by user1
        (
            lambda *_: FeedPostFiltering(
                not_read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "A Look at the Redesigned Apple Apps in watchOS 10",
            ],
        ),
        # filter by not_read_by by user1, but also limited by feed_id
        (
            lambda f1, *_: FeedPostFiltering(
                not_read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                feed_id=f1.id,
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
            ],
        ),
        # filter by not_read_by by user1, but also limited by feed_id with no posts
        (
            lambda f1, f2, f3: FeedPostFiltering(
                not_read_by=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                feed_id=f3.id,
            ),
            20, 0,
            [],
        ),
        # filter by not_read_by by user2
        (
            lambda *_: FeedPostFiltering(
                not_read_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
            ),
            20, 0,
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by followed_by and not_read_by by user2
        (
            lambda *_: FeedPostFiltering(
                followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
                not_read_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
            ),
            20, 0,
            [
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
            ],
        ),
        # filter by followed_by and not_read_by by user2, but also limited by feed_id
        (
            lambda f1, *_: FeedPostFiltering(
                feed_id=f1.id,
                followed_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
                not_read_by=uuid.UUID("facade00-0000-4000-a000-000000000001"),
            ),
            20, 0,
            [],
        ),
    ],
    # fmt: on
)
async def test_get_list(
    repo: PostgresFeedPostRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
    filter_by_factory: Optional[Callable],  # noqa: UP007
    limit: int,
    offset: int,
    expected_titles: list[str],
) -> None:
    now = now_aware()

    user1, user2 = (
        UserFactory.build(uid=uid)
        for uid in (
            uuid.UUID("decade00-0000-4000-a000-000000000000"),
            uuid.UUID("facade00-0000-4000-a000-000000000001"),
        )
    )

    feed1, feed2, feed3 = await insert_feeds(*NewFeedFactory.batch(3))

    await insert_user_feeds(
        # user1 follows feed1 and feed2
        NewUserFeedFactory.build(user_uid=user1.uid, feed_id=feed1.id),
        NewUserFeedFactory.build(user_uid=user1.uid, feed_id=feed2.id),
        # user2 follows feed2 only
        NewUserFeedFactory.build(user_uid=user2.uid, feed_id=feed2.id),
    )

    p1, p2, p3, p4, p5, p6 = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="The Best High DPI Gaming Mice",
            feed_id=feed1.id,
            published_at=now - timedelta(hours=24),
            guid="https://www.makeuseof.com/best-high-dpi-gaming-mice/",
        ),
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed1.id,
            published_at=now - timedelta(hours=24),
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
        NewFeedPostFactory.build(
            title="A Look at the Redesigned Apple Apps in watchOS 10",
            feed_id=feed1.id,
            published_at=now - timedelta(hours=20),
            guid="https://www.makeuseof.com/a-look-at-the-redesigned-apple-apps-in-watchos-10/",
        ),
        NewFeedPostFactory.build(
            title="How to Write a CV for a Tech Job",
            feed_id=feed2.id,
            published_at=now - timedelta(hours=19),
            guid="https://www.makeuseof.com/how-to-write-a-cv-for-a-tech-job/",
        ),
        NewFeedPostFactory.build(
            title="4 Reasons to Buy the M2 Pro Mac mini",
            feed_id=feed1.id,
            published_at=now - timedelta(hours=18),
            guid="https://www.makeuseof.com/reasons-to-buy-the-m2-pro-mac-mini/",
        ),
        NewFeedPostFactory.build(
            title="5 Wellness Practices for Standing Desk Users",
            feed_id=feed2.id,
            published_at=now - timedelta(hours=20),
            guid="https://www.makeuseof.com/wellness-practices-for-standing-desk-users/",
        ),
    )

    await insert_user_posts(
        NewUserPostFactory.build(
            user_uid=user1.uid,
            post_id=p1.id,
        ),
        NewUserPostFactory.build(
            user_uid=user1.uid,
            post_id=p2.id,
        ),
        NewUserPostFactory.build(
            user_uid=user1.uid,
            post_id=p6.id,
        ),
    )

    filter_by = None if filter_by_factory is None else filter_by_factory(feed1, feed2, feed3)

    posts = await repo.get_list(
        filter_by=filter_by,
        order_by=FeedPostOrdering.published_at_desc,
        limit=limit,
        offset=offset,
    )
    assert [post.title for post in posts] == expected_titles


async def test_create_many(
    repo: PostgresFeedPostRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    fetchmany: FetchManyFixtureT,
) -> None:
    feed, other_feed = await insert_feeds(
        NewFeedFactory.build(url="https://www.makeuseof.com/feed/"),
        NewFeedFactory.build(url="https://feeds.simplecast.com/54nAGcIl"),
    )

    existing_posts = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="The Best High DPI Gaming Mice",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/best-high-dpi-gaming-mice/",
        ),
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
        NewFeedPostFactory.build(
            title="4 Reasons to Buy the M2 Pro Mac mini",
            feed_id=other_feed.id,
            guid="https://www.makeuseof.com/reasons-to-buy-the-m2-pro-mac-mini/",
        ),
    )

    created_posts = await repo.create_many(
        [
            NewFeedPostFactory.build(
                feed_id=feed.id,
                guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
            ),
            NewFeedPostFactory.build(
                feed_id=other_feed.id,
                guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
            ),
            NewFeedPostFactory.build(
                feed_id=feed.id,
                guid="https://www.makeuseof.com/best-high-dpi-gaming-mice/",
            ),
            NewFeedPostFactory.build(
                feed_id=feed.id,
                guid="https://www.makeuseof.com/wellness-practices-for-standing-desk-users/",
            ),
        ]
    )
    assert len(created_posts) == 2

    new_db_rows = await fetchmany(
        sa.select(mdl.FeedPost)
        .where(~mdl.FeedPost.c.id.in_([p.id for p in existing_posts]))
        .order_by(mdl.FeedPost.c.id.asc())
    )
    assert len(new_db_rows) == 2

    new_db_row1, new_db_row2 = new_db_rows
    assert new_db_row1["feed_id"] == other_feed.id
    assert new_db_row1["guid"] == "https://www.makeuseof.com/can-chatgpt-transform-healthcare/"
    # fmt: off
    assert new_db_row2["feed_id"] == feed.id
    assert new_db_row2["guid"] == "https://www.makeuseof.com/wellness-practices-for-standing-desk-users/"  # noqa: E501
    # fmt: on
