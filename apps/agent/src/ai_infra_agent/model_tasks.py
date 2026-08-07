from __future__ import annotations

import json
import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from huggingface_hub import snapshot_download
from modelscope_hub import HubApi, ProgressCallback
from tqdm.auto import tqdm

from ai_infra_agent.collectors.models import reset_model_inventory_cache, scan_model_directory
from ai_infra_agent.config import AgentSettings
from ai_infra_agent.schemas import DeleteTaskCommand, DownloadTaskCommand

CHUNK_SIZE = 1024 * 1024
MANIFEST_NAME = ".ai-infra-source.json"
INTERNAL_PARTIALS = ".ai-infra-partials"


class ModelTaskExecutionError(RuntimeError):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class ModelTaskCancelled(ModelTaskExecutionError):
    def __init__(self) -> None:
        super().__init__("cancelled", "The model task was cancelled.")


class ModelScopeDownloadClient(Protocol):
    def download_repo(self, repo_id: str, repo_type: str, **kwargs: object) -> Path: ...


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    downloaded_size: int
    total_size: int | None
    speed_bytes_per_second: int | None


@dataclass(frozen=True, slots=True)
class DownloadExecutionResult:
    path: str
    downloaded_size: int
    total_size: int | None


class DownloadProgress:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._downloaded_size = 0
        self._total_size: int | None = None
        self._speed: int | None = None
        self._last_bytes = 0
        self._last_time = time.monotonic()

    def set_total(self, value: int | None) -> None:
        with self._lock:
            self._total_size = value

    def add(self, value: int) -> None:
        if value <= 0:
            return
        with self._lock:
            total = self._downloaded_size + value
            if self._total_size is not None:
                total = min(total, self._total_size)
            self._downloaded_size = total
            now = time.monotonic()
            elapsed = now - self._last_time
            if elapsed >= 0.25:
                self._speed = max(0, int((total - self._last_bytes) / elapsed))
                self._last_bytes = total
                self._last_time = now

    def finish(self, total: int) -> None:
        with self._lock:
            self._downloaded_size = total
            self._total_size = total
            self._speed = 0

    def snapshot(self) -> ProgressSnapshot:
        with self._lock:
            return ProgressSnapshot(
                downloaded_size=self._downloaded_size,
                total_size=self._total_size,
                speed_bytes_per_second=self._speed,
            )


def _repository_parts(source_id: str) -> tuple[str, str]:
    parts = source_id.strip().split("/")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if (
        len(parts) != 2
        or any(not part or part in {".", ".."} for part in parts)
        or any(any(character not in allowed for character in part) for part in parts)
    ):
        raise ModelTaskExecutionError(
            "invalid_source_id",
            "The model source ID is not a valid owner/repository pair.",
        )
    return parts[0], parts[1]


def _root(settings: AgentSettings, command_root: str) -> Path:
    candidate = Path(command_root)
    try:
        if candidate.is_symlink():
            raise ModelTaskExecutionError(
                "model_root_symlink",
                "The selected model root cannot be a symbolic link.",
            )
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ModelTaskExecutionError(
            "model_root_unavailable",
            "The selected model root is unavailable.",
        ) from exc
    if not resolved.is_dir() or resolved not in settings.allowed_model_directories:
        raise ModelTaskExecutionError(
            "model_root_not_allowed",
            "The selected model root is not in the local Agent allowlist.",
        )
    return resolved


def _strict_target(root: Path, target_path: str) -> Path:
    target = Path(target_path)
    if not target.is_absolute():
        raise ModelTaskExecutionError("invalid_target_path", "The model target must be absolute.")
    resolved = target.resolve(strict=False)
    if resolved == root or not resolved.is_relative_to(root):
        raise ModelTaskExecutionError(
            "target_outside_model_root",
            "The model target is outside the local Agent allowlist.",
        )
    relative = resolved.relative_to(root)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if current.exists() and current.is_symlink():
            raise ModelTaskExecutionError(
                "target_symlink_parent",
                "The model target has a symbolic-link parent.",
            )
    return resolved


def _expected_download_target(
    settings: AgentSettings,
    command: DownloadTaskCommand,
) -> tuple[Path, Path]:
    root = _root(settings, command.root_path)
    owner, repository = _repository_parts(command.source_id)
    expected = root / command.provider / owner / repository
    supplied = _strict_target(root, command.target_path)
    if supplied != expected:
        raise ModelTaskExecutionError(
            "target_path_mismatch",
            "The requested target does not match the Agent-computed path.",
        )
    return root, expected


