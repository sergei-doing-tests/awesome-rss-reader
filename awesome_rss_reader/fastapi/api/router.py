from fastapi import APIRouter

from .views import feeds

router = APIRouter()

router.include_router(feeds.router)
