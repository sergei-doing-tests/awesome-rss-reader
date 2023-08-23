from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class PostgresSettings(BaseSettings):
    dsn: PostgresDsn = "postgresql+asyncpg://awesome-rss-reader:awesome-rss-reader@localhost:5432/awesome-rss-reader"  # type: ignore[assignment] # noqa: E501
    debug: bool = False
    pool_size: int = 5
    pool_recycle: int = 300
    pool_timeout: int = 10
    max_overflow: int = 5

    model_config = SettingsConfigDict(env_prefix="POSTGRES_DB_")


def init_async_engine(settings: PostgresSettings) -> AsyncEngine:
    return create_async_engine(
        str(settings.dsn),
        echo=settings.debug,
        pool_size=settings.pool_size,
        pool_recycle=settings.pool_recycle,
        pool_timeout=settings.pool_timeout,
        max_overflow=settings.max_overflow,
    )
