import time
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from jose import jwt
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.application.settings import AuthSettings


@pytest.fixture()
def auth_settings(container: Container) -> Iterator[AuthSettings]:
    auth_settings = AuthSettings(
        secret_key=uuid4().hex,
        token_expiry_s=60,
    )
    with container.settings.auth.override(auth_settings):
        yield auth_settings


async def test_create_token(api_client: TestClient, auth_settings: AuthSettings) -> None:
    before = time.time()

    response = api_client.post("/token")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json.keys() == {"access_token", "token_type"}
    assert response_json["token_type"] == "bearer"

    jwt_token = response_json["access_token"]
    payload = jwt.decode(jwt_token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])

    # this is the user uid
    assert UUID(payload["sub"])

    assert payload["exp"] >= before
    assert payload["exp"] <= time.time() + auth_settings.token_expiry_s


async def test_create_multiple_tokens(api_client: TestClient, auth_settings: AuthSettings) -> None:
    # tokens and users from consecutive /token calls should be different
    jwt_tokens = set()
    user_uids = set()

    for _ in range(5):
        response = api_client.post("/token")
        response_json = response.json()

        token = response_json["access_token"]
        payload = jwt.decode(token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])

        jwt_tokens.add(token)
        user_uids.add(payload["sub"])

    assert len(jwt_tokens) == 5
    assert len(user_uids) == 5
