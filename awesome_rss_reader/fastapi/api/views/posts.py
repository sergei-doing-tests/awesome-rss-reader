from fastapi import APIRouter, Depends, Query

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.list_feed_posts import ListFeedPostsInput
from awesome_rss_reader.fastapi.api.schemas import (
    ApiFeedPost,
    ApiPostFollowStatus,
    ApiPostReadStatus,
)
from awesome_rss_reader.fastapi.depends.auth import get_current_user
from awesome_rss_reader.fastapi.depends.di import get_container

router = APIRouter(tags=["posts"])


@router.get(
    "/posts",
    summary="List feed posts",
    response_model=list[ApiFeedPost],
)
async def list_posts(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    offset: int = 0,
    limit: int = 100,
    read_status: ApiPostReadStatus = Query(None),
    follow_status: ApiPostFollowStatus = Query(None),
    feed_id: int = Query(None),
) -> list[ApiFeedPost]:
    uc = container.use_cases.list_feed_posts()

    read_by = None
    not_read_by = None
    match read_status:
        case ApiPostReadStatus.read:
            read_by = user.uid
        case ApiPostReadStatus.unread:
            not_read_by = user.uid

    followed_by = None
    not_followed_by = None
    match follow_status:
        case ApiPostFollowStatus.following:
            followed_by = user.uid
        case ApiPostFollowStatus.not_following:
            not_followed_by = user.uid

    uc_input = ListFeedPostsInput(
        followed_by=followed_by,
        not_followed_by=not_followed_by,
        read_by=read_by,
        not_read_by=not_read_by,
        feed_id=feed_id,
        offset=offset,
        limit=limit,
    )
    uc_result = await uc.execute(uc_input)

    return [ApiFeedPost.model_validate(post) for post in uc_result.posts]
