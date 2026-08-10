import asyncio
import uuid

from ai_infra_api.core.config import get_settings
from ai_infra_api.db.session import Database
from ai_infra_api.services.api_resources.catalog import get_account, sync_models


def sync_api_account_models(account_id: str, sync_run_id: str | None = None) -> dict[str, object]:
    return asyncio.run(_sync_models(uuid.UUID(account_id), sync_run_id))


def sync_api_account_balance(account_id: str, sync_run_id: str | None = None) -> dict[str, object]:
    return _unsupported(account_id, sync_run_id, "balance")


def sync_api_account_usage(
    account_id: str,
    sync_run_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, object]:
    return asyncio.run(_sync_usage(uuid.UUID(account_id), sync_run_id, period_start, period_end))


def validate_api_credential(
    credential_id: str, sync_run_id: str | None = None
) -> dict[str, object]:
    return _unsupported(credential_id, sync_run_id, "credential_validation")


def prune_api_resource_history() -> dict[str, object]:
    return {"status": "completed", "records_deleted": 0}


async def _sync_models(account_id: uuid.UUID, sync_run_id: str | None) -> dict[str, object]:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            account, provider = await get_account(session, account_id)
            run = await sync_models(session, account, provider, None, settings)
            return {
                "account_id": str(account_id),
                "sync_run_id": sync_run_id or str(run.id),
                "status": run.status,
                "records_written": run.records_written,
                "error_code": run.error_code,
            }
    finally:
        await database.close()


async def _sync_usage(
    account_id: uuid.UUID,
    sync_run_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> dict[str, object]:
    from ai_infra_api.services.api_resources.catalog import sync_usage

    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            account, provider = await get_account(session, account_id)
            run = await sync_usage(session, account, provider, None, settings)
            return {
                "account_id": str(account_id),
                "sync_run_id": sync_run_id or str(run.id),
                "requested_period_start": period_start,
                "requested_period_end": period_end,
                "status": run.status,
                "records_written": run.records_written,
                "error_code": run.error_code,
            }
    finally:
        await database.close()


def _unsupported(resource_id: str, sync_run_id: str | None, sync_type: str) -> dict[str, object]:
    return {
        "resource_id": resource_id,
        "sync_run_id": sync_run_id,
        "sync_type": sync_type,
        "status": "unsupported",
    }
