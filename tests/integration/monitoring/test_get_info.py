from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.application.settings import ApplicationSettings


async def test_get_info(
    container: Container,
    api_client: TestClient,
    postgres_database: AsyncEngine,
) -> None:
    app_config = ApplicationSettings(
        release_ver="0.1.0",
        release_commit="8de00b9",
    )
    with container.settings.app.override(app_config):
        response = api_client.get("/info", follow_redirects=False)

    assert response.status_code == 200

    response_json = response.json()
    assert response_json == {
        "version": "0.1.0",
        "commit": "8de00b9",
    }


def test_get_no_info(
    api_client: TestClient,
    postgres_database: AsyncEngine,
) -> None:
    response = api_client.get("/info", follow_redirects=False)
    assert response.status_code == 200

    response_json = response.json()
    assert response_json == {
        "version": "unknown",
        "commit": "unknown",
    }
