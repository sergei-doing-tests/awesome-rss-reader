from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from awesome_rss_reader.core.repository.atomic import AtomicProvider
from awesome_rss_reader.data.postgres.repositories.base import BasePostgresRepository


class PostgresAtomicProvider(BasePostgresRepository, AtomicProvider):
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        async with self.db.begin():
            yield
