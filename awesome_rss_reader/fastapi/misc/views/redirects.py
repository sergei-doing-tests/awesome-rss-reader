from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter()


@router.get("/")
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse("/docs")
