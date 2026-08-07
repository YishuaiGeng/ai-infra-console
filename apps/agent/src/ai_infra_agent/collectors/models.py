import json
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal

import httpx

from ai_infra_agent.config import AgentSettings
from ai_infra_agent.schemas import (
    CollectorStatus,
    ModelDirectorySnapshot,
    ModelInstallationSnapshot,
    ModelInventorySnapshot,
)

OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
OLLAMA_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
WEIGHT_SUFFIXES = {".safetensors", ".bin"}
QUANTIZATION_PATTERN = re.compile(
    r"(?i)(q[2-8](?:_[a-z0-9]+)+|int[2-8]|fp(?:8|16|32)|bf16)"
)

_cache_lock = Lock()
_cached_inventory: ModelInventorySnapshot | None = None
_cached_at = 0.0
_cached_key: tuple[object, ...] | None = None


def _inside(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _safe_file(path: Path, root: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=True)
        if not _inside(resolved, root) or not resolved.is_file():
            return None
        return resolved
    except OSError:
        return None


def _walk_directories(root: Path, max_depth: int) -> Iterator[tuple[Path, list[Path]]]:
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        files: list[Path] = []
        child_directories: list[Path] = []
        for entry in entries:
            try:
                if entry.is_symlink():
                    if _safe_file(entry, root) is not None:
                        files.append(entry)
                    continue
                if entry.is_file():
                    files.append(entry)
                elif entry.is_dir() and depth < max_depth:
                    child_directories.append(entry)
            except OSError:
                continue
        yield directory, files
        for child in reversed(child_directories):
            stack.append((child, depth + 1))


def _read_json(path: Path, root: Path, max_bytes: int) -> dict[str, Any]:
    resolved = _safe_file(path, root)
    if resolved is None:
        return {}
    try:
        if resolved.stat().st_size > max_bytes:
            return {}
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _text(value: object, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:max_length] if cleaned else None


def _architecture(config: dict[str, Any]) -> str | None:
    architectures = config.get("architectures")
    if isinstance(architectures, list) and architectures:
        return _text(architectures[0], 128)
    return _text(config.get("architecture"), 128)


def _quantization(config: dict[str, Any], *names: str) -> str | None:
    quantization = config.get("quantization_config")
    if isinstance(quantization, dict):
        method = _text(quantization.get("quant_method"), 48)
        bits = quantization.get("bits")
        if method and isinstance(bits, int):
            return f"{method}-{bits}bit"[:64]
        if method:
            return method
    joined = " ".join(names)
    match = QUANTIZATION_PATTERN.search(joined)
    if match:
        return match.group(1).upper()
    dtype = _text(config.get("torch_dtype"), 64)
    return dtype.upper() if dtype else None


def _hugging_face_identity(path: Path) -> tuple[str, str, str | None] | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if not part.startswith("models--"):
            continue
        source_id = part.removeprefix("models--").replace("--", "/")
        revision = None
        tail = parts[index + 1 :]
        if "snapshots" in tail:
            snapshot_index = tail.index("snapshots")
            if snapshot_index + 1 < len(tail):
                revision = tail[snapshot_index + 1][:128]
        return "huggingface", source_id[:255], revision
    return None


def _local_identity(path: Path, config: dict[str, Any]) -> tuple[str, str, str | None]:
    hugging_face = _hugging_face_identity(path)
    if hugging_face is not None:
        return hugging_face
    configured = _text(config.get("_name_or_path"), 255)
    if configured and not Path(configured).is_absolute():
        return "local", configured, None
    return "local", path.name[:255], None


def _regular_size(path: Path, root: Path) -> int | None:
    resolved = _safe_file(path, root)
    if resolved is None:
        return None
    try:
        return resolved.stat().st_size
    except OSError:
        return None


def _directory_installation(
    directory: Path,
    files: list[Path],
    root: Path,
    max_metadata_bytes: int,
) -> ModelInstallationSnapshot | None:
    weights = [file for file in files if file.suffix.casefold() in WEIGHT_SUFFIXES]
    if not weights:
        return None
    sizes = [size for file in weights if (size := _regular_size(file, root)) is not None]
    if not sizes:
        return None
    config = _read_json(directory / "config.json", root, max_metadata_bytes)
    source, source_id, revision = _local_identity(directory, config)
    weight_names = [file.name for file in weights]
    format_name: Literal["safetensors", "pytorch"] = (
        "safetensors"
        if any(file.suffix.casefold() == ".safetensors" for file in weights)
        else "pytorch"
    )
    display_name = _text(config.get("model_name"), 255) or source_id.rsplit("/", 1)[-1]
    metadata: dict[str, str] = {}
    dtype = _text(config.get("torch_dtype"), 64)
    if dtype:
        metadata["dtype"] = dtype
    return ModelInstallationSnapshot(
        source=source,
        source_id=source_id,
        name=source_id,
        display_name=display_name,
        architecture=_architecture(config),
        model_type=_text(config.get("model_type"), 64),
        path=str(directory),
        size=sum(sizes),
        format=format_name,
        quantization=_quantization(config, directory.name, *weight_names),
        revision=revision,
        file_count=len(sizes),
        metadata=metadata,
    )


def _gguf_installation(path: Path, root: Path) -> ModelInstallationSnapshot | None:
    size = _regular_size(path, root)
    if size is None:
        return None
    source_id = path.stem[:255]
    return ModelInstallationSnapshot(
        source="local",
        source_id=source_id,
        name=source_id,
        display_name=source_id,
        path=str(path),
        size=size,
        format="gguf",
        quantization=_quantization({}, path.name),
    )


def scan_model_directory(
    root: Path,
    *,
    is_default: bool,
    max_depth: int,
    max_installations: int,
    max_metadata_bytes: int,
    scanned_at: datetime | None = None,
) -> tuple[ModelDirectorySnapshot, list[ModelInstallationSnapshot]]:
    timestamp = scanned_at or datetime.now(UTC)
    try:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise NotADirectoryError
        next(resolved.iterdir(), None)
    except FileNotFoundError:
        return (
            ModelDirectorySnapshot(
                path=str(root),
                is_default=is_default,
                available=False,
                error_code="not_found",
                scanned_at=timestamp,
            ),
            [],
        )
    except (NotADirectoryError, PermissionError, OSError):
        return (
            ModelDirectorySnapshot(
                path=str(root),
                is_default=is_default,
                available=False,
                error_code="unavailable",
                scanned_at=timestamp,
            ),
            [],
        )

    installations: list[ModelInstallationSnapshot] = []
    for directory, files in _walk_directories(resolved, max_depth):
        installation = _directory_installation(
            directory,
            files,
            resolved,
            max_metadata_bytes,
        )
        if installation is not None:
            installations.append(installation)
        for file in files:
            if file.suffix.casefold() == ".gguf":
                gguf = _gguf_installation(file, resolved)
                if gguf is not None:
                    installations.append(gguf)
        if len(installations) > max_installations:
            return (
                ModelDirectorySnapshot(
                    path=str(resolved),
                    is_default=is_default,
                    available=False,
                    error_code="limit_exceeded",
                    scanned_at=timestamp,
                ),
                [],
            )
    unique = {item.path: item for item in installations}
    return (
        ModelDirectorySnapshot(
            path=str(resolved),
            is_default=is_default,
            available=True,
            scanned_at=timestamp,
        ),
        sorted(unique.values(), key=lambda item: item.path.casefold()),
    )


def discover_ollama(
    *,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
    collected_at: datetime | None = None,
) -> tuple[CollectorStatus, list[ModelInstallationSnapshot]]:
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            trust_env=False,
        ) as client:
            response = client.get(OLLAMA_TAGS_URL, headers={"accept": "application/json"})
            response.raise_for_status()
            if len(response.content) > OLLAMA_MAX_RESPONSE_BYTES:
                raise ValueError("response_too_large")
            payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return CollectorStatus(available=False, detail="Ollama inventory unavailable"), []

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return CollectorStatus(available=False, detail="Ollama inventory malformed"), []
    installations: dict[str, ModelInstallationSnapshot] = {}
    for item in models[:10_000]:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name") or item.get("model"), 255)
        size = item.get("size")
        if name is None or not isinstance(size, int) or size < 0:
            continue
        raw_details = item.get("details")
        details: dict[str, Any] = raw_details if isinstance(raw_details, dict) else {}
        metadata: dict[str, str] = {}
        for source_key, target_key in (
            ("digest", "digest"),
            ("parameter_size", "parameters"),
            ("family", "family"),
            ("modified_at", "modified_at"),
        ):
            value = item.get(source_key) if source_key in item else details.get(source_key)
            text = _text(value, 255)
            if text:
                metadata[target_key] = text
        installations[name] = ModelInstallationSnapshot(
            source="ollama",
            source_id=name,
            name=name,
            display_name=name,
            architecture=_text(details.get("family"), 128),
            model_type="LLM",
            path=f"ollama://{name}",
            size=size,
            format="ollama",
            quantization=_text(details.get("quantization_level"), 64),
            revision=_text(item.get("digest"), 128),
            metadata=metadata,
        )
    return (
        CollectorStatus(available=True, version="api-tags"),
        sorted(installations.values(), key=lambda item: item.source_id.casefold()),
    )


