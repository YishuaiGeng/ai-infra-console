import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ProviderCapabilitiesResponse(BaseModel):
    credential_validation: bool
    model_discovery: bool
    balance_sync: bool
    usage_sync: bool
    usage_by_model: bool
    usage_by_credential: bool
    manual_usage_import: bool


class ApiProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    display_name: str
    provider_type: str
    default_base_url: str | None
    capabilities: ProviderCapabilitiesResponse
    is_enabled: bool


class ApiAccountCreate(BaseModel):
    provider_slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    purpose: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=128)
    base_url: HttpUrl | None = None
    billing_currency: str | None = Field(default=None, max_length=16)
    monthly_budget: float | None = Field(default=None, ge=0)
    tags: list[str] = Field(default_factory=list, max_length=32)
    notes: str | None = Field(default=None, max_length=4_096)
    credential_name: str | None = Field(default=None, max_length=128)
    credential_type: str = "api_key"
    credential_value: str | None = Field(default=None, min_length=1, max_length=8_192)

    @model_validator(mode="after")
    def credential_fields_match(self) -> "ApiAccountCreate":
        if bool(self.credential_name) != bool(self.credential_value):
            raise ValueError("credential_name and credential_value must be provided together")
        return self


class ApiAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    purpose: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=128)
    base_url: HttpUrl | None = None
    status: str | None = None
    billing_currency: str | None = Field(default=None, max_length=16)
    monthly_budget: float | None = Field(default=None, ge=0)
    tags: list[str] | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=4_096)


class ApiAccountResponse(BaseModel):
    id: uuid.UUID
    provider: ApiProviderResponse
    name: str
    purpose: str | None
    owner: str | None
    base_url: str
    status: str
    billing_currency: str | None
    monthly_budget: float | None
    tags: list[str]
    notes: str | None
    last_verified_at: datetime | None
    last_synced_at: datetime | None
    credential_count: int = 0
    model_count: int = 0
    latest_balance: float | None = None
    latest_usage_cost: float | None = None
    created_at: datetime
    updated_at: datetime


class ApiCredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    credential_type: str = "api_key"
    value: str = Field(min_length=1, max_length=8_192)
    expires_at: datetime | None = None


class ApiCredentialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    expires_at: datetime | None = None


class ApiCredentialRotate(BaseModel):
    value: str = Field(min_length=1, max_length=8_192)


class ApiCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    name: str
    credential_type: str
    masked_value: str
    status: str
    expires_at: datetime | None
    last_validated_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


class ApiAccountModelManual(BaseModel):
    provider_model_id: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    model_family: str | None = Field(default=None, max_length=128)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    context_window: int | None = Field(default=None, ge=1)


class ApiAccountModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    provider_model_id: str
    display_name: str | None
    model_family: str | None
    capabilities: list[str]
    context_window: int | None
    is_available: bool
    source: str
    discovered_at: datetime
    last_seen_at: datetime


class ApiUsageManualCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    granularity: str = "day"
    credential_id: uuid.UUID | None = None
    provider_model_id: str | None = Field(default=None, max_length=255)
    request_count: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=16)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def period_is_valid(self) -> "ApiUsageManualCreate":
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self


class ApiUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    credential_id: uuid.UUID | None
    provider_model_id: str | None
    period_start: datetime
    period_end: datetime
    granularity: str
    request_count: int | None
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    total_tokens: int | None
    cost_amount: float | None
    currency: str | None
    source: str
    collected_at: datetime


class ApiBalanceManualCreate(BaseModel):
    balance_amount: float | None = None
    credit_limit: float | None = None
    remaining_credit: float | None = None
    currency: str | None = Field(default=None, max_length=16)
    expires_at: datetime | None = None


class ApiBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    balance_amount: float | None
    credit_limit: float | None
    remaining_credit: float | None
    currency: str | None
    expires_at: datetime | None
    source: str
    collected_at: datetime


class ApiSyncRequest(BaseModel):
    sync_types: list[str] = Field(min_length=1, max_length=3)


class ApiSyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    sync_type: str
    status: str
    requested_by_user_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    records_written: int
    error_code: str | None
    error_message: str | None
    details: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ApiUsageSummaryResponse(BaseModel):
    account_count: int
    request_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    costs_by_currency: dict[str, float]
