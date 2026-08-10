import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.db.models import (
    ApiAccountModel,
    ApiBalanceSnapshot,
    ApiCredential,
    ApiSyncRun,
    ApiUsageSnapshot,
)
from ai_infra_api.dependencies import AdminUser, CurrentUser, DatabaseSession, SettingsDependency
from ai_infra_api.schemas.api_resources import (
    ApiAccountCreate,
    ApiAccountModelManual,
    ApiAccountModelResponse,
    ApiAccountResponse,
    ApiAccountUpdate,
    ApiBalanceManualCreate,
    ApiBalanceResponse,
    ApiCredentialCreate,
    ApiCredentialResponse,
    ApiCredentialRotate,
    ApiCredentialUpdate,
    ApiProviderCreate,
    ApiProviderResponse,
    ApiProviderUpdate,
    ApiSyncRequest,
    ApiSyncRunResponse,
    ApiUsageManualCreate,
    ApiUsageResponse,
    ApiUsageSummaryResponse,
)
from ai_infra_api.services.api_resources.catalog import (
    ApiResourceError,
    account_response,
    create_account,
    create_credential,
    create_manual_balance,
    create_manual_model,
    create_manual_usage,
    create_provider,
    get_account,
    get_credential,
    get_provider,
    list_accounts,
    list_providers,
    rotate_credential,
    sync_models,
    sync_usage,
    update_account,
    update_credential,
    update_provider,
    usage_summary,
    validate_credential,
)
from ai_infra_api.services.audit import record_audit

router = APIRouter(prefix="/api-resources", tags=["api-resources"])


def _error(error: ApiResourceError) -> AppError:
    return AppError(status_code=error.status_code, code=error.code, message=error.message)


async def _audit(
    session: DatabaseSession,
    request: Request,
    admin: AdminUser,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    details: dict[str, object] | None = None,
) -> None:
    await record_audit(
        session,
        action=action,
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
    )


@router.get("/providers", response_model=list[ApiProviderResponse])
async def provider_list(session: DatabaseSession, _user: CurrentUser) -> list[ApiProviderResponse]:
    providers = await list_providers(session)
    await session.commit()
    return [ApiProviderResponse.model_validate(provider) for provider in providers]


