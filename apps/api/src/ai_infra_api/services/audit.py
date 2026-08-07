import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import AuditLog


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
