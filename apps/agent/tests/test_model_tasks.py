import asyncio
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest
from pydantic import HttpUrl, SecretStr

from ai_infra_agent.collectors.models import scan_model_directory
from ai_infra_agent.config import AgentSettings
from ai_infra_agent.model_tasks import (
    DownloadProgress,
    ModelTaskCancelled,
    ModelTaskExecutionError,
    ModelTaskExecutor,
)
from ai_infra_agent.schemas import (
    DeleteTaskCommand,
    DownloadProgressResponse,
    DownloadTaskCommand,
    ModelTaskCommand,
)
from ai_infra_agent.task_supervisor import ModelTaskSupervisor


def settings(root: Path, fixture: Path | None = None) -> AgentSettings:
    return AgentSettings(
        environment="test",
        allowed_model_directories=(root,),
        default_model_directory=root,
        enable_model_mutations=True,
        model_download_fixture_source=fixture,
    )


def download_command(
    root: Path,
    *,
    provider: Literal["huggingface", "modelscope"] = "huggingface",
    target: Path | None = None,
    cancel_requested: bool = False,
) -> DownloadTaskCommand:
    expected = target or root / provider / "Qwen" / "Qwen3-8B"
    return DownloadTaskCommand(
        kind="download",
        task_id=uuid.uuid4(),
        lease_token=SecretStr("lease-token-with-at-least-thirty-two-characters"),
        root_path=str(root),
        provider=provider,
        source_id="Qwen/Qwen3-8B",
        revision="revision-a",
        target_path=str(expected),
        cancel_requested=cancel_requested,
    )


def fixture_repo(root: Path, provider: str = "huggingface") -> Path:
    repo = root / provider / "Qwen" / "Qwen3-8B"
    repo.mkdir(parents=True)
    (repo / "config.json").write_text(
        '{"architectures":["Qwen3ForCausalLM"],"model_type":"qwen3"}',
        encoding="utf-8",
    )
    (repo / "model.safetensors").write_bytes(b"tiny-model-weights")
    return repo


