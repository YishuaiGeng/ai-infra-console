import uuid
from json import dumps

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import AuditLog, User
from ai_infra_api.schemas.activity import ActivityLogResponse

SENSITIVE_DETAIL_PARTS = ("token", "secret", "password", "authorization", "credential")


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    success: bool,
    request_id: str | None,
    actor_user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            request_id=request_id,
            ip_address=ip_address,
            details=details or {},
        )
    )
    await session.commit()


def _safe_details(details: dict[str, object]) -> str:
    safe = {
        key: value
        for key, value in details.items()
        if not any(part in key.lower() for part in SENSITIVE_DETAIL_PARTS)
    }
    if not safe:
        return "No additional details"
    return dumps(safe, ensure_ascii=False, sort_keys=True, default=str)[:1_024]


def _resource_label(log: AuditLog) -> str:
    if log.resource_type and log.resource_id:
        return f"{log.resource_type}:{log.resource_id}"
    if log.resource_type:
        return log.resource_type
    return log.resource_id or "system"


def _server_id(log: AuditLog) -> str | None:
    if log.resource_type == "server" and log.resource_id:
        return log.resource_id
    value = log.details.get("server_id") if isinstance(log.details, dict) else None
    return value if isinstance(value, str) else None


async def list_activity_logs(
    session: AsyncSession,
    *,
    limit: int = 200,
    search: str | None = None,
) -> list[ActivityLogResponse]:
    query = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if search:
        text = f"%{search.strip()}%"
        query = query.where(
            AuditLog.action.ilike(text)
            | AuditLog.resource_type.ilike(text)
            | AuditLog.resource_id.ilike(text)
            | User.username.ilike(text)
        )
    rows = (await session.execute(query)).all()
    return [
        ActivityLogResponse(
            id=log.id,
            time=log.created_at,
            user=username or "system",
            action=log.action,
            resource=_resource_label(log),
            server_id=_server_id(log),
            status="success" if log.success else "failed",
            detail=_safe_details(log.details if isinstance(log.details, dict) else {}),
        )
        for log, username in rows
    ]
