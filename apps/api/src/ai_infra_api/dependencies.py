from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings, get_settings
from ai_infra_api.core.errors import AppError
from ai_infra_api.core.security import decode_access_token
from ai_infra_api.db.models import User
from ai_infra_api.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)

SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    session: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=401,
            code="authentication_required",
            message="A bearer access token is required.",
        )

    settings: Settings = request.app.state.settings
    user_id = decode_access_token(credentials.credentials, settings)
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise AppError(
            status_code=401,
            code="invalid_token",
            message="The access token does not belong to an active user.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
