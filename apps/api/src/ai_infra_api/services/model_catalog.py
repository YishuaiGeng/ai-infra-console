import asyncio
import time
from collections import OrderedDict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol, cast

from huggingface_hub import HfApi
from modelscope_hub import HubApi

from ai_infra_api.core.config import Settings
from ai_infra_api.schemas.model_tasks import (
    CatalogModelResponse,
    CatalogSearchResponse,
    ModelProvider,
)
from ai_infra_api.services.model_tasks import ModelTaskError, validate_repository_id

CacheKey = tuple[str, str, int]
_CACHE: OrderedDict[CacheKey, tuple[float, list[CatalogModelResponse]]] = OrderedDict()
_CACHE_LIMIT = 128


class HuggingFaceCatalogClient(Protocol):
    def list_models(self, **kwargs: object) -> Iterable[object]: ...

    def model_info(self, repo_id: str, **kwargs: object) -> object: ...


class ModelScopeCatalogClient(Protocol):
    def list_repos(self, repo_type: str, **kwargs: object) -> object: ...

    def get_repo(self, repo_id: str, repo_type: str, **kwargs: object) -> object: ...


class ProviderCatalogError(RuntimeError):
    def __init__(self, provider: ModelProvider, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.provider = provider
        self.code = code
        self.public_message = public_message


def clear_catalog_cache() -> None:
    _CACHE.clear()


def validate_catalog_query(query: str) -> str:
    normalized = query.strip()
    if len(normalized) > 128:
        raise ModelTaskError(
            "catalog_query_too_long", "Catalog search is limited to 128 characters."
        )
    if any(ord(character) < 32 for character in normalized):
        raise ModelTaskError(
            "invalid_catalog_query",
            "Catalog search cannot contain control characters.",
        )
    return normalized


def _license(tags: list[str], explicit: object = None) -> str | None:
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()[:128]
    return next((tag.split(":", 1)[1] for tag in tags if tag.startswith("license:")), None)


def _datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        timestamp = float(value) / (1_000 if value > 100_000_000_000 else 1)
        try:
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _string_list(value: object, *, limit: int = 50) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item)[:128] for item in value[:limit] if str(item).strip()]


def map_huggingface_model(info: object) -> CatalogModelResponse:
    source_id = str(getattr(info, "id", ""))
    validate_repository_id(source_id)
    tags = _string_list(getattr(info, "tags", None))
    config = getattr(info, "config", None)
    architecture = None
    if isinstance(config, dict):
        architectures = config.get("architectures")
        if isinstance(architectures, list) and architectures:
            architecture = str(architectures[0])[:128]
    card_data = getattr(info, "card_data", None)
    explicit_license = getattr(card_data, "license", None) if card_data is not None else None
    return CatalogModelResponse(
        provider="huggingface",
        source_id=source_id,
        display_name=source_id.rsplit("/", 1)[-1],
        model_type=getattr(info, "pipeline_tag", None),
        tags=tags,
        downloads=getattr(info, "downloads", None),
        likes=getattr(info, "likes", None),
        license=_license(tags, explicit_license),
        gated=bool(getattr(info, "gated", False)),
        private=bool(getattr(info, "private", False)),
        revision=getattr(info, "sha", None),
        size=getattr(info, "used_storage", None),
        architecture=architecture,
        last_modified=_datetime(getattr(info, "last_modified", None)),
    )


def map_modelscope_model(info: object) -> CatalogModelResponse:
    owner = str(getattr(info, "owner", "") or "")
    name = str(getattr(info, "name", "") or "")
    source_id = f"{owner}/{name}" if owner and name else str(getattr(info, "id", ""))
    validate_repository_id(source_id)
    tags = _string_list(getattr(info, "tags", None))
    tasks = _string_list(getattr(info, "tasks", None))
    display_name = str(getattr(info, "display_name", "") or name or source_id)
    return CatalogModelResponse(
        provider="modelscope",
        source_id=source_id,
        display_name=display_name[:255],
        model_type=tasks[0] if tasks else None,
        description=(str(value)[:1_024] if (value := getattr(info, "description", None)) else None),
        tags=tags,
        downloads=getattr(info, "downloads", None),
        likes=getattr(info, "likes", None),
        license=_license(tags, getattr(info, "license", None)),
        gated=bool(getattr(info, "gated", False) or getattr(info, "login_required", False)),
        private=bool(getattr(info, "private", False)),
        size=getattr(info, "file_size", None),
        last_modified=_datetime(getattr(info, "last_modified", None)),
    )


def _provider_error(provider: ModelProvider, error: Exception) -> ProviderCatalogError:
    name = type(error).__name__.lower()
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    if isinstance(error, TimeoutError) or "timeout" in name:
        return ProviderCatalogError(provider, "timeout", "The provider timed out.")
    if status_code in {401, 403} or "auth" in name or "permission" in name:
        return ProviderCatalogError(provider, "authentication", "Provider authentication failed.")
    if status_code == 429 or "ratelimit" in name or "rate_limit" in name:
        return ProviderCatalogError(
            provider, "rate_limited", "The provider rate limit was reached."
        )
    if status_code == 404 or "notfound" in name or "not_found" in name:
        return ProviderCatalogError(provider, "not_found", "The model was not found.")
    return ProviderCatalogError(provider, "unavailable", "The provider is unavailable.")


def _hf_client(settings: Settings) -> HuggingFaceCatalogClient:
    return cast(
        HuggingFaceCatalogClient,
        HfApi(
            endpoint=str(settings.hf_endpoint).rstrip("/"),
            token=(settings.hf_token.get_secret_value() if settings.hf_token else False),
            library_name="ai-infra-console",
            library_version=settings.app_version,
        ),
    )