def _manifest(path: Path) -> dict[str, object]:
    manifest = path / MANIFEST_NAME
    try:
        if manifest.is_symlink() or manifest.stat().st_size > 16_384:
            return {}
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _manifest_matches(path: Path, command: DownloadTaskCommand) -> bool:
    value = _manifest(path)
    return (
        value.get("source") == command.provider
        and value.get("source_id") == command.source_id
        and value.get("revision") == command.revision
    )


def _write_manifest(path: Path, command: DownloadTaskCommand) -> None:
    payload = {
        "schema_version": 1,
        "source": command.provider,
        "source_id": command.source_id,
        "revision": command.revision,
        "task_id": str(command.task_id),
    }
    temporary = path / f"{MANIFEST_NAME}.tmp"
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path / MANIFEST_NAME)


def _directory_size(path: Path) -> int:
    total = 0
    for directory, names, files in os.walk(path, followlinks=False):
        directory_path = Path(directory)
        names[:] = [name for name in names if not (directory_path / name).is_symlink()]
        for name in files:
            candidate = directory_path / name
            try:
                if not candidate.is_symlink() and candidate.is_file():
                    total += candidate.stat().st_size
            except OSError:
                continue
    return total


def _progress_tqdm(
    progress: DownloadProgress,
    cancelled: threading.Event,
) -> type[tqdm[Any]]:
    class TaskTqdm(tqdm):
        def update(self, amount: float | None = 1) -> bool | None:
            if cancelled.is_set():
                raise ModelTaskCancelled
            result = super().update(amount)
            if self.unit == "B" and amount:
                progress.add(int(amount))
            return result

    return TaskTqdm


def _modelscope_progress(
    progress: DownloadProgress,
    cancelled: threading.Event,
) -> type[ProgressCallback]:
    class TaskProgressCallback(ProgressCallback):
        def update(self, size: int) -> None:
            if cancelled.is_set():
                raise ModelTaskCancelled
            progress.add(size)

        def end(self) -> None:
            if cancelled.is_set():
                raise ModelTaskCancelled

    return TaskProgressCallback


