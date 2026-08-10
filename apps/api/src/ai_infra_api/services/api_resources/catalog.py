import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings
from ai_infra_api.db.models import (
    ApiAccount,
    ApiAccountModel,
    ApiBalanceSnapshot,
    ApiCredential,
    ApiHealthCheck,
    ApiProvider,
    ApiSyncRun,
    ApiUsageSnapshot,
    User,
)
from ai_infra_api.schemas.api_resources import (
    ApiAccountCreate,
    ApiAccountModelManual,
    ApiAccountResponse,
    ApiAccountUpdate,
    ApiBalanceManualCreate,
    ApiCredentialCreate,
    ApiCredentialRotate,
    ApiCredentialUpdate,
    ApiProviderResponse,
    ApiUsageManualCreate,
    ApiUsageSummaryResponse,
)
from ai_infra_api.services.api_resources.adapters.base import ProviderContext
from ai_infra_api.services.api_resources.adapters.generic_openai import ProviderRequestError
from ai_infra_api.services.api_resources.adapters.registry import ADAPTERS, get_adapter
from ai_infra_api.services.api_resources.encryption import CredentialEncryption, mask_credential
from ai_infra_api.services.api_resources.network_policy import validate_external_base_url

ACCOUNT_STATUSES = {"active", "unverified", "degraded", "disabled", "archived"}
CREDENTIAL_TYPES = {"api_key", "bearer_token"}
SYNC_TYPES = {"models", "usage", "balance"}


class ApiResourceError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def utc_now() -> datetime:
    return datetime.now(UTC)


async def ensure_builtin_providers(session: AsyncSession) -> None:
    existing = set((await session.scalars(select(ApiProvider.slug))).all())
    for adapter in ADAPTERS.values():
        if adapter.slug not in existing:
            session.add(
                ApiProvider(
                    slug=adapter.slug,
                    display_name=adapter.display_name,
                    provider_type="built_in",
                    default_base_url=adapter.default_base_url,
                    capabilities=adapter.capabilities.model_dump(),
                    is_enabled=True,
                )
            )
    await session.flush()


async def list_providers(session: AsyncSession) -> list[ApiProvider]:
    await ensure_builtin_providers(session)
    return list(
        (await session.scalars(select(ApiProvider).order_by(ApiProvider.display_name))).all()
    )


async def get_provider(session: AsyncSession, slug: str) -> ApiProvider:
    await ensure_builtin_providers(session)
    provider = await session.scalar(select(ApiProvider).where(ApiProvider.slug == slug))
    if provider is None:
        raise ApiResourceError("api_provider_not_found", "API provider was not found.", 404)
    return provider


async def create_account(
    session: AsyncSession, payload: ApiAccountCreate, user: User, settings: Settings
) -> ApiAccount:
    provider = await get_provider(session, payload.provider_slug)
    if not provider.is_enabled:
        raise ApiResourceError("api_provider_disabled", "API provider is disabled.")
    base_url_value = str(payload.base_url) if payload.base_url else provider.default_base_url
    if not base_url_value:
        raise ApiResourceError("api_base_url_required", "A base URL is required for this provider.")
    base_url = await _validated_url(base_url_value, settings)
    account = ApiAccount(
        provider_id=provider.id,
        name=payload.name.strip(),
        purpose=payload.purpose,
        owner=payload.owner,
        base_url=base_url,
        status="unverified",
        billing_currency=payload.billing_currency,
        monthly_budget=payload.monthly_budget,
        tags=_tags(payload.tags),
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    session.add(account)
    await session.flush()
    if payload.credential_name and payload.credential_value:
        await create_credential(
            session,
            account,
            ApiCredentialCreate(
                name=payload.credential_name,
                credential_type=payload.credential_type,
                value=payload.credential_value,
            ),
            user,
            settings,
        )
    await session.commit()
    return account


async def list_accounts(
    session: AsyncSession,
    *,
    provider: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    owner: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> list[ApiAccountResponse]:
    await ensure_builtin_providers(session)
    query = select(ApiAccount, ApiProvider).join(
        ApiProvider, ApiProvider.id == ApiAccount.provider_id
    )
    if not include_archived:
        query = query.where(ApiAccount.status != "archived")
    if provider:
        query = query.where(ApiProvider.slug == provider)
    if status:
        query = query.where(ApiAccount.status == status)
    if owner:
        query = query.where(ApiAccount.owner == owner)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ApiAccount.name.ilike(pattern),
                ApiAccount.purpose.ilike(pattern),
                ApiAccount.owner.ilike(pattern),
            )
        )
    rows = [
        (account, item_provider)
        for account, item_provider in (
            await session.execute(query.order_by(ApiAccount.updated_at.desc()))
        ).tuples()
    ]
    if tag:
        rows = [(account, item_provider) for account, item_provider in rows if tag in account.tags]
    return [
        await account_response(session, account, item_provider) for account, item_provider in rows
    ]


