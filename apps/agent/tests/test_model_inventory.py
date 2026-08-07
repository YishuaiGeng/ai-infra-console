import json
from pathlib import Path

import httpx
import pytest

from ai_infra_agent.collectors.models import (
    collect_model_inventory,
    discover_ollama,
    reset_model_inventory_cache,
    scan_model_directory,
)
from ai_infra_agent.config import AgentSettings


def scan(root: Path, *, limit: int = 20):
    return scan_model_directory(
        root,
        is_default=True,
        max_depth=6,
        max_installations=limit,
        max_metadata_bytes=1024,
    )


def test_scans_sharded_hugging_face_and_standalone_gguf(tmp_path: Path) -> None:
    root = tmp_path / "models"
    snapshot = root / "models--Qwen--Qwen3-8B" / "snapshots" / "revision-1"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text(
        json.dumps(
            {
                "architectures": ["Qwen3ForCausalLM"],
                "model_type": "qwen3",
                "torch_dtype": "bfloat16",
            }
        ),
        encoding="utf-8",
    )
    (snapshot / "model-00001-of-00002.safetensors").write_bytes(b"a" * 8)
    (snapshot / "model-00002-of-00002.safetensors").write_bytes(b"b" * 12)
    gguf = root / "Qwen3-8B-Q4_K_M.gguf"
    gguf.write_bytes(b"g" * 7)

    state, installations = scan(root)

    assert state.available is True
    assert state.is_default is True
    assert {item.format: item.size for item in installations} == {
        "gguf": 7,
        "safetensors": 20,
    }
    hugging_face = next(item for item in installations if item.format == "safetensors")
    assert hugging_face.source == "huggingface"
    assert hugging_face.source_id == "Qwen/Qwen3-8B"
    assert hugging_face.revision == "revision-1"
    assert hugging_face.architecture == "Qwen3ForCausalLM"
    assert hugging_face.file_count == 2
    gguf_installation = next(item for item in installations if item.format == "gguf")
    assert gguf_installation.quantization == "Q4_K_M"


def test_scanner_handles_missing_malformed_and_limits(tmp_path: Path) -> None:
    missing, empty = scan(tmp_path / "missing")
    assert missing.available is False
    assert missing.error_code == "not_found"
    assert empty == []

    root = tmp_path / "models"
    first = root / "first"
    second = root / "second"
    first.mkdir(parents=True)
    second.mkdir()
    (first / "config.json").write_text("{not-json", encoding="utf-8")
    (first / "weights.bin").write_bytes(b"123")
    (second / "weights.bin").write_bytes(b"456")

    limited, installations = scan(root, limit=1)
    assert limited.available is False
    assert limited.error_code == "limit_exceeded"
    assert installations == []


def test_scanner_does_not_follow_escaping_symlink(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "outside.gguf"
    outside.write_bytes(b"outside")
    link = root / "escaped-Q4_K_M.gguf"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not available")

    state, installations = scan(root)

    assert state.available is True
    assert installations == []


def test_ollama_discovery_maps_and_deduplicates_tags() -> None:
    payload = {
        "models": [
            {
                "name": "qwen3:8b",
                "digest": "sha256:first",
                "size": 8_000,
                "modified_at": "2026-08-08T00:00:00Z",
                "details": {
                    "family": "qwen3",
                    "parameter_size": "8.2B",
                    "quantization_level": "Q4_K_M",
                },
            },
            {"name": "qwen3:8b", "digest": "sha256:second", "size": 9_000},
        ]
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))

    status, installations = discover_ollama(timeout_seconds=1, transport=transport)

    assert status.available is True
    assert len(installations) == 1
    assert installations[0].path == "ollama://qwen3:8b"
    assert installations[0].size == 9_000
    assert installations[0].format == "ollama"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"wrong": []}),
    ],
)
def test_ollama_discovery_degrades_invalid_responses(response: httpx.Response) -> None:
    transport = httpx.MockTransport(lambda _request: response)

    status, installations = discover_ollama(timeout_seconds=1, transport=transport)

    assert status.available is False
    assert installations == []


def test_inventory_cache_avoids_repeated_scan(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    (root / "first.gguf").write_bytes(b"first")
    settings = AgentSettings(
        environment="test",
        allowed_model_directories=(root,),
        default_model_directory=root,
        model_scan_interval_seconds=60,
    )
    reset_model_inventory_cache()
    first = collect_model_inventory(settings, ollama_available=False, monotonic=10)
    (root / "second.gguf").write_bytes(b"second")
    cached = collect_model_inventory(settings, ollama_available=False, monotonic=20)
    refreshed = collect_model_inventory(settings, ollama_available=False, monotonic=80)

    assert len(first.installations) == 1
    assert len(cached.installations) == 1
    assert len(refreshed.installations) == 2