class ModelTaskExecutor:
    def __init__(
        self,
        settings: AgentSettings,
        *,
        hf_download: Callable[..., object] = snapshot_download,
        modelscope_client: ModelScopeDownloadClient | None = None,
    ) -> None:
        self._settings = settings
        self._hf_download = hf_download
        self._modelscope = modelscope_client

    def execute_download(
        self,
        command: DownloadTaskCommand,
        progress: DownloadProgress,
        cancelled: threading.Event,
    ) -> DownloadExecutionResult:
        if not self._settings.enable_model_mutations:
            raise ModelTaskExecutionError(
                "model_mutations_disabled",
                "Model mutations are disabled by local Agent policy.",
            )
        root, target = _expected_download_target(self._settings, command)
        if target.exists():
            if target.is_dir() and not target.is_symlink() and _manifest_matches(target, command):
                size = _directory_size(target)
                progress.finish(size)
                return DownloadExecutionResult(str(target), size, size)
            raise ModelTaskExecutionError(
                "target_already_exists",
                "The model target already exists and is not owned by this task.",
            )
        partial_root = root / INTERNAL_PARTIALS
        if partial_root.exists() and (partial_root.is_symlink() or not partial_root.is_dir()):
            raise ModelTaskExecutionError(
                "invalid_partial_directory",
                "The Agent partial-download directory is unsafe.",
            )
        partial_root.mkdir(mode=0o750, exist_ok=True)
        partial = partial_root / str(command.task_id)
        if partial.exists() and (partial.is_symlink() or not partial.is_dir()):
            raise ModelTaskExecutionError(
                "invalid_partial_target",
                "The task partial-download path is unsafe.",
            )
        partial.mkdir(mode=0o750, exist_ok=True)
        if command.cancel_requested or cancelled.is_set():
            shutil.rmtree(partial)
            raise ModelTaskCancelled
        try:
            if self._settings.model_download_fixture_source is not None:
                self._fixture_download(command, partial, progress, cancelled)
            elif command.provider == "huggingface":
                self._huggingface_download(command, partial, progress, cancelled)
            else:
                self._modelscope_download(command, partial, progress, cancelled)
            if cancelled.is_set():
                raise ModelTaskCancelled
            _write_manifest(partial, command)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            if _strict_target(root, str(target)) != target or target.exists():
                raise ModelTaskExecutionError(
                    "target_publish_conflict",
                    "The model target changed before it could be published.",
                )
            partial.replace(target)
            size = _directory_size(target)
            progress.finish(size)
            reset_model_inventory_cache()
            return DownloadExecutionResult(str(target), size, size)
        except ModelTaskCancelled:
            if partial.exists() and partial.is_dir() and not partial.is_symlink():
                shutil.rmtree(partial)
            raise
        except ModelTaskExecutionError:
            raise
        except Exception as exc:
            raise ModelTaskExecutionError(
                "provider_download_failed",
                "The provider download failed; this task can be retried.",
            ) from exc

    def _fixture_download(
        self,
        command: DownloadTaskCommand,
        partial: Path,
        progress: DownloadProgress,
        cancelled: threading.Event,
    ) -> None:
        fixture_root = self._settings.model_download_fixture_source
        assert fixture_root is not None
        owner, repository = _repository_parts(command.source_id)
        source = fixture_root / command.provider / owner / repository
        try:
            resolved = source.resolve(strict=True)
        except OSError as exc:
            raise ModelTaskExecutionError(
                "fixture_model_not_found",
                "The test model fixture does not exist.",
            ) from exc
        if not resolved.is_dir() or not resolved.is_relative_to(fixture_root):
            raise ModelTaskExecutionError(
                "invalid_fixture_model",
                "The test model fixture is invalid.",
            )
        files = [path for path in resolved.rglob("*") if path.is_file() and not path.is_symlink()]
        total = sum(path.stat().st_size for path in files)
        progress.set_total(total)
        for source_file in files:
            if cancelled.is_set():
                raise ModelTaskCancelled
            destination = partial / source_file.relative_to(resolved)
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            with source_file.open("rb") as reader, destination.open("wb") as writer:
                while chunk := reader.read(CHUNK_SIZE):
                    if cancelled.is_set():
                        raise ModelTaskCancelled
                    writer.write(chunk)
                    progress.add(len(chunk))

    def _huggingface_download(
        self,
        command: DownloadTaskCommand,
        partial: Path,
        progress: DownloadProgress,
        cancelled: threading.Event,
    ) -> None:
        token = self._settings.hf_token.get_secret_value() if self._settings.hf_token else False
        endpoint = str(self._settings.hf_endpoint).rstrip("/")
        dry_run = self._hf_download(
            repo_id=command.source_id,
            revision=command.revision,
            token=token,
            endpoint=endpoint,
            dry_run=True,
        )
        if isinstance(dry_run, list):
            total = sum(int(getattr(item, "file_size", 0)) for item in dry_run)
            progress.set_total(total)
        self._hf_download(
            repo_id=command.source_id,
            revision=command.revision,
            token=token,
            endpoint=endpoint,
            local_dir=partial,
            max_workers=self._settings.model_download_max_workers,
            tqdm_class=_progress_tqdm(progress, cancelled),
        )

    def _modelscope_download(
        self,
        command: DownloadTaskCommand,
        partial: Path,
        progress: DownloadProgress,
        cancelled: threading.Event,
    ) -> None:
        client = self._modelscope or cast(
            ModelScopeDownloadClient,
            HubApi(
                endpoint=str(self._settings.modelscope_endpoint).rstrip("/"),
                token=(
                    self._settings.modelscope_token.get_secret_value()
                    if self._settings.modelscope_token
                    else None
                ),
            ),
        )
        client.download_repo(
            command.source_id,
            "model",
            revision=command.revision,
            local_dir=partial,
            max_workers=self._settings.model_download_max_workers,
            progress_callbacks=[_modelscope_progress(progress, cancelled)],
        )

    def execute_delete(self, command: DeleteTaskCommand) -> None:
        if not self._settings.enable_model_mutations:
            raise ModelTaskExecutionError(
                "model_mutations_disabled",
                "Model mutations are disabled by local Agent policy.",
            )
        root = _root(self._settings, command.root_path)
        target = _strict_target(root, command.target_path)
        if not target.exists() and not target.is_symlink():
            reset_model_inventory_cache()
            return
        if target.is_symlink():
            raise ModelTaskExecutionError(
                "delete_target_symlink",
                "The Agent refuses to delete a symbolic-link target.",
            )
        if not target.is_file() and not target.is_dir():
            raise ModelTaskExecutionError(
                "delete_target_special_file",
                "The Agent refuses to delete a special filesystem object.",
            )
        if target.is_dir():
            manifest = _manifest(target)
            identity_matches = (
                manifest.get("source") == command.source
                and manifest.get("source_id") == command.source_id
            )
        else:
            identity_matches = False
        if not identity_matches:
            _, installations = scan_model_directory(
                root,
                is_default=False,
                max_depth=self._settings.model_scan_max_depth,
                max_installations=self._settings.model_scan_max_installations,
                max_metadata_bytes=self._settings.model_metadata_max_bytes,
            )
            identity_matches = any(
                Path(item.path).resolve(strict=False) == target
                and item.source == command.source
                and item.source_id == command.source_id
                for item in installations
            )
        if not identity_matches:
            raise ModelTaskExecutionError(
                "delete_identity_mismatch",
                "The local model identity does not match the deletion task.",
            )
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        reset_model_inventory_cache()
