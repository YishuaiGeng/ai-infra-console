from datetime import UTC, datetime, timedelta

import jwt
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from ai_infra_api.core.security import hash_password
from ai_infra_api.db.models import AuditLog, User, UserRole


async def create_user(
    app: FastAPI,
    *,
    username: str = "admin",
    password: str = "correct-password",
    active: bool = True,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=active,
    )
    async with app.state.database.session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def test_login_and_current_user(client: AsyncClient, app: FastAPI) -> None:
    user = await create_user(app)

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )
    token = login.json()["access_token"]
    current = await client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {token}"})

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert current.status_code == 200
    assert current.json()["id"] == str(user.id)
    assert current.json()["role"] == "admin"

    async with app.state.database.session_factory() as session:
        audit = await session.scalar(select(AuditLog).where(AuditLog.action == "auth.login"))
        assert audit is not None
        assert audit.success is True


async def test_invalid_credentials_use_error_envelope(client: AsyncClient, app: FastAPI) -> None:
    await create_user(app)

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
        headers={"x-request-id": "login-failure"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "invalid_credentials",
        "message": "The username or password is incorrect.",
        "request_id": "login-failure",
        "details": None,
    }


async def test_unknown_user_still_returns_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_disabled_user_cannot_login(client: AsyncClient, app: FastAPI) -> None:
    await create_user(app, active=False)

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_disabled"


async def test_authentication_required(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


async def test_invalid_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_expired_token_is_rejected(client: AsyncClient, app: FastAPI) -> None:
    user = await create_user(app)
    settings = app.state.settings
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_validation_error_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={}, headers={"x-request-id": "validation-request"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["request_id"] == "validation-request"
    assert len(response.json()["error"]["details"]) == 2
