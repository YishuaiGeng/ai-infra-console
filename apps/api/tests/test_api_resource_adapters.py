from datetime import UTC, datetime

from ai_infra_api.services.api_resources.adapters.base import ProviderContext
from ai_infra_api.services.api_resources.adapters.generic_openai import AnthropicAdapter
from ai_infra_api.services.api_resources.adapters.registry import ADAPTERS


def test_builtin_adapter_registry_and_anthropic_headers() -> None:
    assert set(ADAPTERS) == {
        "openai",
        "codex",
        "anthropic",
        "claude-code",
        "aliyun-bailian",
        "generic-openai",
    }
    context = ProviderContext(
        base_url="https://api.anthropic.com/v1",
        credential="test-key",
        timeout_seconds=10,
        max_response_bytes=1024,
        credential_header="x-api-key",
        static_headers=(("anthropic-version", "2023-06-01"),),
    )
    assert context.request_headers() == {
        "x-api-key": "test-key",
        "anthropic-version": "2023-06-01",
    }


async def test_anthropic_usage_parser(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    adapter = AnthropicAdapter()

    async def fake_get_json(context, path):  # type: ignore[no-untyped-def]
        assert "group_by%5B%5D=api_key_id" in path
        assert "group_by%5B%5D=model" in path
        return {
            "data": [
                {
                    "starting_at": "2026-08-01T00:00:00Z",
                    "ending_at": "2026-08-02T00:00:00Z",
                    "results": [
                        {
                            "api_key_id": "key-1",
                            "model": "claude-sonnet-4-5",
                            "uncached_input_tokens": 100,
                            "cache_read_input_tokens": 25,
                            "cache_creation": {"ephemeral_5m_input_tokens": 10},
                            "output_tokens": 40,
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(adapter, "_get_json", fake_get_json)
    context = ProviderContext("https://example.com/v1", "key", 10, 1024)
    records = await adapter.fetch_usage(
        context,
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert len(records) == 1
    assert records[0].input_tokens == 135
    assert records[0].output_tokens == 40
    assert records[0].total_tokens == 175
    assert records[0].model_id == "claude-sonnet-4-5"
    assert records[0].credential_reference == "key-1"
