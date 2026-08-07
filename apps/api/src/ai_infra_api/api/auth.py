from datetime import UTC, datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Request
from sqlalchemy import select

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.core.security import create_access_token, hash_password, verify_password
from ai_infra_api.db.models import User
from ai_infra_api.dependencies import CurrentUser, DatabaseSession
from ai_infra_api.schemas.auth import LoginRequest, TokenResponse, UserResponse
from ai_infra_api.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["authentication"])
DUMMY_PASSWORD_HASH = hash_password(token_urlsafe(32))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: DatabaseSession,
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.username == payload.username))
    request_id = request_id_from(request)
    client_ip = request.client.host if request.client else None

    encoded_password = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, encoded_password)
    if user is None or not password_valid:
        await record_audit(
            session,
            action="auth.login",
            success=False,
            request_id=request_id,
            ip_address=client_ip,
            details={"username": payload.username},
        )
        raise AppError(
            status_code=401,
            code="invalid_credentials",
            message="The username or password is incorrect.",
        )

    if not user.is_active:
        await record_audit(
            session,
            action="auth.login",
            success=False,
            request_id=request_id,
            actor_user_id=user.id,
            ip_address=client_ip,
            details={"reason": "disabled"},
        )
        raise AppError(
            status_code=403,
            code="user_disabled",
            message="This user is disabled.",
        )

    user.last_login_at = datetime.now(UTC)
    token, expires_in = create_access_token(user, request.app.state.settings)
    await record_audit(
        session,
        action="auth.login",
        success=True,
        request_id=request_id,
        actor_user_id=user.id,
        ip_address=client_ip,
    )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
async def current_user(user: CurrentUser) -> User:
    return user
