from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class ProviderCapabilities(BaseModel):
    credential_validation: bool = True
    model_discovery: bool = True
    balance_sync: bool = False
    usage_sync: bool = False
    usage_by_model: bool = False
    usage_by_credential: bool = False
    manual_usage_import: bool = True


@dataclass(frozen=True)
class ProviderContext:
    base_url: str
    credential: str
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class ProviderModel:
    model_id: str
    display_name: str | None = None
    capabilities: tuple[str, ...] = ()
    context_window: int | None = None


@dataclass(frozen=True)
class ProviderUsage:
    record_id: str
    period_start: datetime
    period_end: datetime
    request_count: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_amount: float | None = None
    currency: str | None = None
    model_id: str | None = None
    credential_reference: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    latency_ms: int
    error_code: str | None = None
    error_message: str | None = None


class ProviderAdapter(Protocol):
    slug: str
    display_name: str
    default_base_url: str | None
    capabilities: ProviderCapabilities

    async def validate_credential(self, context: ProviderContext) -> ValidationResult: ...

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]: ...

    async def fetch_usage(
        self, context: ProviderContext, period_start: datetime, period_end: datetime
    ) -> list[ProviderUsage]: ...
