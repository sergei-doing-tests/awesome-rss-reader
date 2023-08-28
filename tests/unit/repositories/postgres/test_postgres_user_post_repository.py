import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from awesome_rss_reader.core.entity.user_post import NewUserPost
from awesome_rss_reader.core.repository.user_post import UserPostNoPostError, UserPostNotFoundError
from awesome_rss_reader.data.postgres import models as mdl
from awesome_rss_reader.data.postgres.repositories.user_posts import PostgresUserPostRepository
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import NewFeedFactory, NewFeedPostFactory, NewUserPostFactory
from tests.pytest_fixtures.types import (
    FetchManyFixtureT,
    FetchOneFixtureT,
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertUserPostsFixtureT,
)


@pytest_asyncio.fixture()
async def repo(db: AsyncEngine) -> PostgresUserPostRepository:
    return PostgresUserPostRepository(db=db)


async def test_get_by_id(
    repo: PostgresUserPostRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    post, *_ = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )
    up1, up2 = await insert_user_posts(
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            post_id=post.id,
        ),
    )

    got1 = await repo.get_by_id(up1.id)
    assert got1.post_id == post.id
    assert got1.user_uid == uuid.UUID("decade00-0000-4000-a000-000000000000")

    got2 = await repo.get_by_id(up2.id)
    assert got2.post_id == post.id
    assert got2.user_uid == uuid.UUID("facade00-0000-4000-a000-000000000000")

    with pytest.raises(UserPostNotFoundError):
        await repo.get_by_id(999999)


@pytest.mark.parametrize(
    "user_uid, post_title, found",
    [
        # user1
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Post 1", True),
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Post 2", True),
        (uuid.UUID("decade00-0000-4000-a000-000000000000"), "Post 3", False),
        # user2
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Post 1", False),
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Post 2", False),
        (uuid.UUID("facade00-0000-4000-a000-000000000000"), "Post 3", True),
        # unrecognized user
        (uuid.uuid4(), "Post 1", False),
    ],
)
async def test_get_for_user_and_post(
    repo: PostgresUserPostRepository,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
    user_uid: uuid.UUID,
    post_title: str,
    found: bool,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    post1, post2, post3 = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Post 1",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/post-1/",
        ),
        NewFeedPostFactory.build(
            title="Post 2",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/post-2/",
        ),
        NewFeedPostFactory.build(
            title="Post 3",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/post-3/",
        ),
    )
    await insert_user_posts(
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post1.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post2.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            post_id=post3.id,
        ),
    )

    post_id = {
        "Post 1": post1.id,
        "Post 2": post2.id,
        "Post 3": post3.id,
    }[post_title]

    if found:
        got = await repo.get_for_user_and_post(user_uid=user_uid, post_id=post_id)
        assert got.user_uid == user_uid
        assert got.post_id == post_id
    else:
        with pytest.raises(UserPostNotFoundError):
            await repo.get_for_user_and_post(user_uid=user_uid, post_id=post_id)


async def test_get_or_create_new(
    repo: PostgresUserPostRepository,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
) -> None:
    then = now_aware()

    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    post1, post2 = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
        NewFeedPostFactory.build(
            title="How to Use the New Google Chrome Memories Feature",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/how-to-use-the-new-google-chrome-memories-feature/",
        ),
    )

    new_user_posts = [
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post1.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post2.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            post_id=post1.id,
        ),
    ]

    for new_up in new_user_posts:
        user_post = await repo.get_or_create(new_up)
        assert user_post.id is not None
        assert user_post.user_uid == new_up.user_uid
        assert user_post.post_id == new_up.post_id
        assert user_post.read_at >= then

    db_row1, db_row2, db_row3 = await fetchmany(
        sa.select(mdl.UserPost).order_by(mdl.UserPost.c.id.asc())
    )

    assert db_row1["user_uid"] == uuid.UUID("decade00-0000-4000-a000-000000000000")
    assert db_row1["post_id"] == post1.id

    assert db_row2["user_uid"] == uuid.UUID("decade00-0000-4000-a000-000000000000")
    assert db_row2["post_id"] == post2.id

    assert db_row3["user_uid"] == uuid.UUID("facade00-0000-4000-a000-000000000000")
    assert db_row3["post_id"] == post1.id


async def test_get_or_create_existing(
    repo: PostgresUserPostRepository,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    post, *_ = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )

    existing_user_post, *_ = await insert_user_posts(
        NewUserPost(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post.id,
            read_at=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
    )

    user_post = await repo.get_or_create(
        NewUserPost(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post.id,
            read_at=now_aware(),
        ),
    )
    assert user_post.id == existing_user_post.id

    db_rows = await fetchmany(sa.select(mdl.UserPost))
    assert len(db_rows) == 1


async def test_get_or_create_post_not_found(repo: PostgresUserPostRepository) -> None:
    with pytest.raises(UserPostNoPostError):
        await repo.get_or_create(
            NewUserPostFactory.build(
                user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                post_id=9999,
            )
        )


async def test_delete(
    repo: PostgresUserPostRepository,
    fetchone: FetchOneFixtureT,
    fetchmany: FetchManyFixtureT,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    post, *_ = await insert_feed_posts(
        NewFeedPostFactory.build(
            title="Can ChatGPT Transform Healthcare?",
            feed_id=feed.id,
            guid="https://www.makeuseof.com/can-chatgpt-transform-healthcare/",
        ),
    )
    up1, up2 = await insert_user_posts(
        NewUserPostFactory.build(
            user_uid=uuid.UUID("decade00-0000-4000-a000-000000000000"),
            post_id=post.id,
        ),
        NewUserPostFactory.build(
            user_uid=uuid.UUID("facade00-0000-4000-a000-000000000000"),
            post_id=post.id,
        ),
    )

    await repo.delete(up1.id)
    # the specified user post should be deleted
    no_rows = await fetchmany(sa.select(mdl.UserPost).where(mdl.UserPost.c.id == up1.id))
    assert no_rows == []

    # the other user post should not be deleted
    other_row = await fetchone(sa.select(mdl.UserPost).where(mdl.UserPost.c.id == up2.id))
    assert other_row["id"] == up2.id

    # the delete operation is idempotent
    await repo.delete(up1.id)
