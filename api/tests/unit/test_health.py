"""Contract tests for the public health endpoint and the problem+json error shape."""

from httpx import AsyncClient

from app import SERVICE_NAME, __version__

HEALTH_URL = "/api/v1/health"


async def test_health_returns_ok_payload(client: AsyncClient) -> None:
    response = await client.get(HEALTH_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == SERVICE_NAME
    assert body["version"] == __version__
    assert body["env"] == "ci"
    assert body["timestamp"].endswith("+00:00") or body["timestamp"].endswith("Z")


async def test_health_requires_no_api_key(client: AsyncClient) -> None:
    response = await client.get(HEALTH_URL)

    assert response.status_code == 200


async def test_health_echoes_client_request_id(client: AsyncClient) -> None:
    response = await client.get(HEALTH_URL, headers={"X-Request-ID": "corr-123"})

    assert response.headers["X-Request-ID"] == "corr-123"
    assert response.json()["requestId"] == "corr-123"


async def test_health_generates_request_id_when_missing(client: AsyncClient) -> None:
    response = await client.get(HEALTH_URL)

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert response.json()["requestId"] == request_id


async def test_unknown_route_returns_problem_json(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["code"] == "NOT_FOUND"
    assert body["status"] == 404
    assert body["requestId"]