def test_fixture_download_inventory_idempotency_and_delete(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    fixtures = tmp_path / "fixtures"
    fixture_repo(fixtures)
    configured = settings(root, fixtures)
    command = download_command(root)
    progress = DownloadProgress()
    executor = ModelTaskExecutor(configured)

    result = executor.execute_download(command, progress, threading.Event())
    target = Path(result.path)
    assert target == root / "huggingface" / "Qwen" / "Qwen3-8B"
    assert result.downloaded_size > 0
    assert progress.snapshot().downloaded_size == result.downloaded_size
    assert (target / ".ai-infra-source.json").is_file()
    _, installations = scan_model_directory(
        root,
        is_default=True,
        max_depth=6,
        max_installations=20,
        max_metadata_bytes=1024,
    )
    assert [(item.source, item.source_id, item.revision) for item in installations] == [
        ("huggingface", "Qwen/Qwen3-8B", "revision-a")
    ]

    repeated = executor.execute_download(command, DownloadProgress(), threading.Event())
    assert repeated.path == result.path
    delete = DeleteTaskCommand(
        kind="delete",
        task_id=uuid.uuid4(),
        lease_token=SecretStr("another-lease-token-with-thirty-two-characters"),
        root_path=str(root),
        model_file_id=uuid.uuid4(),
        source="huggingface",
        source_id="Qwen/Qwen3-8B",
        target_path=str(target),
    )
    executor.execute_delete(delete)
    assert not target.exists()
    executor.execute_delete(delete)


def test_download_and_delete_path_guards(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    fixtures = tmp_path / "fixtures"
    fixture_repo(fixtures)
    configured = settings(root, fixtures)
    executor = ModelTaskExecutor(configured)

    with pytest.raises(ModelTaskExecutionError, match="outside"):
        executor.execute_download(
            download_command(root, target=tmp_path / "outside"),
            DownloadProgress(),
            threading.Event(),
        )
    disabled = AgentSettings(environment="test", allowed_model_directories=(root,))
    with pytest.raises(ModelTaskExecutionError, match="disabled"):
        ModelTaskExecutor(disabled).execute_download(
            download_command(root),
            DownloadProgress(),
            threading.Event(),
        )
    target = root / "huggingface" / "Qwen" / "Qwen3-8B"
    target.mkdir(parents=True)
    (target / "unrelated.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ModelTaskExecutionError, match="already exists"):
        executor.execute_download(download_command(root), DownloadProgress(), threading.Event())

    delete_root = DeleteTaskCommand(
        kind="delete",
        task_id=uuid.uuid4(),
        lease_token=SecretStr("delete-lease-token-with-thirty-two-characters"),
        root_path=str(root),
        model_file_id=None,
        source="local",
        source_id="models",
        target_path=str(root),
    )
    with pytest.raises(ModelTaskExecutionError, match="outside"):
        executor.execute_delete(delete_root)


def test_cancelled_download_removes_task_partial(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    fixtures = tmp_path / "fixtures"
    fixture_repo(fixtures)
    command = download_command(root, cancel_requested=True)
    with pytest.raises(ModelTaskCancelled):
        ModelTaskExecutor(settings(root, fixtures)).execute_download(
            command,
            DownloadProgress(),
            threading.Event(),
        )
    assert not (root / ".ai-infra-partials" / str(command.task_id)).exists()


def test_official_provider_adapters_receive_local_configuration(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    hf_calls: list[dict[str, object]] = []

    def fake_hf(**kwargs: object) -> object:
        hf_calls.append(kwargs)
        if kwargs.get("dry_run"):
            return [SimpleNamespace(file_size=5)]
        local_dir = Path(str(kwargs["local_dir"]))
        (local_dir / "model.safetensors").write_bytes(b"12345")
        progress_type = kwargs["tqdm_class"]
        progress_bar = progress_type(total=5, unit="B")  # type: ignore[operator]
        progress_bar.update(5)
        progress_bar.close()
        return str(local_dir)

    configured = AgentSettings(
        environment="test",
        allowed_model_directories=(root,),
        enable_model_mutations=True,
        hf_token=SecretStr("local-hf-secret"),
        hf_endpoint=HttpUrl("https://hf.example.test"),
    )
    result = ModelTaskExecutor(configured, hf_download=fake_hf).execute_download(
        download_command(root),
        DownloadProgress(),
        threading.Event(),
    )
    assert Path(result.path).is_dir()
    assert hf_calls[0]["token"] == "local-hf-secret"
    assert hf_calls[0]["endpoint"] == "https://hf.example.test"

    ms_root = tmp_path / "ms-models"
    ms_root.mkdir()

    class FakeModelScope:
        def __init__(self) -> None:
            self.kwargs: dict[str, object] = {}

        def download_repo(self, repo_id: str, repo_type: str, **kwargs: object) -> Path:
            assert repo_id == "Qwen/Qwen3-8B"
            assert repo_type == "model"
            self.kwargs = kwargs
            local_dir = Path(str(kwargs["local_dir"]))
            (local_dir / "model.safetensors").write_bytes(b"modelscope")
            callbacks = kwargs["progress_callbacks"]
            callback = callbacks[0]("model.safetensors", 10)  # type: ignore[index]
            callback.update(10)
            callback.end()
            return local_dir

    ms_client = FakeModelScope()
    ms_result = ModelTaskExecutor(
        settings(ms_root),
        modelscope_client=ms_client,
    ).execute_download(
        download_command(ms_root, provider="modelscope"),
        DownloadProgress(),
        threading.Event(),
    )
    assert Path(ms_result.path).is_dir()
    assert ms_client.kwargs["revision"] == "revision-a"


class FakeReporter:
    def __init__(self, command: ModelTaskCommand) -> None:
        self.command: ModelTaskCommand | None = command
        self.progress_reports: list[tuple[int, int | None]] = []
        self.download_outcome: str | None = None
        self.delete_outcome: str | None = None

    async def claim_model_task(self) -> ModelTaskCommand | None:
        command, self.command = self.command, None
        return command

    async def report_download_progress(
        self,
        command: DownloadTaskCommand,
        *,
        downloaded_size: int,
        total_size: int | None,
        speed_bytes_per_second: int | None,
    ) -> DownloadProgressResponse:
        del command, speed_bytes_per_second
        self.progress_reports.append((downloaded_size, total_size))
        return DownloadProgressResponse(
            cancel_requested=False,
            lease_expires_at=datetime(2026, 8, 8, tzinfo=UTC),
        )

    async def complete_download_task(
        self,
        command: DownloadTaskCommand,
        *,
        outcome: Literal["completed", "failed", "cancelled"],
        downloaded_size: int,
        total_size: int | None,
        final_path: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        del command, downloaded_size, total_size, final_path, error_code, error_message
        self.download_outcome = outcome

    async def complete_delete_task(
        self,
        command: DeleteTaskCommand,
        *,
        outcome: Literal["completed", "failed"],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        del command, error_code, error_message
        self.delete_outcome = outcome


async def test_supervisor_completes_fixture_download_without_blocking_tick(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    fixtures = tmp_path / "fixtures"
    fixture_repo(fixtures)
    reporter = FakeReporter(download_command(root))
    supervisor = ModelTaskSupervisor(
        reporter,
        ModelTaskExecutor(settings(root, fixtures)),
        progress_seconds=0.01,
    )
    await supervisor.tick()
    assert reporter.download_outcome is None
    await supervisor.wait()
    assert reporter.download_outcome == "completed"
    await supervisor.tick()


async def test_supervisor_reports_delete_failure(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()
    command = DeleteTaskCommand(
        kind="delete",
        task_id=uuid.uuid4(),
        lease_token=SecretStr("delete-lease-token-with-thirty-two-characters"),
        root_path=str(root),
        model_file_id=None,
        source="local",
        source_id="models",
        target_path=str(root),
    )
    reporter = FakeReporter(command)
    supervisor = ModelTaskSupervisor(
        reporter,
        ModelTaskExecutor(settings(root)),
        progress_seconds=0.01,
    )
    await supervisor.tick()
    await supervisor.wait()
    assert reporter.delete_outcome == "failed"
    await asyncio.sleep(0)
