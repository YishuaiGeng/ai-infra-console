from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from ai_infra_api.core.config import Settings
from ai_infra_api.services.model_catalog import (
    ProviderCatalogError,
    clear_catalog_cache,
    get_catalog_model,
    map_huggingface_model,
    map_modelscope_model,
    search_catalog,
    validate_catalog_query,
)
from ai_infra_api.services.model_tasks import ModelTaskError


class FakeHuggingFace:
    def __init__(self, records: list[object], error: Exception | None = None) -> None:
        self.records = records
        self.error = error
        self.calls = 0

    def list_models(self, **_kwargs: object) -> list[object]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.records

    def model_info(self, repo_id: str, **kwargs: object) -> object:
        del repo_id, kwargs
        if self.error:
            raise self.error
        return self.records[0]


class FakeModelScope:
    def __init__(self, records: list[object], error: Exception | None = None) -> None:
        self.records = records
        self.error = error

    def list_repos(self, repo_type: str, **kwargs: object) -> object:
        del repo_type, kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(items=self.records)

    def get_repo(self, repo_id: str, repo_type: str, **kwargs: object) -> object:
        del repo_id, repo_type, kwargs
        if self.error:
            raise self.error
        return self.records[0]


def hf_record(**overrides: Any) -> object:
    values = {
        "id": "Qwen/Qwen3-8B",
        "pipeline_tag": "text-generation",
        "tags": ["license:apache-2.0", "transformers"],
        "downloads": 42,
        "likes": 7,
        "gated": False,
        "private": False,
        "sha": "revision-a",
        "used_storage": 1234,
        "config": {"architectures": ["Qwen3ForCausalLM"]},
        "card_data": None,
        "last_modified": datetime(2026, 8, 8, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def ms_record(**overrides: Any) -> object:
    values = {
        "owner": "Qwen",
        "name": "Qwen3-8B",
        "id": "Qwen/Qwen3-8B",
        "display_name": "Qwen3 8B",
        "tasks": ["text-generation"],
        "tags": ["chat"],
        "description": "ModelScope fixture",
        "downloads": 21,
        "likes": 3,
        "license": "Apache-2.0",
        "gated": False,
        "login_required": False,
        "private": False,
        "file_size": 5678,
        "last_modified": "2026-08-08T00:00:00Z",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_catalog_mapping_and_query_validation() -> None:
    hf = map_huggingface_model(hf_record())
    assert hf.provider == "huggingface"
    assert hf.license == "apache-2.0"
    assert hf.architecture == "Qwen3ForCausalLM"
    ms = map_modelscope_model(ms_record(login_required=True))
    assert ms.provider == "modelscope"
    assert ms.gated is True
    assert ms.last_modified is not None
    assert validate_catalog_query(" Qwen ") == "Qwen"
    try:
        validate_catalog_query("bad\nquery")
    except ModelTaskError as exc:
        assert exc.code == "invalid_catalog_query"
    else:
        raise AssertionError("control character query was accepted")


async def test_catalog_search_partial_failure_cache_and_detail() -> None:
    clear_catalog_cache()
    settings = Settings(
        environment="test",
        model_catalog_cache_seconds=60,
        model_catalog_max_results=5,
    )
    hf = FakeHuggingFace([hf_record(), hf_record(id="invalid")])
    ms = FakeModelScope([], TimeoutError())
    result = await search_catalog(
        settings,
        query="Qwen",
        provider=None,
        limit=5,
        hf_client=hf,
        modelscope_client=ms,
    )
    assert [item.source_id for item in result.items] == ["Qwen/Qwen3-8B"]
    assert result.provider_errors == {"modelscope": "timeout"}
    cached = await search_catalog(
        settings,
        query="Qwen",
        provider="huggingface",
        limit=5,
        hf_client=hf,
    )
    assert cached.items[0].revision == "revision-a"
    assert hf.calls == 1
    detail = await get_catalog_model(
        settings,
        "huggingface",
        "Qwen/Qwen3-8B",
        hf_client=hf,
    )
    assert detail.size == 1234


async def test_catalog_detail_sanitizes_provider_failure() -> None:
    settings = Settings(environment="test")
    client = FakeHuggingFace([], RuntimeError("secret upstream body"))
    try:
        await get_catalog_model(
            settings,
            "huggingface",
            "Qwen/Qwen3-8B",
            hf_client=client,
        )
    except ProviderCatalogError as exc:
        assert exc.code == "unavailable"
        assert "secret" not in exc.public_message
    else:
        raise AssertionError("provider failure was not mapped")
