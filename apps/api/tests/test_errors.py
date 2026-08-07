from fastapi import FastAPI
from httpx import AsyncClient


async def test_unexpected_error_is_sanitized(client: AsyncClient, app: FastAPI) -> None:
    @app.get("/_test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("sensitive internal detail")

    response = await client.get("/_test/unexpected", headers={"x-request-id": "unexpected-request"})

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "request_id": "unexpected-request",
        "details": None,
    }
    assert "sensitive internal detail" not in response.text
