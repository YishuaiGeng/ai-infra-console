import logging
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings, get_settings
from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.core.security import decode_access_token, digest_agent_token, ensure_admin
from ai_infra_api.db.models import ServerAgent, User
from ai_infra_api.db.session import get_db
from ai_infra_api.services.audit import record_audit

logger = logging.getLogger(__name__)

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


async def get_admin_user(user: CurrentUser) -> User:
    return ensure_admin(user)


async def get_current_agent(
    request: Request,
    session: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> ServerAgent:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=401,
            code="agent_authentication_required",
            message="An Agent bearer token is required.",
        )

    token_hash = digest_agent_token(credentials.credentials)
    agent = await session.scalar(select(ServerAgent).where(ServerAgent.token_hash == token_hash))
    if agent is None or agent.revoked_at is not None:
        if agent is None:
            logger.warning(
                "unknown Agent token rejected",
                extra={"event": "agent.authentication.rejected"},
            )
        else:
            await record_audit(
                session,
                action="agent.authentication.rejected",
                success=False,
                request_id=request_id_from(request),
                resource_type="server",
                resource_id=str(agent.server_id),
                details={"reason": "revoked"},
            )
        raise AppError(
            status_code=401,
            code="invalid_agent_token",
            message="The Agent token is invalid or revoked.",
        )
    return agent


AdminUser = Annotated[User, Depends(get_admin_user)]
CurrentAgent = Annotated[ServerAgent, Depends(get_current_agent)]