async def get_account(
    session: AsyncSession, account_id: uuid.UUID
) -> tuple[ApiAccount, ApiProvider]:
    row = (
        await session.execute(
            select(ApiAccount, ApiProvider)
            .join(ApiProvider, ApiProvider.id == ApiAccount.provider_id)
            .where(ApiAccount.id == account_id)
        )
    ).one_or_none()
    if row is None:
        raise ApiResourceError("api_account_not_found", "API account was not found.", 404)
    return row[0], row[1]


async def account_response(
    session: AsyncSession, account: ApiAccount, provider: ApiProvider
) -> ApiAccountResponse:
    credential_count = await session.scalar(
        select(func.count())
        .select_from(ApiCredential)
        .where(ApiCredential.account_id == account.id)
    )
    model_count = await session.scalar(
        select(func.count())
        .select_from(ApiAccountModel)
        .where(ApiAccountModel.account_id == account.id, ApiAccountModel.is_available.is_(True))
    )
    balance = await session.scalar(
        select(ApiBalanceSnapshot)
        .where(ApiBalanceSnapshot.account_id == account.id)
        .order_by(ApiBalanceSnapshot.collected_at.desc())
        .limit(1)
    )
    usage_cost = await session.scalar(
        select(func.sum(ApiUsageSnapshot.cost_amount)).where(
            ApiUsageSnapshot.account_id == account.id
        )
    )
    return ApiAccountResponse(
        id=account.id,
        provider=ApiProviderResponse.model_validate(provider),
        name=account.name,
        purpose=account.purpose,
        owner=account.owner,
        base_url=account.base_url,
        status=account.status,
        billing_currency=account.billing_currency,
        monthly_budget=float(account.monthly_budget)
        if account.monthly_budget is not None
        else None,
        tags=account.tags,
        notes=account.notes,
        last_verified_at=account.last_verified_at,
        last_synced_at=account.last_synced_at,
        credential_count=credential_count or 0,
        model_count=model_count or 0,
        latest_balance=float(balance.balance_amount)
        if balance and balance.balance_amount is not None
        else None,
        latest_usage_cost=float(usage_cost) if usage_cost is not None else None,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


async def update_account(
    session: AsyncSession, account: ApiAccount, payload: ApiAccountUpdate, settings: Settings
) -> None:
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in ACCOUNT_STATUSES - {"archived"}:
        raise ApiResourceError("api_account_status_invalid", "API account status is invalid.")
    if payload.base_url is not None:
        values["base_url"] = await _validated_url(str(payload.base_url), settings)
    if payload.tags is not None:
        values["tags"] = _tags(payload.tags)
    for key, value in values.items():
        setattr(account, key, value)
    await session.commit()
    await session.refresh(account)


async def create_credential(
    session: AsyncSession,
    account: ApiAccount,
    payload: ApiCredentialCreate,
    user: User,
    settings: Settings,
) -> ApiCredential:
    if payload.credential_type not in CREDENTIAL_TYPES:
        raise ApiResourceError("api_credential_type_invalid", "Credential type is invalid.")
    encryption = CredentialEncryption(settings)
    credential_id = uuid.uuid4()
    fingerprint = encryption.fingerprint(payload.value)
    duplicate = await session.scalar(
        select(ApiCredential.id).where(
            ApiCredential.account_id == account.id, ApiCredential.fingerprint == fingerprint
        )
    )
    if duplicate:
        raise ApiResourceError("api_credential_duplicate", "Credential already exists.", 409)
    credential = ApiCredential(
        id=credential_id,
        account_id=account.id,
        name=payload.name.strip(),
        credential_type=payload.credential_type,
        encrypted_value=encryption.encrypt(account.id, credential_id, payload.value),
        encryption_key_version=encryption.key_version,
        masked_value=mask_credential(payload.value),
        fingerprint=fingerprint,
        status="active",
        expires_at=payload.expires_at,
        created_by_user_id=user.id,
    )
    session.add(credential)
    await session.flush()
    return credential


async def get_credential(session: AsyncSession, credential_id: uuid.UUID) -> ApiCredential:
    credential = await session.get(ApiCredential, credential_id)
    if credential is None:
        raise ApiResourceError("api_credential_not_found", "Credential was not found.", 404)
    return credential


async def update_credential(
    session: AsyncSession, credential: ApiCredential, payload: ApiCredentialUpdate
) -> None:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(credential, key, value)
    await session.commit()


async def rotate_credential(
    session: AsyncSession,
    credential: ApiCredential,
    payload: ApiCredentialRotate,
    settings: Settings,
) -> None:
    encryption = CredentialEncryption(settings)
    fingerprint = encryption.fingerprint(payload.value)
    duplicate = await session.scalar(
        select(ApiCredential.id).where(
            ApiCredential.account_id == credential.account_id,
            ApiCredential.fingerprint == fingerprint,
            ApiCredential.id != credential.id,
        )
    )
    if duplicate:
        raise ApiResourceError("api_credential_duplicate", "Credential already exists.", 409)
    credential.encrypted_value = encryption.encrypt(
        credential.account_id, credential.id, payload.value
    )
    credential.encryption_key_version = encryption.key_version
    credential.masked_value = mask_credential(payload.value)
    credential.fingerprint = fingerprint
    credential.status = "active"
    credential.last_error_code = None
    credential.last_error_message = None
    await session.commit()


async def validate_credential(
    session: AsyncSession, credential: ApiCredential, settings: Settings
) -> ApiHealthCheck:
    account, provider = await get_account(session, credential.account_id)
    adapter = get_adapter(provider.slug)
    base_url = await _validated_url(account.base_url, settings)
    encryption = CredentialEncryption(settings)
    context = ProviderContext(
        base_url=base_url,
        credential=encryption.decrypt(account.id, credential.id, credential.encrypted_value),
        timeout_seconds=settings.api_resource_request_timeout_seconds,
        max_response_bytes=settings.api_resource_max_response_bytes,
    )
    result = await adapter.validate_credential(context)
    checked_at = utc_now()
    credential.last_validated_at = checked_at
    credential.status = "active" if result.valid else "invalid"
    credential.last_error_code = result.error_code
    credential.last_error_message = result.error_message
    account.last_verified_at = checked_at
    account.status = "active" if result.valid else "degraded"
    health = ApiHealthCheck(
        account_id=account.id,
        credential_id=credential.id,
        check_type="credential",
        status="healthy" if result.valid else "failed",
        latency_ms=result.latency_ms,
        error_code=result.error_code,
        error_message=result.error_message,
        checked_at=checked_at,
    )
    session.add(health)
    await session.commit()
    return health


async def sync_models(
    session: AsyncSession,
    account: ApiAccount,
    provider: ApiProvider,
    user: User | None,
    settings: Settings,
) -> ApiSyncRun:
    run = await _start_sync(session, account.id, "models", user)
    try:
        credential = await session.scalar(
            select(ApiCredential)
            .where(ApiCredential.account_id == account.id, ApiCredential.status == "active")
            .order_by(ApiCredential.created_at)
        )
        if credential is None:
            raise ApiResourceError("api_credential_required", "An active credential is required.")
        adapter = get_adapter(provider.slug)
        base_url = await _validated_url(account.base_url, settings)
        encryption = CredentialEncryption(settings)
        models = await adapter.list_models(
            ProviderContext(
                base_url=base_url,
                credential=encryption.decrypt(
                    account.id, credential.id, credential.encrypted_value
                ),
                timeout_seconds=settings.api_resource_request_timeout_seconds,
                max_response_bytes=settings.api_resource_max_response_bytes,
            )
        )
        now = utc_now()
        existing = {
            item.provider_model_id: item
            for item in (
                await session.scalars(
                    select(ApiAccountModel).where(ApiAccountModel.account_id == account.id)
                )
            ).all()
        }
        for item in existing.values():
            if item.source == "provider":
                item.is_available = False
        for model in models:
            record = existing.get(model.model_id)
            if record is None:
                record = ApiAccountModel(
                    account_id=account.id,
                    provider_model_id=model.model_id,
                    discovered_at=now,
                    source="provider",
                )
                session.add(record)
            record.display_name = model.display_name
            record.capabilities = list(model.capabilities)
            record.context_window = model.context_window
            record.is_available = True
            record.last_seen_at = now
        account.last_synced_at = now
        run.status = "completed"
        run.records_written = len(models)
        run.completed_at = now
        run.details = {"models": len(models)}
        session.add(
            ApiHealthCheck(
                account_id=account.id,
                credential_id=credential.id,
                check_type="models",
                status="healthy",
                checked_at=now,
            )
        )
    except (ApiResourceError, ProviderRequestError, ValueError) as error:
        run.status = "failed"
        run.completed_at = utc_now()
        run.error_code = getattr(error, "code", "api_sync_failed")
        run.error_message = str(error)[:512]
        account.status = "degraded"
    await session.commit()
    return run


async def create_manual_model(
    session: AsyncSession, account: ApiAccount, payload: ApiAccountModelManual
) -> ApiAccountModel:
    record = await session.scalar(
        select(ApiAccountModel).where(
            ApiAccountModel.account_id == account.id,
            ApiAccountModel.provider_model_id == payload.provider_model_id,
        )
    )
    now = utc_now()
    if record is None:
        record = ApiAccountModel(
            account_id=account.id,
            provider_model_id=payload.provider_model_id,
            source="manual",
            discovered_at=now,
        )
        session.add(record)
    record.display_name = payload.display_name
    record.model_family = payload.model_family
    record.capabilities = payload.capabilities
    record.context_window = payload.context_window
    record.is_available = True
    record.last_seen_at = now
    await session.commit()
    return record


async def create_manual_usage(
    session: AsyncSession, account: ApiAccount, payload: ApiUsageManualCreate
) -> ApiUsageSnapshot:
    if payload.granularity not in {"hour", "day", "month"}:
        raise ApiResourceError("api_usage_granularity_invalid", "Usage granularity is invalid.")
    if payload.credential_id:
        credential = await get_credential(session, payload.credential_id)
        if credential.account_id != account.id:
            raise ApiResourceError(
                "api_credential_account_mismatch", "Credential belongs to another account."
            )
    snapshot = ApiUsageSnapshot(
        account_id=account.id,
        credential_id=payload.credential_id,
        provider_model_id=payload.provider_model_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        granularity=payload.granularity,
        request_count=payload.request_count,
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        cached_tokens=payload.cached_tokens,
        total_tokens=payload.total_tokens,
        cost_amount=payload.cost_amount,
        currency=payload.currency or account.billing_currency,
        source="manual",
        raw_metadata=payload.metadata,
    )
    session.add(snapshot)
    await session.commit()
    return snapshot


async def sync_usage(
    session: AsyncSession,
    account: ApiAccount,
    provider: ApiProvider,
    user: User | None,
    settings: Settings,
) -> ApiSyncRun:
    run = await _start_sync(session, account.id, "usage", user)
    try:
        credential = await session.scalar(
            select(ApiCredential)
            .where(
                ApiCredential.account_id == account.id,
                ApiCredential.status == "active",
            )
            .order_by(ApiCredential.created_at)
        )
        if credential is None:
            raise ApiResourceError("api_credential_required", "An active credential is required.")
        adapter = get_adapter(provider.slug)
        if not adapter.capabilities.usage_sync:
            raise ApiResourceError(
                "api_provider_capability_unsupported",
                "Provider does not support usage synchronization.",
            )
        encryption = CredentialEncryption(settings)
        period_end = utc_now()
        period_start = period_end - timedelta(days=7)
        records = await adapter.fetch_usage(
            ProviderContext(
                base_url=await _validated_url(account.base_url, settings),
                credential=encryption.decrypt(
                    account.id, credential.id, credential.encrypted_value
                ),
                timeout_seconds=settings.api_resource_request_timeout_seconds,
                max_response_bytes=settings.api_resource_max_response_bytes,
            ),
            period_start,
            period_end,
        )
        existing_ids = set(
            (
                await session.scalars(
                    select(ApiUsageSnapshot.provider_record_id).where(
                        ApiUsageSnapshot.account_id == account.id,
                        ApiUsageSnapshot.provider_record_id.is_not(None),
                    )
                )
            ).all()
        )
        written = 0
        for record in records:
            if record.record_id in existing_ids:
                continue
            session.add(
                ApiUsageSnapshot(
                    account_id=account.id,
                    provider_model_id=record.model_id,
                    period_start=record.period_start,
                    period_end=record.period_end,
                    granularity="day",
                    request_count=record.request_count,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    total_tokens=record.total_tokens,
                    cost_amount=record.cost_amount,
                    currency=record.currency.upper()
                    if record.currency
                    else account.billing_currency,
                    source="provider_api",
                    provider_record_id=record.record_id,
                    raw_metadata={
                        "credential_reference": record.credential_reference,
                    }
                    if record.credential_reference
                    else {},
                )
            )
            written += 1
        account.last_synced_at = period_end
        run.status = "completed"
        run.records_written = written
        run.completed_at = period_end
        run.details = {"period_days": 7, "records_received": len(records)}
    except (ApiResourceError, ProviderRequestError, ValueError) as error:
        run.status = "failed"
        run.completed_at = utc_now()
        run.error_code = getattr(error, "code", "api_sync_failed")
        run.error_message = str(error)[:512]
        account.status = "degraded"
    await session.commit()
    return run


async def create_manual_balance(
    session: AsyncSession, account: ApiAccount, payload: ApiBalanceManualCreate
) -> ApiBalanceSnapshot:
    snapshot = ApiBalanceSnapshot(
        account_id=account.id,
        balance_amount=payload.balance_amount,
        credit_limit=payload.credit_limit,
        remaining_credit=payload.remaining_credit,
        currency=payload.currency or account.billing_currency,
        expires_at=payload.expires_at,
        source="manual",
    )
    session.add(snapshot)
    await session.commit()
    return snapshot


async def usage_summary(session: AsyncSession) -> ApiUsageSummaryResponse:
    rows = (await session.execute(select(ApiUsageSnapshot))).scalars().all()
    costs: dict[str, float] = {}
    for row in rows:
        if row.cost_amount is not None:
            currency = row.currency or "UNSPECIFIED"
            costs[currency] = costs.get(currency, 0.0) + float(row.cost_amount)
    account_count = await session.scalar(
        select(func.count()).select_from(ApiAccount).where(ApiAccount.status != "archived")
    )
    return ApiUsageSummaryResponse(
        account_count=account_count or 0,
        request_count=sum(row.request_count or 0 for row in rows),
        input_tokens=sum(row.input_tokens or 0 for row in rows),
        output_tokens=sum(row.output_tokens or 0 for row in rows),
        total_tokens=sum(row.total_tokens or 0 for row in rows),
        costs_by_currency=costs,
    )


async def _start_sync(
    session: AsyncSession, account_id: uuid.UUID, sync_type: str, user: User | None
) -> ApiSyncRun:
    running = await session.scalar(
        select(ApiSyncRun.id).where(
            ApiSyncRun.account_id == account_id,
            ApiSyncRun.sync_type == sync_type,
            ApiSyncRun.status.in_(("queued", "running")),
        )
    )
    if running:
        raise ApiResourceError("api_sync_already_running", "A sync is already running.", 409)
    run = ApiSyncRun(
        account_id=account_id,
        sync_type=sync_type,
        status="running",
        requested_by_user_id=user.id if user else None,
        started_at=utc_now(),
    )
    session.add(run)
    await session.flush()
    return run


async def _validated_url(value: str, settings: Settings) -> str:
    try:
        return await validate_external_base_url(value, settings)
    except ValueError as error:
        raise ApiResourceError("api_base_url_rejected", str(error)) from error


def _tags(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in values if item.strip()))
