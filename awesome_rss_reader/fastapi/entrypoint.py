import structlog
from fastapi import FastAPI

from awesome_rss_reader.application import di
from awesome_rss_reader.application.di import Container
from awesome_rss_reader.fastapi.api.router import router as api_router
from awesome_rss_reader.fastapi.misc.router import router as misc_router


def init(container: Container) -> FastAPI:
    app_settings = container.settings.app()

    app = FastAPI(title=app_settings.name, version=app_settings.release_ver)
    app.include_router(misc_router)
    app.include_router(api_router, prefix="/api")

    app.state.container = container
    app.state.logger = structlog.getLogger()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await container.database.engine().dispose()

    return app


def get_asgi_app() -> FastAPI:
    container = di.init()
    return init(container)
