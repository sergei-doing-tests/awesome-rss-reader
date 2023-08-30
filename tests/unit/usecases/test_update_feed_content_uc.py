import uuid
from datetime import UTC, datetime
from unittest import mock

import pytest

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.feed import FeedFiltering, FeedUpdates
from awesome_rss_reader.core.entity.feed_content import (
    FeedContentBatchRequest,
    FeedContentBatchResponse,
    FeedContentRequest,
    FeedContentResult,
    FeedContentResultItem,
)
from awesome_rss_reader.core.entity.feed_post import NewFeedPost
from awesome_rss_reader.core.entity.feed_refresh_job import (
    FeedRefreshJobFiltering,
    FeedRefreshJobOrdering,
    FeedRefreshJobState,
    FeedRefreshJobUpdates,
)
from awesome_rss_reader.core.repository.feed_content import FeedContentParseError
from awesome_rss_reader.core.usecase.update_feed_content import (
    UpdateFeedContentInput,
    UpdateFeedContentUseCase,
)
from tests.factories import FeedFactory, FeedRefreshJobFactory


@pytest.fixture()
def uc(
    container: Container,
    job_repository: mock.Mock,
    feed_repository: mock.Mock,
    feed_content_repository: mock.Mock,
    post_repository: mock.Mock,
    user_feed_repository: mock.Mock,
) -> UpdateFeedContentUseCase:
    return container.use_cases.update_feed_content()