def _modelscope_client(settings: Settings) -> ModelScopeCatalogClient:
    return cast(
        ModelScopeCatalogClient,
        HubApi(
            endpoint=str(settings.modelscope_endpoint).rstrip("/"),
            token=(
                settings.modelscope_token.get_secret_value() if settings.modelscope_token else None
            ),
        ),
    )


def _search_huggingface(
    client: HuggingFaceCatalogClient,
    query: str,
    limit: int,
) -> list[CatalogModelResponse]:
    try:
        records = client.list_models(
            search=query or None,
            limit=limit,
            sort="downloads",
            full=True,
            cardData=True,
            fetch_config=True,
        )
        items: list[CatalogModelResponse] = []
        for record in records:
            try:
                items.append(map_huggingface_model(record))
            except (ModelTaskError, ValueError, TypeError):
                continue
            if len(items) >= limit:
                break
        return items
    except Exception as exc:
        raise _provider_error("huggingface", exc) from exc


def _search_modelscope(
    client: ModelScopeCatalogClient,
    query: str,
    limit: int,
) -> list[CatalogModelResponse]:
    try:
        result = client.list_repos(
            "model",
            search=query or None,
            sort="downloads",
            page_number=1,
            page_size=limit,
        )
        records = cast(Iterable[object], getattr(result, "items", result))
        items: list[CatalogModelResponse] = []
        for record in records:
            try:
                items.append(map_modelscope_model(record))
            except (ModelTaskError, ValueError, TypeError):
                continue
            if len(items) >= limit:
                break
        return items
    except Exception as exc:
        raise _provider_error("modelscope", exc) from exc


def _cached(key: CacheKey, ttl: int) -> list[CatalogModelResponse] | None:
    cached = _CACHE.get(key)
    if cached is None:
        return None
    inserted_at, items = cached
    if time.monotonic() - inserted_at > ttl:
        _CACHE.pop(key, None)
        return None
    _CACHE.move_to_end(key)
    return [item.model_copy(deep=True) for item in items]


def _store(key: CacheKey, items: list[CatalogModelResponse]) -> None:
    _CACHE[key] = (time.monotonic(), [item.model_copy(deep=True) for item in items])
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_LIMIT:
        _CACHE.popitem(last=False)


async def search_catalog(
    settings: Settings,
    *,
    query: str,
    provider: ModelProvider | None,
    limit: int,
    hf_client: HuggingFaceCatalogClient | None = None,
    modelscope_client: ModelScopeCatalogClient | None = None,
) -> CatalogSearchResponse:
    normalized = validate_catalog_query(query)
    bounded_limit = min(limit, settings.model_catalog_max_results)
    providers: tuple[ModelProvider, ...] = (
        (provider,) if provider else ("huggingface", "modelscope")
    )

    async def one(selected: ModelProvider) -> tuple[ModelProvider, list[CatalogModelResponse]]:
        key = (selected, normalized.casefold(), bounded_limit)
        if settings.model_catalog_cache_seconds:
            cached = _cached(key, settings.model_catalog_cache_seconds)
            if cached is not None:
                return selected, cached
        if selected == "huggingface":
            selected_hf_client = hf_client or _hf_client(settings)
            items = await asyncio.wait_for(
                asyncio.to_thread(
                    _search_huggingface,
                    selected_hf_client,
                    normalized,
                    bounded_limit,
                ),
                timeout=settings.model_catalog_timeout_seconds,
            )
        else:
            selected_modelscope_client = modelscope_client or _modelscope_client(settings)
            items = await asyncio.wait_for(
                asyncio.to_thread(
                    _search_modelscope,
                    selected_modelscope_client,
                    normalized,
                    bounded_limit,
                ),
                timeout=settings.model_catalog_timeout_seconds,
            )
        if settings.model_catalog_cache_seconds:
            _store(key, items)
        return selected, items

    results = await asyncio.gather(*(one(item) for item in providers), return_exceptions=True)
    items: list[CatalogModelResponse] = []
    errors: dict[ModelProvider, str] = {}
    for selected, result in zip(providers, results, strict=True):
        if isinstance(result, BaseException):
            error = (
                result
                if isinstance(result, ProviderCatalogError)
                else _provider_error(selected, cast(Exception, result))
            )
            errors[selected] = error.code
        else:
            items.extend(result[1])
    items.sort(key=lambda item: (-(item.downloads or 0), item.provider, item.source_id.casefold()))
    return CatalogSearchResponse(
        items=items[: bounded_limit * len(providers)], provider_errors=errors
    )


async def get_catalog_model(
    settings: Settings,
    provider: ModelProvider,
    source_id: str,
    *,
    hf_client: HuggingFaceCatalogClient | None = None,
    modelscope_client: ModelScopeCatalogClient | None = None,
) -> CatalogModelResponse:
    validate_repository_id(source_id)
    try:
        if provider == "huggingface":
            selected_hf_client = hf_client or _hf_client(settings)
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    selected_hf_client.model_info,
                    source_id,
                    timeout=settings.model_catalog_timeout_seconds,
                    files_metadata=True,
                ),
                timeout=settings.model_catalog_timeout_seconds,
            )
            return map_huggingface_model(result)
        selected_modelscope_client = modelscope_client or _modelscope_client(settings)
        result = await asyncio.wait_for(
            asyncio.to_thread(selected_modelscope_client.get_repo, source_id, "model"),
            timeout=settings.model_catalog_timeout_seconds,
        )
        return map_modelscope_model(result)
    except ProviderCatalogError:
        raise
    except Exception as exc:
        raise _provider_error(provider, exc) from exc
