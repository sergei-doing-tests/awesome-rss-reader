from fastapi import APIRouter, Depends, HTTPException, Path, status
from structlog.stdlib import BoundLogger

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase import read_post, unread_post
from awesome_rss_reader.fastapi.depends.auth import get_current_user
from awesome_rss_reader.fastapi.depends.di import get_container
from awesome_rss_reader.fastapi.depends.logging import get_logger

router = APIRouter(tags=["post details"])


@router.put(
    "/posts/{post_id}/read",
    summary="Mark post read by its id",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Post not found",
        },
    },
)
async def mark_post_read_by_id(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    post_id: int = Path(title="ID of the post to mark read"),
) -> None:
    uc = container.use_cases.read_post()

    uc_input = read_post.ReadPostInput(post_id=post_id, user_uid=user.uid)

    try:
        await uc.execute(uc_input)
    except read_post.PostNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    logger.info("Marked post read", post_id=post_id, user_uid=user.uid)


@router.delete(
    "/posts/{post_id}/unread",
    summary="Mark post unread by its id",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Post not found",
        },
    },
)
async def mark_post_unread_by_id(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    post_id: int = Path(title="ID of the post to mark unread"),
) -> None:
    uc = container.use_cases.unread_post()

    uc_input = unread_post.UnreadPostInput(post_id=post_id, user_uid=user.uid)

    try:
        await uc.execute(uc_input)
    except unread_post.PostNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    logger.info("Marked post unread", post_id=post_id, user_uid=user.uid)