@mock.patch(
    "awesome_rss_reader.core.usecase.update_feed_content.now_aware",
    return_value=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
)
@mock.patch(
    "awesome_rss_reader.core.usecase.update_feed_content.uuid.uuid4",
    side_effect=[
        uuid.UUID("decade00-0000-4000-a000-000000000000"),
        uuid.UUID("facade00-0000-4000-a000-000000000000"),
        uuid.UUID("5ca1ab1e-0000-4000-a000-000000000000"),
        uuid.UUID("c0c0a000-0000-4000-a000-000000000000"),
    ],
)
async def test_happy_path(
    uuid4_mock: mock.Mock,
    now_aware_mock: mock.Mock,
    uc: UpdateFeedContentUseCase,
    job_repository: mock.Mock,
    feed_repository: mock.Mock,
    post_repository: mock.Mock,
    feed_content_repository: mock.Mock,
) -> None:
    feed1, feed2, feed3, feed4, feed5 = [
        FeedFactory.build(
            id=1,
            url="http://example.com/feed1",
            title="Feed 1",
            published_at=datetime(2006, 1, 1, 1, 1, 1, 999999, tzinfo=UTC),
        ),
        FeedFactory.build(
            id=2,
            url="http://example.com/feed2",
            title=None,
            published_at=None,
        ),
        FeedFactory.build(
            id=3,
            url="http://example.com/feed3",
            title="Feed 3",
            published_at=datetime(2006, 2, 2, 2, 2, 2, 999999, tzinfo=UTC),
        ),
        FeedFactory.build(
            id=4,
            url="http://example.com/feed4",
            title="Feed 4",
            published_at=None,
        ),
        FeedFactory.build(
            id=5,
            url="http://example.com/feed5",
            title="Feed 5",
            published_at=None,
        ),
    ]

    available_jobs = [
        FeedRefreshJobFactory.build(
            id=1,
            feed_id=feed1.id,
            state=FeedRefreshJobState.complete,
            retries=1,
        ),
        FeedRefreshJobFactory.build(
            id=2,
            feed_id=feed2.id,
            state=FeedRefreshJobState.complete,
            retries=0,
        ),
        FeedRefreshJobFactory.build(
            id=3,
            feed_id=feed3.id,
            state=FeedRefreshJobState.complete,
            retries=2,
        ),
        FeedRefreshJobFactory.build(
            id=4,
            feed_id=feed4.id,
            state=FeedRefreshJobState.complete,
            retries=0,
        ),
        FeedRefreshJobFactory.build(
            id=5,
            feed_id=feed5.id,
            state=FeedRefreshJobState.complete,
            retries=3,
        ),
    ]

    received_jobs = [
        FeedRefreshJobFactory.build(
            id=1,
            feed_id=feed1.id,
            state=FeedRefreshJobState.in_progress,
            retries=1,
        ),
        FeedRefreshJobFactory.build(
            id=2,
            feed_id=feed2.id,
            state=FeedRefreshJobState.in_progress,
            retries=0,
        ),
        FeedRefreshJobFactory.build(
            id=3,
            feed_id=feed3.id,
            state=FeedRefreshJobState.in_progress,
            retries=2,
        ),
        # job 4 was not received
        FeedRefreshJobFactory.build(
            id=5,
            feed_id=feed5.id,
            state=FeedRefreshJobState.in_progress,
            retries=3,
        ),
    ]

    job_repository.get_list.return_value = available_jobs
    job_repository.transit_state.side_effect = received_jobs
    job_repository.transit_state_batch.return_value = received_jobs
    feed_repository.get_list.return_value = [feed1, feed2, feed3, feed5]
    feed_content_repository.fetch_many.return_value = FeedContentBatchResponse(
        results={
            uuid.UUID("decade00-0000-4000-a000-000000000000"): FeedContentResult(
                title="Best RSS Feed",
                published_at=datetime(2023, 1, 1, 1, 1, 1, 999999, tzinfo=UTC),
                items=[],
            ),
            uuid.UUID("facade00-0000-4000-a000-000000000000"): FeedContentResult(
                title="Also not bad RSS Feed",
                published_at=datetime(2023, 9, 9, 9, 9, 9, 999999, tzinfo=UTC),
                items=[
                    FeedContentResultItem(
                        title="Can you believe it?",
                        summary="I can't",
                        url="http://example.com/feed2/1",  # type: ignore[arg-type]
                        guid="http://example.com/feed2/1",
                        published_at=datetime(2023, 8, 8, 8, 8, 8, 999999, tzinfo=UTC),
                    ),
                    FeedContentResultItem(
                        title="How about that?",
                        summary=None,
                        url="http://example.com/feed2/2",  # type: ignore[arg-type]
                        guid="http://example.com/feed2/2",
                        published_at=datetime(2023, 9, 9, 9, 9, 9, 999999, tzinfo=UTC),
                    ),
                ],
            ),
        },
        errors={
            uuid.UUID("5ca1ab1e-0000-4000-a000-000000000000"): FeedContentParseError("error"),
            uuid.UUID("c0c0a000-0000-4000-a000-000000000000"): FeedContentParseError("error"),
        },
    )

    uc_input = UpdateFeedContentInput(batch_size=100)
    await uc.execute(uc_input)

    job_repository.get_list.assert_called_once_with(
        filter_by=FeedRefreshJobFiltering(
            state=FeedRefreshJobState.pending,
            execute_before=datetime(2006, 1, 2, 15, 4, 5, 999999, tzinfo=UTC),
        ),
        order_by=FeedRefreshJobOrdering.state_changed_at_asc,
        offset=0,
        limit=100,
    )
    job_repository.transit_state_batch.assert_called_once_with(
        job_ids=[1, 2, 3, 4, 5],
        old_state=FeedRefreshJobState.pending,
        new_state=FeedRefreshJobState.in_progress,
    )
    # the job 4 was not received (some other process took it)
    feed_repository.get_list.assert_called_once_with(
        filter_by=FeedFiltering(
            feed_ids=[1, 2, 3, 5],
        ),
        limit=4,
        offset=0,
    )
    feed_content_repository.fetch_many.assert_called_once_with(
        FeedContentBatchRequest(
            timeout_s=10,
            max_body_size_b=512 * 1024,
            requests=[
                FeedContentRequest(
                    request_id=uuid.UUID("decade00-0000-4000-a000-000000000000"),
                    url="http://example.com/feed1",
                    published_since=datetime(2006, 1, 1, 1, 1, 1, 999999, tzinfo=UTC),
                ),
                FeedContentRequest(
                    request_id=uuid.UUID("facade00-0000-4000-a000-000000000000"),
                    url="http://example.com/feed2",
                    published_since=None,
                ),
                FeedContentRequest(
                    request_id=uuid.UUID("5ca1ab1e-0000-4000-a000-000000000000"),
                    url="http://example.com/feed3",
                    published_since=datetime(2006, 2, 2, 2, 2, 2, 999999, tzinfo=UTC),
                ),
                FeedContentRequest(
                    request_id=uuid.UUID("c0c0a000-0000-4000-a000-000000000000"),
                    url="http://example.com/feed5",
                    published_since=None,
                ),
            ],
        )
    )

    # all jobs except the feed 3 job move to complete state, and the job 3 is retried
    job_repository.transit_state.assert_has_calls(
        [
            mock.call(
                job_id=1,
                old_state=FeedRefreshJobState.in_progress,
                new_state=FeedRefreshJobState.complete,
            ),
            mock.call(
                job_id=2,
                old_state=FeedRefreshJobState.in_progress,
                new_state=FeedRefreshJobState.complete,
            ),
            mock.call(
                job_id=3,
                old_state=FeedRefreshJobState.in_progress,
                new_state=FeedRefreshJobState.pending,
            ),
            mock.call(
                job_id=5,
                old_state=FeedRefreshJobState.in_progress,
                new_state=FeedRefreshJobState.failed,
            ),
        ]
    )

    job_repository.update.assert_has_calls(
        [
            mock.call(
                job_id=1,
                updates=FeedRefreshJobUpdates(
                    retries=0,
                ),
            ),
            mock.call(
                job_id=2,
                updates=FeedRefreshJobUpdates(
                    retries=0,
                ),
            ),
            # the job 3 is retried with a delay
            mock.call(
                job_id=3,
                updates=FeedRefreshJobUpdates(
                    retries=3,
                    # 8 minutes later, because of the retry delay for the 3rd retry
                    execute_after=datetime(2006, 1, 2, 15, 12, 5, 999999, tzinfo=UTC),
                ),
            ),
        ]
    )

    # because there are new posts for Feed 2, we also update its metadata
    feed_repository.update.assert_has_calls(
        [
            mock.call(
                feed_id=2,
                updates=FeedUpdates(
                    title="Also not bad RSS Feed",
                    published_at=datetime(2023, 9, 9, 9, 9, 9, 999999, tzinfo=UTC),
                ),
            ),
        ]
    )

    post_repository.create_many.assert_called_once_with(
        [
            NewFeedPost(
                feed_id=2,
                title="Can you believe it?",
                summary="I can't",
                url="http://example.com/feed2/1",
                guid="http://example.com/feed2/1",
                published_at=datetime(2023, 8, 8, 8, 8, 8, 999999, tzinfo=UTC),
            ),
            NewFeedPost(
                feed_id=2,
                title="How about that?",
                summary=None,
                url="http://example.com/feed2/2",
                guid="http://example.com/feed2/2",
                published_at=datetime(2023, 9, 9, 9, 9, 9, 999999, tzinfo=UTC),
            ),
        ]
    )
