from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.application.settings import ApplicationSettings


@pytest.fixture()
def _test_app_version(container: Container) -> Iterator[None]:
    app_settings = ApplicationSettings(
        release_ver="0.1.0",
        release_commit="8de00b9",
        **container.settings.app().model_dump(exclude={"release_ver", "release_commit"}),
    )
    with container.settings.app.override(app_settings):
        yield


@pytest.mark.usefixtures("_test_app_version")
async def test_get_info(api_client: TestClient) -> None:
    response = api_client.get("/info", follow_redirects=False)

    assert response.status_code == 200

    response_json = response.json()
    assert response_json == {
        "version": "0.1.0",
        "commit": "8de00b9",
    }


def test_get_no_info(api_client: TestClient) -> None:
    response = api_client.get("/info", follow_redirects=False)
    assert response.status_code == 200

    response_json = response.json()
    assert response_json == {
        "version": "development",
        "commit": "unknown",
    }