@router.get("/providers/{provider_slug}", response_model=ApiProviderResponse)
async def provider_detail(
    provider_slug: str, session: DatabaseSession, _user: CurrentUser
) -> ApiProviderResponse:
    try:
        provider = await get_provider(session, provider_slug)
        await session.commit()
        return ApiProviderResponse.model_validate(provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/providers", response_model=ApiProviderResponse, status_code=201)
async def provider_create(
    payload: ApiProviderCreate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiProviderResponse:
    try:
        provider = await create_provider(session, payload)
        await _audit(
            session, request, admin, "api_resource.provider.created", "api_provider", provider.id
        )
        return ApiProviderResponse.model_validate(provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.patch("/providers/{provider_slug}", response_model=ApiProviderResponse)
async def provider_patch(
    provider_slug: str,
    payload: ApiProviderUpdate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiProviderResponse:
    try:
        provider = await get_provider(session, provider_slug)
        provider = await update_provider(session, provider, payload)
        await _audit(
            session, request, admin, "api_resource.provider.updated", "api_provider", provider.id
        )
        return ApiProviderResponse.model_validate(provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts", response_model=list[ApiAccountResponse])
async def account_list(
    session: DatabaseSession,
    _user: CurrentUser,
    provider: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    owner: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> list[ApiAccountResponse]:
    return await list_accounts(
        session,
        provider=provider,
        status=status,
        tag=tag,
        owner=owner,
        search=search,
        include_archived=include_archived,
    )


@router.post("/accounts", response_model=ApiAccountResponse, status_code=201)
async def account_create(
    payload: ApiAccountCreate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiAccountResponse:
    try:
        account = await create_account(session, payload, admin, settings)
        _, provider = await get_account(session, account.id)
        await _audit(
            session,
            request,
            admin,
            "api_resource.account.created",
            "api_account",
            account.id,
            {"provider": provider.slug},
        )
        return await account_response(session, account, provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts/{account_id}", response_model=ApiAccountResponse)
async def account_detail(
    account_id: uuid.UUID, session: DatabaseSession, _user: CurrentUser
) -> ApiAccountResponse:
    try:
        account, provider = await get_account(session, account_id)
        return await account_response(session, account, provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.patch("/accounts/{account_id}", response_model=ApiAccountResponse)
async def account_patch(
    account_id: uuid.UUID,
    payload: ApiAccountUpdate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiAccountResponse:
    try:
        account, provider = await get_account(session, account_id)
        await update_account(session, account, payload, settings)
        await _audit(
            session, request, admin, "api_resource.account.updated", "api_account", account.id
        )
        return await account_response(session, account, provider)
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/accounts/{account_id}/archive", response_model=ApiAccountResponse)
async def account_archive(
    account_id: uuid.UUID, request: Request, session: DatabaseSession, admin: AdminUser
) -> ApiAccountResponse:
    return await _set_archive(account_id, True, request, session, admin)


@router.post("/accounts/{account_id}/restore", response_model=ApiAccountResponse)
async def account_restore(
    account_id: uuid.UUID, request: Request, session: DatabaseSession, admin: AdminUser
) -> ApiAccountResponse:
    return await _set_archive(account_id, False, request, session, admin)


async def _set_archive(
    account_id: uuid.UUID,
    archived: bool,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiAccountResponse:
    try:
        account, provider = await get_account(session, account_id)
        account.status = "archived" if archived else "unverified"
        await session.commit()
        await session.refresh(account)
        response = await account_response(session, account, provider)
        action = "api_resource.account.archived" if archived else "api_resource.account.restored"
        await _audit(session, request, admin, action, "api_account", account.id)
        return response
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts/{account_id}/credentials", response_model=list[ApiCredentialResponse])
async def credential_list(
    account_id: uuid.UUID, session: DatabaseSession, _user: CurrentUser
) -> list[ApiCredential]:
    try:
        await get_account(session, account_id)
    except ApiResourceError as error:
        raise _error(error) from error
    return list(
        (
            await session.scalars(
                select(ApiCredential)
                .where(ApiCredential.account_id == account_id)
                .order_by(ApiCredential.created_at.desc())
            )
        ).all()
    )


@router.post(
    "/accounts/{account_id}/credentials", response_model=ApiCredentialResponse, status_code=201
)
async def credential_create(
    account_id: uuid.UUID,
    payload: ApiCredentialCreate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiCredential:
    try:
        account, _ = await get_account(session, account_id)
        credential = await create_credential(session, account, payload, admin, settings)
        await session.commit()
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.created",
            "api_credential",
            credential.id,
            {"account_id": str(account.id), "masked_value": credential.masked_value},
        )
        return credential
    except ApiResourceError as error:
        raise _error(error) from error


@router.patch("/credentials/{credential_id}", response_model=ApiCredentialResponse)
async def credential_patch(
    credential_id: uuid.UUID,
    payload: ApiCredentialUpdate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiCredential:
    try:
        credential = await get_credential(session, credential_id)
        await update_credential(session, credential, payload)
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.updated",
            "api_credential",
            credential.id,
        )
        return credential
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/credentials/{credential_id}/rotate", response_model=ApiCredentialResponse)
async def credential_rotate(
    credential_id: uuid.UUID,
    payload: ApiCredentialRotate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiCredential:
    try:
        credential = await get_credential(session, credential_id)
        await rotate_credential(session, credential, payload, settings)
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.rotated",
            "api_credential",
            credential.id,
        )
        return credential
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/credentials/{credential_id}/validate", response_model=ApiCredentialResponse)
async def credential_validate(
    credential_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiCredential:
    try:
        credential = await get_credential(session, credential_id)
        await validate_credential(session, credential, settings)
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.validated",
            "api_credential",
            credential.id,
            {"result": credential.status, "error_code": credential.last_error_code or "none"},
        )
        return credential
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/credentials/{credential_id}/disable", response_model=ApiCredentialResponse)
async def credential_disable(
    credential_id: uuid.UUID, request: Request, session: DatabaseSession, admin: AdminUser
) -> ApiCredential:
    try:
        credential = await get_credential(session, credential_id)
        credential.status = "disabled"
        await session.commit()
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.disabled",
            "api_credential",
            credential.id,
        )
        return credential
    except ApiResourceError as error:
        raise _error(error) from error


@router.delete("/credentials/{credential_id}", status_code=204)
async def credential_delete(
    credential_id: uuid.UUID, request: Request, session: DatabaseSession, admin: AdminUser
) -> Response:
    try:
        credential = await get_credential(session, credential_id)
        await session.delete(credential)
        await session.commit()
        await _audit(
            session,
            request,
            admin,
            "api_resource.credential.deleted",
            "api_credential",
            credential_id,
        )
        return Response(status_code=204)
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts/{account_id}/models", response_model=list[ApiAccountModelResponse])
async def model_list(
    account_id: uuid.UUID, session: DatabaseSession, _user: CurrentUser
) -> list[ApiAccountModel]:
    try:
        await get_account(session, account_id)
    except ApiResourceError as error:
        raise _error(error) from error
    return list(
        (
            await session.scalars(
                select(ApiAccountModel)
                .where(ApiAccountModel.account_id == account_id)
                .order_by(ApiAccountModel.provider_model_id)
            )
        ).all()
    )


@router.post(
    "/accounts/{account_id}/models/manual", response_model=ApiAccountModelResponse, status_code=201
)
async def model_manual(
    account_id: uuid.UUID,
    payload: ApiAccountModelManual,
    session: DatabaseSession,
    _admin: AdminUser,
) -> ApiAccountModel:
    try:
        account, _ = await get_account(session, account_id)
        return await create_manual_model(session, account, payload)
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/accounts/{account_id}/models/sync", response_model=ApiSyncRunResponse)
async def model_sync(
    account_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiSyncRun:
    try:
        account, provider = await get_account(session, account_id)
        run = await sync_models(session, account, provider, admin, settings)
        await _audit(
            session,
            request,
            admin,
            "api_resource.models.synced"
            if run.status == "completed"
            else "api_resource.sync.failed",
            "api_account",
            account.id,
            {"sync_run_id": str(run.id), "status": run.status},
        )
        return run
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts/{account_id}/usage", response_model=list[ApiUsageResponse])
async def usage_list(
    account_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    granularity: str | None = None,
    model: str | None = None,
    credential_id: uuid.UUID | None = None,
    source: str | None = None,
) -> list[ApiUsageSnapshot]:
    query = select(ApiUsageSnapshot).where(ApiUsageSnapshot.account_id == account_id)
    if date_from:
        query = query.where(ApiUsageSnapshot.period_start >= date_from)
    if date_to:
        query = query.where(ApiUsageSnapshot.period_end <= date_to)
    if granularity:
        query = query.where(ApiUsageSnapshot.granularity == granularity)
    if model:
        query = query.where(ApiUsageSnapshot.provider_model_id == model)
    if credential_id:
        query = query.where(ApiUsageSnapshot.credential_id == credential_id)
    if source:
        query = query.where(ApiUsageSnapshot.source == source)
    return list((await session.scalars(query.order_by(ApiUsageSnapshot.period_start.desc()))).all())


@router.post(
    "/accounts/{account_id}/usage/manual", response_model=ApiUsageResponse, status_code=201
)
async def usage_manual(
    account_id: uuid.UUID,
    payload: ApiUsageManualCreate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiUsageSnapshot:
    try:
        account, _ = await get_account(session, account_id)
        snapshot = await create_manual_usage(session, account, payload)
        await _audit(
            session, request, admin, "api_resource.usage.manual_created", "api_account", account.id
        )
        return snapshot
    except ApiResourceError as error:
        raise _error(error) from error


@router.post("/accounts/{account_id}/usage/sync", response_model=ApiSyncRunResponse)
async def usage_sync(
    account_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> ApiSyncRun:
    try:
        account, provider = await get_account(session, account_id)
        run = await sync_usage(session, account, provider, admin, settings)
        await _audit(
            session,
            request,
            admin,
            "api_resource.usage.synced"
            if run.status == "completed"
            else "api_resource.sync.failed",
            "api_account",
            account.id,
            {"sync_run_id": str(run.id), "status": run.status},
        )
        return run
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/accounts/{account_id}/balance", response_model=list[ApiBalanceResponse])
async def balance_list(
    account_id: uuid.UUID, session: DatabaseSession, _user: CurrentUser
) -> list[ApiBalanceSnapshot]:
    return list(
        (
            await session.scalars(
                select(ApiBalanceSnapshot)
                .where(ApiBalanceSnapshot.account_id == account_id)
                .order_by(ApiBalanceSnapshot.collected_at.desc())
            )
        ).all()
    )


@router.post(
    "/accounts/{account_id}/balance/manual", response_model=ApiBalanceResponse, status_code=201
)
async def balance_manual(
    account_id: uuid.UUID,
    payload: ApiBalanceManualCreate,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ApiBalanceSnapshot:
    try:
        account, _ = await get_account(session, account_id)
        snapshot = await create_manual_balance(session, account, payload)
        await _audit(
            session,
            request,
            admin,
            "api_resource.balance.manual_created",
            "api_account",
            account.id,
        )
        return snapshot
    except ApiResourceError as error:
        raise _error(error) from error


@router.get("/usage/summary", response_model=ApiUsageSummaryResponse)
async def usage_summary_read(
    session: DatabaseSession, _user: CurrentUser
) -> ApiUsageSummaryResponse:
    return await usage_summary(session)


@router.get("/accounts/{account_id}/sync-runs", response_model=list[ApiSyncRunResponse])
async def sync_run_list(
    account_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ApiSyncRun]:
    return list(
        (
            await session.scalars(
                select(ApiSyncRun)
                .where(ApiSyncRun.account_id == account_id)
                .order_by(ApiSyncRun.created_at.desc())
                .limit(limit)
            )
        ).all()
    )


@router.get("/sync-runs/{sync_run_id}", response_model=ApiSyncRunResponse)
async def sync_run_detail(
    sync_run_id: uuid.UUID, session: DatabaseSession, _user: CurrentUser
) -> ApiSyncRun:
    run = await session.get(ApiSyncRun, sync_run_id)
    if run is None:
        raise AppError(
            status_code=404, code="api_sync_run_not_found", message="Sync run was not found."
        )
    return run


@router.post("/accounts/{account_id}/sync", response_model=list[ApiSyncRunResponse])
async def account_sync(
    account_id: uuid.UUID,
    payload: ApiSyncRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    settings: SettingsDependency,
) -> list[ApiSyncRun]:
    invalid = set(payload.sync_types) - {"models", "usage", "balance"}
    if invalid:
        raise AppError(
            status_code=422, code="api_sync_type_invalid", message="Sync type is invalid."
        )
    try:
        account, provider = await get_account(session, account_id)
        runs: list[ApiSyncRun] = []
        for sync_type in dict.fromkeys(payload.sync_types):
            if sync_type == "models":
                runs.append(await sync_models(session, account, provider, admin, settings))
            elif sync_type == "usage":
                runs.append(await sync_usage(session, account, provider, admin, settings))
            else:
                capabilities = provider.capabilities
                if not capabilities.get(f"{sync_type}_sync", False):
                    raise AppError(
                        status_code=422,
                        code="api_provider_capability_unsupported",
                        message=f"Provider does not support {sync_type} synchronization.",
                    )
        await _audit(
            session, request, admin, "api_resource.account.synced", "api_account", account.id
        )
        return runs
    except ApiResourceError as error:
        raise _error(error) from error
