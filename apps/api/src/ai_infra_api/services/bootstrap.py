import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings
from ai_infra_api.core.security import hash_password
from ai_infra_api.db.models import User, UserRole

logger = logging.getLogger(__name__)


async def bootstrap_admin(session: AsyncSession, settings: Settings) -> bool:
    password = settings.bootstrap_admin_password
    if password is None:
        logger.info("admin bootstrap skipped", extra={"event": "auth.bootstrap.skipped"})
        return False

    existing = await session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )
    if existing is not None:
        logger.info("admin already exists", extra={"event": "auth.bootstrap.exists"})
        return False

    session.add(
        User(
            username=settings.bootstrap_admin_username,
            password_hash=hash_password(password.get_secret_value()),
            role=UserRole.ADMIN,
            is_active=True,
        )
    )
    await session.commit()
    logger.info("admin created", extra={"event": "auth.bootstrap.created"})
    return True