def _collect_model_inventory(
    settings: AgentSettings,
    *,
    ollama_available: bool,
) -> ModelInventorySnapshot:
    collected_at = datetime.now(UTC)
    directories: list[ModelDirectorySnapshot] = []
    installations: list[ModelInstallationSnapshot] = []
    default = settings.default_model_directory
    for root in settings.allowed_model_directories:
        state, found = scan_model_directory(
            root,
            is_default=default == root,
            max_depth=settings.model_scan_max_depth,
            max_installations=settings.model_scan_max_installations,
            max_metadata_bytes=settings.model_metadata_max_bytes,
            scanned_at=collected_at,
        )
        directories.append(state)
        installations.extend(found)
    if ollama_available:
        ollama, ollama_models = discover_ollama(
            timeout_seconds=settings.ollama_timeout_seconds,
            collected_at=collected_at,
        )
        installations.extend(ollama_models)
    else:
        ollama = CollectorStatus(available=False, detail="Ollama runtime unavailable")
    unique = {(item.source, item.path): item for item in installations}
    return ModelInventorySnapshot(
        collected_at=collected_at,
        directories=directories,
        installations=sorted(
            unique.values(),
            key=lambda item: (item.source, item.source_id.casefold(), item.path.casefold()),
        )[: settings.model_scan_max_installations],
        ollama=ollama,
    )


def collect_model_inventory(
    settings: AgentSettings,
    *,
    ollama_available: bool,
    monotonic: float | None = None,
) -> ModelInventorySnapshot:
    global _cached_at, _cached_inventory, _cached_key
    now = monotonic if monotonic is not None else time.monotonic()
    cache_key = (
        settings.allowed_model_directories,
        settings.default_model_directory,
        settings.model_scan_max_depth,
        settings.model_scan_max_installations,
        settings.model_metadata_max_bytes,
        settings.ollama_timeout_seconds,
        ollama_available,
    )
    with _cache_lock:
        if (
            _cached_inventory is not None
            and _cached_key == cache_key
            and now - _cached_at < settings.model_scan_interval_seconds
        ):
            return _cached_inventory.model_copy(deep=True)
        inventory = _collect_model_inventory(settings, ollama_available=ollama_available)
        _cached_inventory = inventory
        _cached_at = now
        _cached_key = cache_key
        return inventory.model_copy(deep=True)


def reset_model_inventory_cache() -> None:
    global _cached_at, _cached_inventory, _cached_key
    with _cache_lock:
        _cached_inventory = None
        _cached_at = 0.0
        _cached_key = None
