from typing import Any

import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from .types import FetchManyFixtureT, FetchOneFixtureT, InsertManyFixtureT, InsertOneFixtureT


@pytest_asyncio.fixture()
async def fetchone(db: AsyncEngine) -> FetchOneFixtureT:
    async def fetcher(query: sa.Select) -> dict[str, Any]:
        async with db.connect() as conn:
            result = await conn.execute(query)
            return dict(result.mappings().one())

    return fetcher


@pytest_asyncio.fixture()
async def fetchmany(db: AsyncEngine) -> FetchManyFixtureT:
    async def fetcher(query: sa.Select) -> list[dict[str, Any]]:
        async with db.connect() as conn:
            result = await conn.execute(query)
            return [dict(row) for row in result.mappings().fetchall()]

    return fetcher


@pytest_asyncio.fixture()
async def insert_one(db: AsyncEngine) -> InsertOneFixtureT:
    async def inserter(query: sa.Insert) -> dict[str, Any]:
        async with db.begin() as conn:
            result = await conn.execute(query)
            return dict(result.mappings().one())

    return inserter


@pytest_asyncio.fixture()
async def insert_many(db: AsyncEngine) -> InsertManyFixtureT:
    async def inserter(query: sa.Insert) -> list[dict[str, Any]]:
        async with db.begin() as conn:
            result = await conn.execute(query)
            return [dict(row) for row in result.mappings().fetchall()]

    return inserter
