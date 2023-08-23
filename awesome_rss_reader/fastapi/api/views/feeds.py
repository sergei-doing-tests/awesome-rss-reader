from fastapi import APIRouter, Body, Depends, status

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.usecase.create_feed import CreateFeedInput
from awesome_rss_reader.fastapi.api.schemas import ApiCreateFeedBody, ApiFeed
from awesome_rss_reader.fastapi.depends.auth import get_current_user
from awesome_rss_reader.fastapi.depends.di import get_container

router = APIRouter(tags=["feeds"])


@router.post(
    "/feeds",
    summary="Subscribe to a feed by its URL",
    response_model=ApiFeed,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_feed(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
    body: ApiCreateFeedBody = Body(...),
) -> ApiFeed:
    uc = container.use_cases.create_feed()

    uc_input = CreateFeedInput(
        user_uid=user.uid,
        url=str(body.url),
    )
    uc_result = await uc.execute(uc_input)

    return ApiFeed.model_validate(uc_result.feed)
