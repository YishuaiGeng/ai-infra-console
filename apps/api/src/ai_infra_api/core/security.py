import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from ai_infra_api.core.config import Settings
from ai_infra_api.core.errors import AppError
from ai_infra_api.db.models import User, UserRole

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(user: User, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.access_token_minutes * 60
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError(
            status_code=401,
            code="invalid_token",
            message="The access token is invalid or expired.",
        ) from exc


def ensure_admin(user: User) -> User:
    if user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="insufficient_permissions",
            message="Administrator access is required.",
        )
    return user
