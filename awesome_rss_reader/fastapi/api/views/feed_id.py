from fastapi import APIRouter, Depends, HTTPException, Path, status
from structlog.stdlib import BoundLogger

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase import follow_feed, refresh_feed, unfollow_feed
from awesome_rss_reader.fastapi.depends.auth import get_current_user
from awesome_rss_reader.fastapi.depends.di import get_container
from awesome_rss_reader.fastapi.depends.logging import get_logger

router = APIRouter(tags=["feed details"])


@router.put(
    "/feeds/{feed_id}/follow",
    summary="Follow a feed by its id",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Feed not found",
        },
    },
)
async def follow_feed_by_id(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    feed_id: int = Path(title="ID of the feed to follow"),
) -> None:
    uc = container.use_cases.follow_feed()

    uc_input = follow_feed.FollowFeedInput(feed_id=feed_id, user_uid=user.uid)

    try:
        await uc.execute(uc_input)
    except follow_feed.FeedNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found",
        )

    logger.info("Subscribed user to feed", feed_id=feed_id, user_uid=user.uid)


@router.delete(
    "/feeds/{feed_id}/unfollow",
    summary="Unfollow a feed by its id",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Feed not found",
        },
    },
)
async def unfollow_feed_by_id(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    feed_id: int = Path(title="ID of the feed to unfollow"),
) -> None:
    uc = container.use_cases.unfollow_feed()
    uc_input = unfollow_feed.UnfollowFeedInput(feed_id=feed_id, user_uid=user.uid)

    try:
        await uc.execute(uc_input)
    except unfollow_feed.FeedNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found",
        )

    logger.info("Unsubscribed user from feed", feed_id=feed_id, user_uid=user.uid)


@router.post(
    "/feeds/{feed_id}/refresh",
    summary="Force refresh a feed by its id",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Feed not found",
        },
    },
)
async def refresh_feed_by_id(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    feed_id: int = Path(title="ID of the feed to refresh"),
) -> None:
    uc = container.use_cases.refresh_feed()
    uc_input = refresh_feed.RefreshFeedInput(feed_id=feed_id)

    try:
        await uc.execute(uc_input)
    except refresh_feed.FeedNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found",
        )

    logger.info("Feed refresh requested by user", feed_id=feed_id, user_uid=user.uid)
