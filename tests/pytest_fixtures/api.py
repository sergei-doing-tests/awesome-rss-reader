from collections.abc import Callable

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.fastapi.depends.auth import get_current_user
from tests.factories import UserFactory


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


@pytest.fixture()
def user() -> User:
    return UserFactory.build()


@pytest.fixture()
def user_api_client(
    user: User, api_client_factory: Callable[[User | None], TestClient]
) -> TestClient:
    return api_client_factory(user)
