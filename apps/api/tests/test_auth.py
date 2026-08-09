from datetime import UTC, datetime, timedelta

import jwt
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import AuditLog, User, UserRole


async def create_user(
    app: FastAPI,
    *,
    username: str = "admin",
    password: str = "correct-password",
    role: UserRole = UserRole.ADMIN,
    active: bool = True,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
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
        session.add(
            AuditLog(
                actor_user_id=user.id,
                action="agent.token.created",
                resource_type="server",
                resource_id="server-1",
                success=True,
                details={"registration_token": "secret-token", "note": "safe"},
            )
        )
        await session.commit()
    activity = await client.get(
        "/api/v1/activity?search=agent.token.created",
        headers={"authorization": f"Bearer {token}"},
    )
    assert activity.status_code == 200
    assert activity.json()[0]["action"] == "agent.token.created"
    assert activity.json()[0]["user"] == "admin"
    assert activity.json()[0]["status"] == "success"
    assert "secret-token" not in activity.json()[0]["detail"]
    assert "safe" in activity.json()[0]["detail"]

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
    activity = await client.get("/api/v1/activity")
    assert activity.status_code == 401
    assert activity.json()["error"]["code"] == "authentication_required"


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


async def test_system_settings_are_persisted_and_role_protected(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    admin = await create_user(app, username="settings-admin")
    viewer = await create_user(
        app,
        username="settings-viewer",
        role=UserRole.VIEWER,
    )
    admin_token, _ = create_access_token(admin, app.state.settings)
    viewer_token, _ = create_access_token(viewer, app.state.settings)
    payload = {
        "console_name": "Personal GPU Console",
        "timezone": "Asia/Shanghai",
        "language": "English",
        "heartbeat_interval": 15,
        "offline_threshold": 45,
        "metrics_retention_days": 30,
        "default_model_directory": "/data/models",
        "default_backend": "vLLM",
        "default_port": 8001,
        "default_gpu_memory_utilization": 0.85,
        "require_delete_confirmation": True,
        "audit_log_retention_days": 120,
    }

    read_default = await client.get(
        "/api/v1/settings",
        headers={"authorization": f"Bearer {viewer_token}"},
    )
    forbidden = await client.put(
        "/api/v1/settings",
        headers={"authorization": f"Bearer {viewer_token}"},
        json=payload,
    )
    saved = await client.put(
        "/api/v1/settings",
        headers={"authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    read_saved = await client.get(
        "/api/v1/settings",
        headers={"authorization": f"Bearer {viewer_token}"},
    )

    assert read_default.status_code == 200
    assert read_default.json()["console_name"] == "AI Infra Console"
    assert forbidden.status_code == 403
    assert saved.status_code == 200
    assert saved.json()["console_name"] == "Personal GPU Console"
    assert read_saved.json()["metrics_retention_days"] == 30
    async with app.state.database.session_factory() as session:
        audit = await session.scalar(select(AuditLog).where(AuditLog.action == "settings.updated"))
        assert audit is not None
