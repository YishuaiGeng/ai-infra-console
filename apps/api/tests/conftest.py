import base64
from collections.abc import AsyncIterator
from pathlib import Path

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from ai_infra_api.core.config import Settings
from ai_infra_api.db.base import Base
from ai_infra_api.main import create_app


@pytest.fixture
async def app(tmp_path: Path) -> AsyncIterator[FastAPI]:
    database_path = tmp_path / "test.db"
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        redis_url="redis://unused/0",
        jwt_secret=SecretStr("test-secret-that-is-long-enough-for-tests"),
        credential_encryption_key=SecretStr(base64.b64encode(b"k" * 32).decode()),
        bootstrap_admin_password=None,
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        await application.state.redis.aclose()
        application.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        async with application.state.database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
