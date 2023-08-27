from collections.abc import Awaitable, Callable
from typing import Any

import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest_asyncio.fixture()
async def fetchone(db: AsyncEngine) -> Callable[[sa.Select], Awaitable[dict[str, Any] | None]]:
    async def fetcher(query: sa.Select) -> dict[str, Any] | None:
        async with db.connect() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return dict(row)
            return None

    return fetcher


@pytest_asyncio.fixture()
async def fetchmany(db: AsyncEngine) -> Callable[[sa.Select], Awaitable[list[dict[str, Any]]]]:
    async def fetcher(query: sa.Select) -> list[dict[str, Any]]:
        async with db.connect() as conn:
            result = await conn.execute(query)
            return [dict(row) for row in result.mappings().fetchall()]

    return fetcher


@pytest_asyncio.fixture()
async def insert_one(db: AsyncEngine) -> Callable[[sa.Insert], Awaitable[dict[str, Any] | None]]:
    async def inserter(query: sa.Insert) -> dict[str, Any] | None:
        async with db.begin() as conn:
            result = await conn.execute(query)
            if row := result.mappings().fetchone():
                return dict(row)
            return None

    return inserter


@pytest_asyncio.fixture()
async def insert_many(db: AsyncEngine) -> Callable[[sa.Insert], Awaitable[list[dict[str, Any]]]]:
    async def inserter(query: sa.Insert) -> list[dict[str, Any]]:
        async with db.begin() as conn:
            result = await conn.execute(query)
            return [dict(row) for row in result.mappings().fetchall()]

    return inserter
