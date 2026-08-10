import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from ai_infra_api.services.api_resources.adapters.base import (
    ProviderCapabilities,
    ProviderContext,
    ProviderModel,
    ProviderUsage,
    ValidationResult,
)


class ProviderRequestError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class GenericOpenAIAdapter:
    slug = "generic-openai"
    display_name = "OpenAI Compatible"
    default_base_url: str | None = None
    capabilities = ProviderCapabilities()

    async def validate_credential(self, context: ProviderContext) -> ValidationResult:
        started = time.monotonic()
        try:
            await self.list_models(context)
        except ProviderRequestError as error:
            return ValidationResult(
                valid=False,
                latency_ms=int((time.monotonic() - started) * 1_000),
                error_code=error.code,
                error_message=error.message,
            )
        return ValidationResult(valid=True, latency_ms=int((time.monotonic() - started) * 1_000))

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        payload = await self._get_json(context, "/models")
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderRequestError(
                "provider_invalid_response", "Provider returned invalid model data."
            )
        return [
            ProviderModel(model_id=item["id"], display_name=item["id"])
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]

    async def fetch_usage(
        self, context: ProviderContext, period_start: datetime, period_end: datetime
    ) -> list[ProviderUsage]:
        raise ProviderRequestError(
            "provider_capability_unsupported", "Provider does not support usage synchronization."
        )

    async def _get_json(self, context: ProviderContext, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=context.timeout_seconds,
                follow_redirects=False,
            ) as client:
                async with client.stream(
                    "GET",
                    f"{context.base_url.rstrip('/')}{path}",
                    headers=context.request_headers(),
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        raise ProviderRequestError(
                            "provider_redirect_rejected", "Provider redirect was rejected."
                        )
                    if response.status_code in {401, 403}:
                        raise ProviderRequestError(
                            "provider_authentication_failed", "Credential was rejected."
                        )
                    if response.status_code == 429:
                        raise ProviderRequestError(
                            "provider_rate_limited", "Provider rate limit was reached."
                        )
                    if response.status_code >= 400:
                        raise ProviderRequestError(
                            "provider_request_failed", "Provider request failed."
                        )
                    body = await response.aread()
                    if len(body) > context.max_response_bytes:
                        raise ProviderRequestError(
                            "provider_response_too_large",
                            "Provider response exceeded the size limit.",
                        )
        except httpx.TimeoutException as error:
            raise ProviderRequestError("provider_timeout", "Provider request timed out.") from error
        except httpx.RequestError as error:
            raise ProviderRequestError(
                "provider_unavailable", "Provider is unavailable."
            ) from error
        try:
            payload = response.json()
        except ValueError as error:
            raise ProviderRequestError(
                "provider_invalid_response", "Provider returned invalid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise ProviderRequestError(
                "provider_invalid_response", "Provider returned invalid JSON."
            )
        return payload


class OpenAIAdapter(GenericOpenAIAdapter):
    slug = "openai"
    display_name = "OpenAI"
    default_base_url: str | None = "https://api.openai.com/v1"
    capabilities = ProviderCapabilities(
        usage_sync=True,
        usage_by_model=True,
        usage_by_credential=True,
    )

    async def fetch_usage(
        self, context: ProviderContext, period_start: datetime, period_end: datetime
    ) -> list[ProviderUsage]:
        query = urlencode(
            {
                "start_time": int(period_start.timestamp()),
                "end_time": int(period_end.timestamp()),
                "bucket_width": "1d",
                "limit": 31,
                "group_by": ["model", "api_key_id"],
            },
            doseq=True,
        )
        usage = await self._get_json(context, f"/organization/usage/completions?{query}")
        costs = await self._get_json(
            context,
            "/organization/costs?"
            + urlencode(
                {
                    "start_time": int(period_start.timestamp()),
                    "end_time": int(period_end.timestamp()),
                    "bucket_width": "1d",
                    "limit": 31,
                }
            ),
        )
        return self.parse_usage(usage, costs)

    @staticmethod
    def parse_usage(usage: dict[str, Any], costs: dict[str, Any]) -> list[ProviderUsage]:
        records: list[ProviderUsage] = []
        for bucket_index, bucket in enumerate(_data_buckets(usage)):
            start, end = _bucket_period(bucket)
            for result_index, result in enumerate(_result_items(bucket)):
                input_tokens = _optional_int(result.get("input_tokens"))
                output_tokens = _optional_int(result.get("output_tokens"))
                records.append(
                    ProviderUsage(
                        record_id=f"openai-usage-{start.timestamp():.0f}-{bucket_index}-{result_index}",
                        period_start=start,
                        period_end=end,
                        request_count=_optional_int(result.get("num_model_requests")),
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=(input_tokens or 0) + (output_tokens or 0),
                        model_id=_as_string(result.get("model")),
                        credential_reference=_as_string(result.get("api_key_id")),
                    )
                )
        for bucket_index, bucket in enumerate(_data_buckets(costs)):
            start, end = _bucket_period(bucket)
            for result_index, result in enumerate(_result_items(bucket)):
                amount = result.get("amount")
                if not isinstance(amount, dict):
                    continue
                value = amount.get("value")
                records.append(
                    ProviderUsage(
                        record_id=f"openai-cost-{start.timestamp():.0f}-{bucket_index}-{result_index}",
                        period_start=start,
                        period_end=end,
                        cost_amount=float(value) if isinstance(value, (int, float)) else None,
                        currency=_as_string(amount.get("currency")),
                    )
                )
        return records


class CodexAdapter(OpenAIAdapter):
    slug = "codex"
    display_name = "OpenAI Codex"


class AliyunBailianAdapter(GenericOpenAIAdapter):
    slug = "aliyun-bailian"
    display_name = "阿里云百炼"
    default_base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class AnthropicAdapter(GenericOpenAIAdapter):
    slug = "anthropic"
    display_name = "Anthropic / Claude Code"
    default_base_url: str | None = "https://api.anthropic.com/v1"
    capabilities = ProviderCapabilities(
        usage_sync=True,
        usage_by_model=True,
        usage_by_credential=True,
    )

    async def list_models(self, context: ProviderContext) -> list[ProviderModel]:
        payload = await self._get_json(context, "/models")
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderRequestError(
                "provider_invalid_response", "Provider returned invalid model data."
            )
        return [
            ProviderModel(model_id=item["id"], display_name=item.get("display_name", item["id"]))
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]

    async def fetch_usage(
        self, context: ProviderContext, period_start: datetime, period_end: datetime
    ) -> list[ProviderUsage]:
        query = urlencode(
            {
                "starting_at": period_start.isoformat().replace("+00:00", "Z"),
                "ending_at": period_end.isoformat().replace("+00:00", "Z"),
                "limit": 31,
                "group_by[]": ["api_key_id", "model"],
            },
            doseq=True,
        )
        payload = await self._get_json(context, f"/organizations/usage_report/messages?{query}")
        records: list[ProviderUsage] = []
        for bucket_index, bucket in enumerate(_data_buckets(payload)):
            start = _parse_datetime(bucket.get("starting_at"))
            end = _parse_datetime(bucket.get("ending_at"))
            if start is None or end is None:
                continue
            for result_index, result in enumerate(_result_items(bucket)):
                input_tokens = sum(
                    _number(result.get(key))
                    for key in ("uncached_input_tokens", "cache_read_input_tokens")
                )
                cache_creation = result.get("cache_creation")
                if isinstance(cache_creation, dict):
                    input_tokens += sum(_number(value) for value in cache_creation.values())
                output_tokens = _number(result.get("output_tokens"))
                records.append(
                    ProviderUsage(
                        record_id=f"anthropic-usage-{start.timestamp():.0f}-{bucket_index}-{result_index}",
                        period_start=start,
                        period_end=end,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        model_id=_as_string(result.get("model")),
                        credential_reference=_as_string(result.get("api_key_id")),
                    )
                )
        return records


class ClaudeCodeAdapter(AnthropicAdapter):
    slug = "claude-code"
    display_name = "Claude Code"


class ConfiguredOpenAIAdapter(GenericOpenAIAdapter):
    def __init__(self, slug: str, display_name: str) -> None:
        self.slug = slug
        self.display_name = display_name
        self.default_base_url: str | None = None
        self.capabilities = ProviderCapabilities()


def _data_buckets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _result_items(bucket: dict[str, Any]) -> list[dict[str, Any]]:
    results = bucket.get("results")
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _number(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _bucket_period(bucket: dict[str, Any]) -> tuple[datetime, datetime]:
    start = _optional_int(bucket.get("start_time")) or 0
    end = _optional_int(bucket.get("end_time")) or start
    return datetime.fromtimestamp(start, UTC), datetime.fromtimestamp(end, UTC)
