from fastapi import FastAPI
from httpx import AsyncClient


class UnavailableRedis:
    async def ping(self) -> None:
        raise ConnectionError("test Redis outage")

    async def aclose(self) -> None:
        return None


async def test_liveness_generates_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert response.headers["x-request-id"]


async def test_request_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"x-request-id": "request-123"})

    assert response.headers["x-request-id"] == "request-123"


async def test_readiness_checks_database_and_redis(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "database": {"status": "ready", "detail": None},
            "redis": {"status": "ready", "detail": None},
        },
    }


async def test_readiness_returns_503_when_redis_is_unavailable(
    client: AsyncClient, app: FastAPI
) -> None:
    await app.state.redis.aclose()
    app.state.redis = UnavailableRedis()

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["redis"]["status"] == "unavailable"
