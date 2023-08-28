from fastapi import APIRouter

from .views import feed_id, feeds, posts

router = APIRouter()

router.include_router(feeds.router)
router.include_router(feed_id.router)
router.include_router(posts.router)
