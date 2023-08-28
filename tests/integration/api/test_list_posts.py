from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.utils.dtime import now_aware
from tests.factories import (
    NewFeedFactory,
    NewFeedPostFactory,
    NewUserFeedFactory,
    NewUserPostFactory,
    UserFactory,
)
from tests.pytest_fixtures.types import (
    InsertFeedPostsFixtureT,
    InsertFeedsFixtureT,
    InsertUserFeedsFixtureT,
    InsertUserPostsFixtureT,
)


@pytest.mark.parametrize(
    "query_params, expected_titles",
    [
        # no filters
        (
            {},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # explicit offset and limit
        (
            {"limit": "20", "offset": 0},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # small limit
        (
            {"limit": "3"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
            ],
        ),
        # small limit and offset
        (
            {"limit": "3", "offset": "2"},
            [
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
            ],
        ),
        # offset beyond the end of the collection
        (
            {"offset": "100"},
            [],
        ),
        # filter by feed
        (
            {"feed": "Feed 1"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by feed with no posts
        (
            {"feed": "Feed 3"},
            [],
        ),
        # filter by feed, apply limit
        (
            {"feed": "Feed 1", "limit": "1"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
            ],
        ),
        # filter by following
        (
            {"follow_status": "following"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "5 Wellness Practices for Standing Desk Users",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by following and feed id
        (
            {"follow_status": "following", "feed": "Feed 1"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by not following and feed with no posts
        (
            {"follow_status": "not_following", "feed": "Feed 3"},
            [],
        ),
        # filter by not following
        (
            {"follow_status": "not_following"},
            [],
        ),
        # filter by read
        (
            {"read_status": "read"},
            [
                "5 Wellness Practices for Standing Desk Users",
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by read and feed id
        (
            {"read_status": "read", "feed": "Feed 1"},
            [
                "Can ChatGPT Transform Healthcare?",
                "The Best High DPI Gaming Mice",
            ],
        ),
        # filter by read and feed with no posts
        (
            {"read_status": "read", "feed": "Feed 3"},
            [],
        ),
        # filter by unread
        (
            {"read_status": "unread"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "How to Write a CV for a Tech Job",
                "A Look at the Redesigned Apple Apps in watchOS 10",
            ],
        ),
        # filter by unread, but also restrict results by feed
        (
            {"read_status": "unread", "feed": "Feed 1"},
            [
                "4 Reasons to Buy the M2 Pro Mac mini",
                "A Look at the Redesigned Apple Apps in watchOS 10",
            ],
        ),
        # filter by unread, but also restrict results by feed with no posts
        (
            {"read_status": "unread", "feed": "Feed 3"},
            [],
        ),
    ],
    ids=str,
)
async def test_list_posts_happy_path(
    postgres_database: AsyncEngine,
    user: User,
    user_api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_user_feeds: InsertUserFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
    insert_user_posts: InsertUserPostsFixtureT,
    query_params: dict[str, Any],
    expected_titles: list[str],
) -> None:
    now = now_aware()
    other_user = UserFactory.build()

    feed1, feed2, feed3 = await insert_feeds(
        NewFeedFactory.build(title="Feed 1", url="https://example.com/feed1.xml"),
        NewFeedFactory.build(title="Feed 2", url="https://example.com/feed2.xml"),
        NewFeedFactory.build(title="Feed 3", url="https://example.com/feed3.xml"),
    )

    # in query params, replace feeds with actual feed ids
    if feed_name := query_params.pop("feed", None):
        query_params["feed_id"] = {
            "Feed 1": feed1.id,
            "Feed 2": feed2.id,
            "Feed 3": feed3.id,
        }[feed_name]

    await insert_user_feeds(
        # the user follows feed1 and feed2
        NewUserFeedFactory.build(user_uid=user.uid, feed_id=feed1.id),
        NewUserFeedFactory.build(user_uid=user.uid, feed_id=feed2.id),
        # other user follows feed2 only
        NewUserFeedFactory.build(user_uid=other_user.uid, feed_id=feed2.id),
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
        # the user follows the posts:
        # - The Best High DPI Gaming Mice
        # - Can ChatGPT Transform Healthcare?
        # - 5 Wellness Practices for Standing Desk Users
        NewUserPostFactory.build(
            user_uid=user.uid,
            post_id=p1.id,
        ),
        NewUserPostFactory.build(
            user_uid=user.uid,
            post_id=p2.id,
        ),
        NewUserPostFactory.build(
            user_uid=user.uid,
            post_id=p6.id,
        ),
        # the other user follows the posts:
        # - How to Write a CV for a Tech Job
        NewUserPostFactory.build(
            user_uid=other_user.uid,
            post_id=p4.id,
        ),
    )

    resp = user_api_client.get("/api/posts", params=query_params)
    assert resp.status_code == 200

    actual_titles = [post["title"] for post in resp.json()]
    assert actual_titles == expected_titles


async def test_list_posts_requires_auth(
    postgres_database: AsyncEngine,
    api_client: TestClient,
    insert_feeds: InsertFeedsFixtureT,
    insert_feed_posts: InsertFeedPostsFixtureT,
) -> None:
    feed, *_ = await insert_feeds(
        NewFeedFactory.build(url="https://example.com/feed.xml"),
    )
    await insert_feed_posts(
        NewFeedPostFactory.build(
            title="The Best High DPI Gaming Mice",
            feed_id=feed.id,
        )
    )

    resp = api_client.get("/api/feeds")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
