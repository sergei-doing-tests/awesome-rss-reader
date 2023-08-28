from fastapi import APIRouter

from .views import feed_id, feeds, post_id, posts

router = APIRouter()

router.include_router(feeds.router)
router.include_router(feed_id.router)
router.include_router(posts.router)
router.include_router(post_id.router)
