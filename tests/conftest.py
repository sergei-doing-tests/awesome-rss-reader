import asyncio
from collections.abc import Callable, Iterator

import pytest
import pytest_asyncio
import structlog
from fastapi import FastAPI
from sqlalchemy import URL, NullPool, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy_utils import create_database, database_exists, drop_database
from starlette.testclient import TestClient

from awesome_rss_reader.application import di
from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.data.postgres.database import PostgresSettings
from awesome_rss_reader.data.postgres.models import metadata
from awesome_rss_reader.fastapi import entrypoint as api_entrypoint
from awesome_rss_reader.fastapi.depends.auth import get_current_user

logger = structlog.get_logger()

pytest_plugins = [
    "tests.pytest_fixtures.api",
    "tests.pytest_fixtures.data",
    "tests.pytest_fixtures.db",
]


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest.fixture(scope="session")
def db_settings() -> PostgresSettings:
    return PostgresSettings()


@pytest.fixture(scope="session")
def db_dsn(db_settings: PostgresSettings) -> URL:
    actual_dsn = make_url(str(db_settings.dsn))
    return actual_dsn.set(database=f"{actual_dsn.database}_test")


@pytest.fixture(scope="session")
def _setup_db(db_dsn: URL) -> None:
    sync_dsn = db_dsn.set(drivername="postgresql+psycopg")

    if database_exists(sync_dsn):
        logger.info("dropping test database", dsn=sync_dsn)
        drop_database(sync_dsn)

    logger.info("creating test database", dsn=sync_dsn)
    create_database(sync_dsn)

    yield

    logger.info("dropping test database", dsn=sync_dsn)
    drop_database(sync_dsn)


@pytest_asyncio.fixture(scope="session")
async def db_engine(_setup_db: None, db_dsn: URL) -> Iterator[AsyncEngine]:
    engine = create_async_engine(db_dsn, poolclass=NullPool)

    async with engine.begin() as conn:
        logger.info("creating tables in the test database", dsn=db_dsn)
        await conn.run_sync(metadata.create_all, checkfirst=False)

    yield engine

    async with engine.begin() as conn:
        logger.info("dropping tables in the test database", dsn=db_dsn)
        await conn.run_sync(metadata.drop_all, checkfirst=False)

    logger.info("closing connections to the test database", dsn=db_dsn)
    await engine.dispose()


@pytest.fixture()
def clear_db(db_engine: AsyncEngine) -> Callable:
    async def clearer() -> None:
        async with db_engine.begin() as conn:
            for table in reversed(metadata.sorted_tables):
                await conn.execute(table.delete())

    return clearer


@pytest_asyncio.fixture()
async def db(db_engine: AsyncEngine, clear_db: Callable) -> Iterator[AsyncEngine]:
    async with db_engine.connect():
        yield db_engine
        await clear_db()


@pytest.fixture(scope="session")
def container() -> Container:
    return di.init()


@pytest.fixture()
def postgres_database(container: Container, db: AsyncEngine) -> Iterator[AsyncEngine]:
    with container.database.engine.override(db):
        yield db


@pytest.fixture()
def fastapi_app(container: Container) -> FastAPI:
    app = api_entrypoint.init(container)
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def api_client(fastapi_app: FastAPI) -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture()
def api_client_factory(fastapi_app: FastAPI) -> Callable[[User | None], TestClient]:
    def factory(user: User | None = None) -> TestClient:
        async def auth_user() -> User | None:
            return user

        if user is not None:
            fastapi_app.dependency_overrides[get_current_user] = auth_user

        return TestClient(fastapi_app)

    return factory
