from fastapi import APIRouter, Request

from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.dependencies import AdminUser, CurrentUser, DatabaseSession
from ai_infra_api.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.settings import get_system_settings, update_system_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SystemSettingsResponse)
async def read_settings(
    session: DatabaseSession,
    _user: CurrentUser,
) -> SystemSettingsResponse:
    return await get_system_settings(session)


@router.put("", response_model=SystemSettingsResponse)
async def save_settings(
    payload: SystemSettingsUpdate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> SystemSettingsResponse:
    result = await update_system_settings(session, payload)
    await record_audit(
        session,
        action="settings.updated",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="system_settings",
        resource_id="console",
        details={"keys": sorted(payload.model_dump().keys())},
    )
    return result
