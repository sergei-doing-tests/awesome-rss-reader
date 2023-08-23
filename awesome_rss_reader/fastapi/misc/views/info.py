from fastapi import APIRouter, Depends

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.fastapi.depends.di import get_container
from awesome_rss_reader.fastapi.misc.schemas import ApiReleaseStats

router = APIRouter()


@router.get(
    "/info",
    summary="Get release info",
    response_model=ApiReleaseStats,
)
async def get_info(
    container: Container = Depends(get_container),
) -> ApiReleaseStats:
    app_settings = container.settings.app()
    return ApiReleaseStats(
        version=app_settings.release_ver,
        commit=app_settings.release_commit,
    )
