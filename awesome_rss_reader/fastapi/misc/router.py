from fastapi import APIRouter

from .views import info, redirects, token

router = APIRouter(tags=["misc"])

router.include_router(info.router)
router.include_router(token.router)
router.include_router(redirects.router, include_in_schema=False)
