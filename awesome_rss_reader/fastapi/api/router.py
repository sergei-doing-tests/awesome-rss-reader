from fastapi import APIRouter

from .views import feed_id, feeds

router = APIRouter()

router.include_router(feeds.router)
router.include_router(feed_id.router)
