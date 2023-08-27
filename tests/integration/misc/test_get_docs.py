from starlette.testclient import TestClient


def test_main_redirects_to_docs(api_client: TestClient) -> None:
    response = api_client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_get_docs(api_client: TestClient) -> None:
    response = api_client.get("/docs", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "SwaggerUIBundle" in response.text


def test_get_openapi_schema(api_client: TestClient) -> None:
    response = api_client.get("/openapi.json", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    response_json = response.json()
    assert response_json["info"]["title"] == "Awesome RSS Reader"
    assert response_json["info"]["version"] == "development"
