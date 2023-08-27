from collections.abc import Callable

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from tests.factories.user import UserFactory


@pytest.fixture()
def user() -> User:
    return UserFactory.build()


@pytest.fixture()
def user_api_client(
    user: User, api_client_factory: Callable[[User | None], TestClient]
) -> TestClient:
    return api_client_factory(user)
