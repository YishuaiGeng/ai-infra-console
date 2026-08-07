from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import func, select

from ai_infra_api.core.config import Settings
from ai_infra_api.core.security import verify_password
from ai_infra_api.db.models import User, UserRole
from ai_infra_api.services.bootstrap import bootstrap_admin


async def test_bootstrap_creates_admin_once(app: FastAPI) -> None:
    settings = Settings(
        environment="test",
        database_url=app.state.settings.database_url,
        jwt_secret=app.state.settings.jwt_secret,
        bootstrap_admin_username="maintainer",
        bootstrap_admin_password=SecretStr("bootstrap-password"),
    )

    async with app.state.database.session_factory() as session:
        assert await bootstrap_admin(session, settings) is True
        assert await bootstrap_admin(session, settings) is False
        count = await session.scalar(select(func.count()).select_from(User))
        user = await session.scalar(select(User).where(User.username == "maintainer"))

    assert count == 1
    assert user is not None
    assert user.role == UserRole.ADMIN
    assert verify_password("bootstrap-password", user.password_hash)
