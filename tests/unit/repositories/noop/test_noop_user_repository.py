import uuid

import pytest

from awesome_rss_reader.data.noop.users import NoopUserRepository


@pytest.fixture()
def repo() -> NoopUserRepository:
    return NoopUserRepository()


async def test_create(repo: NoopUserRepository) -> None:
    user1, user2 = [await repo.create() for _ in range(2)]

    assert isinstance(user1.uid, uuid.UUID)
    assert isinstance(user2.uid, uuid.UUID)

    assert user1.uid != user2.uid
