from fastapi import APIRouter, Depends

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.fastapi.depends.di import get_container
from awesome_rss_reader.fastapi.misc.schemas import ApiToken, ApiTokenType

router = APIRouter()


@router.post(
    "/token",
    summary="Generate an authentication token for testing purposes.",
    response_model=ApiToken,
)
async def login_for_access_token(
    container: Container = Depends(get_container),
) -> ApiToken:
    uc = container.use_cases.authenticate_user()

    uc_result = await uc.execute()

    return ApiToken(
        access_token=uc_result.token,
        token_type=ApiTokenType.bearer,
    )
