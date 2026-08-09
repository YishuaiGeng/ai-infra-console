from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import SystemSetting
from ai_infra_api.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate

SETTINGS_KEY = "console"

DEFAULT_SETTINGS = SystemSettingsResponse(
    console_name="AI Infra Console",
    timezone="Asia/Shanghai",
    language="English",
    heartbeat_interval=10,
    offline_threshold=30,
    metrics_retention_days=14,
    default_model_directory="/data/models",
    default_backend="vLLM",
    default_port=8000,
    default_gpu_memory_utilization=0.9,
    require_delete_confirmation=True,
    audit_log_retention_days=90,
)


async def get_system_settings(session: AsyncSession) -> SystemSettingsResponse:
    row = await session.get(SystemSetting, SETTINGS_KEY)
    if row is None or not isinstance(row.value, dict):
        return DEFAULT_SETTINGS
    return SystemSettingsResponse.model_validate(
        {**DEFAULT_SETTINGS.model_dump(), **row.value}
    )


async def update_system_settings(
    session: AsyncSession,
    payload: SystemSettingsUpdate,
) -> SystemSettingsResponse:
    value = payload.model_dump(mode="json")
    row = await session.get(SystemSetting, SETTINGS_KEY)
    if row is None:
        row = SystemSetting(key=SETTINGS_KEY, value=value, is_secret=False)
        session.add(row)
    else:
        row.value = value
        row.is_secret = False
    await session.commit()
    return payload
