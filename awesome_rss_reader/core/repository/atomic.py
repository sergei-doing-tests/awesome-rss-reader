from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class AtomicProvider(ABC):
    @abstractmethod
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield None
