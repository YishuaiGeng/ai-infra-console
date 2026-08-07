import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, cast

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings
from ai_infra_api.db.models import (
    Deployment,
    Model,
    ModelDeleteTask,
    ModelDownloadTask,
    ModelFile,
    Server,
    ServerAgent,
    ServerModelDirectory,
    User,
)
from ai_infra_api.schemas.model_inventory import ModelServerResponse
from ai_infra_api.schemas.model_tasks import (
    DeleteTaskCommand,
    DeleteTerminalRequest,
    DownloadCreateRequest,
    DownloadProgressRequest,
    DownloadProgressResponse,
    DownloadTargetResponse,
    DownloadTaskCommand,
    DownloadTaskResponse,
    DownloadTerminalRequest,
    ModelDeleteTaskResponse,
    ModelTaskCommand,
)
from ai_infra_api.services.model_reads import list_model_directories

ACTIVE_DOWNLOAD_STATUSES = ("queued", "downloading", "cancelling")
TERMINAL_DOWNLOAD_STATUSES = ("completed", "failed", "cancelled")
ACTIVE_DELETE_STATUSES = ("queued", "deleting")
REPOSITORY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TaskRow = ModelDownloadTask | ModelDeleteTask


class ModelTaskError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def utc_now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def validate_repository_id(source_id: str) -> tuple[str, str]:
    parts = source_id.strip().split("/")
    if len(parts) != 2 or any(part in {".", ".."} for part in parts):
        raise ModelTaskError(
            "invalid_source_id",
            "A model source ID must use the owner/repository form.",
        )
    if any(REPOSITORY_PART.fullmatch(part) is None for part in parts):
        raise ModelTaskError(
            "invalid_source_id",
            "The model source ID contains unsupported characters.",
        )
    return parts[0], parts[1]


def build_target_path(root: str, provider: str, source_id: str) -> str:
    owner, repository = validate_repository_id(source_id)
    path_type = PureWindowsPath if "\\" in root else PurePosixPath
    base = path_type(root)
    target = base / provider / owner / repository
    if target == base or not target.is_relative_to(base):
        raise ModelTaskError("invalid_target_path", "The target is outside the selected root.")
    return str(target)


def _digest_lease(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _safe_error(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()[:1_024] or None


def _server_response(server: Server) -> ModelServerResponse:
    return ModelServerResponse(
        id=server.id,
        name=server.name,
        status=server.status,
        type=server.type,
        host=server.host,
        hostname=server.hostname,
    )


def download_response(task: ModelDownloadTask, server: Server) -> DownloadTaskResponse:
    progress = None
    if task.total_size is not None and task.total_size > 0:
        progress = min(100.0, round(task.downloaded_size / task.total_size * 100, 2))
    elif task.status == "completed":
        progress = 100.0
    return DownloadTaskResponse(
        id=task.id,
        model_id=task.model_id,
        server=_server_response(server),
        directory_id=task.directory_id,
        target_path=task.target_path,
        source=task.source,
        source_id=task.source_id,
        revision=task.revision,
        status=task.status,
        downloaded_size=task.downloaded_size,
        total_size=task.total_size,
        speed_bytes_per_second=task.speed_bytes_per_second,
        progress=progress,
        attempt_count=task.attempt_count,
        error_code=task.error_code,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        last_progress_at=task.last_progress_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def delete_response(task: ModelDeleteTask, server: Server) -> ModelDeleteTaskResponse:
    return ModelDeleteTaskResponse(
        id=task.id,
        model_file_id=task.model_file_id,
        server=_server_response(server),
        directory_id=task.directory_id,
        source=task.source,
        source_id=task.source_id,
        target_path=task.target_path,
        status=task.status,
        attempt_count=task.attempt_count,
        error_code=task.error_code,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _eligible_target(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    directory_id: uuid.UUID,
) -> tuple[Server, ServerModelDirectory]:
    server = await session.get(Server, server_id)
    if server is None:
        raise ModelTaskError("server_not_found", "The target server does not exist.")
    if server.name not in settings.mutable_server_names:
        raise ModelTaskError(
            "server_mutation_not_allowed",
            "Model mutations are disabled for this server.",
        )
    if server.status != "online":
        raise ModelTaskError("server_offline", "The target server is not online.")
    agent = await session.scalar(
        select(ServerAgent).where(
            ServerAgent.server_id == server.id,
            ServerAgent.token_hash.is_not(None),
            ServerAgent.revoked_at.is_(None),
        )
    )
    if agent is None:
        raise ModelTaskError("agent_unavailable", "The target server has no active Agent.")
    directory = await session.scalar(
        select(ServerModelDirectory).where(
            ServerModelDirectory.id == directory_id,
            ServerModelDirectory.server_id == server.id,
            ServerModelDirectory.is_allowed.is_(True),
            ServerModelDirectory.is_available.is_(True),
        )
    )
    if directory is None:
        raise ModelTaskError(
            "model_directory_not_selectable",
            "The target must be an available Agent-advertised directory.",
        )
    return server, directory


async def create_download_task(
    session: AsyncSession,
    settings: Settings,
    request: DownloadCreateRequest,
    user: User,
) -> tuple[ModelDownloadTask, Server]:
    server, directory = await _eligible_target(
        session,
        settings,
        request.server_id,
        request.directory_id,
    )
    target_path = build_target_path(directory.path, request.provider, request.source_id)
    duplicate = await session.scalar(
        select(ModelDownloadTask).where(
            ModelDownloadTask.server_id == server.id,
            ModelDownloadTask.target_path == target_path,
            ModelDownloadTask.status.in_(ACTIVE_DOWNLOAD_STATUSES),
        )
    )
    if duplicate is not None:
        raise ModelTaskError(
            "download_already_active",
            "An active download already owns this destination.",
        )
    installed = await session.scalar(
        select(ModelFile).where(
            ModelFile.server_id == server.id,
            ModelFile.path == target_path,
            ModelFile.revision == request.revision,
            ModelFile.status == "discovered",
        )
    )
    if installed is not None:
        raise ModelTaskError(
            "model_already_installed",
            "This model revision is already installed at the selected destination.",
        )
    model = await session.scalar(
        select(Model).where(
            Model.source == request.provider,
            Model.source_id == request.source_id,
        )
    )
    if model is None:
        model = Model(
            source=request.provider,
            source_id=request.source_id,
            name=request.source_id,
            display_name=request.source_id.rsplit("/", 1)[-1],
            metadata_json={},
        )
        session.add(model)
        await session.flush()
    task = ModelDownloadTask(
        model_id=model.id,
        server_id=server.id,
        directory_id=directory.id,
        requested_by_user_id=user.id,
        source=request.provider,
        source_id=request.source_id,
        revision=request.revision,
        target_path=target_path,
        status="queued",
        downloaded_size=0,
        attempt_count=0,
    )
    session.add(task)
    await session.flush()
    return task, server


async def list_download_targets(
    session: AsyncSession,
    settings: Settings,
) -> list[DownloadTargetResponse]:
    if not settings.mutable_server_names:
        return []
    servers = list(
        await session.scalars(
            select(Server)
            .join(ServerAgent, ServerAgent.server_id == Server.id)
            .where(
                Server.name.in_(settings.mutable_server_names),
                Server.status == "online",
                ServerAgent.token_hash.is_not(None),
                ServerAgent.revoked_at.is_(None),
            )
            .order_by(Server.name)
        )
    )
    targets: list[DownloadTargetResponse] = []
    for server in servers:
        directories = [
            directory
            for directory in await list_model_directories(session, server.id)
            if directory.is_allowed and directory.is_available
        ]
        if directories:
            targets.append(
                DownloadTargetResponse(
                    server=_server_response(server),
                    directories=directories,
                )
            )
    return targets


def _download_query() -> Select[tuple[ModelDownloadTask, Server]]:
    return select(ModelDownloadTask, Server).join(Server, Server.id == ModelDownloadTask.server_id)


async def list_download_tasks(
    session: AsyncSession,
    *,
    server_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[DownloadTaskResponse]:
    query = _download_query()
    if server_id is not None:
        query = query.where(ModelDownloadTask.server_id == server_id)
    if status is not None:
        query = query.where(ModelDownloadTask.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ModelDownloadTask.source_id.ilike(pattern),
                ModelDownloadTask.target_path.ilike(pattern),
                Server.name.ilike(pattern),
            )
        )
    rows = (await session.execute(query.order_by(ModelDownloadTask.created_at.desc()))).all()
    return [download_response(task, server) for task, server in rows]


async def get_download_task(
    session: AsyncSession,
    task_id: uuid.UUID,
) -> tuple[ModelDownloadTask, Server] | None:
    row = (
        await session.execute(_download_query().where(ModelDownloadTask.id == task_id))
    ).one_or_none()
    return None if row is None else (row[0], row[1])


async def cancel_download_task(task: ModelDownloadTask, *, now: datetime | None = None) -> None:
    current = now or utc_now()
    if task.status == "queued":
        task.status = "cancelled"
        task.cancel_requested_at = current
        task.completed_at = current
        return
    if task.status in {"downloading", "cancelling"}:
        task.status = "cancelling"
        task.cancel_requested_at = task.cancel_requested_at or current
        return
    if task.status == "cancelled":
        return
    raise ModelTaskError("download_not_cancellable", "This download cannot be cancelled.")


async def retry_download_task(task: ModelDownloadTask) -> None:
    if task.status not in {"failed", "cancelled"}:
        raise ModelTaskError(
            "download_not_retryable", "Only failed or cancelled downloads can retry."
        )
    task.status = "queued"
    task.downloaded_size = 0
    task.total_size = None
    task.speed_bytes_per_second = None
    task.lease_token_hash = None
    task.lease_expires_at = None
    task.last_progress_at = None
    task.cancel_requested_at = None
    task.error_code = None
    task.error_message = None
    task.started_at = None
    task.completed_at = None


async def create_delete_task(
    session: AsyncSession,
    settings: Settings,
    model_file_id: uuid.UUID,
    confirmation: str,
    user: User,
) -> tuple[ModelDeleteTask, Server]:
    row = (
        await session.execute(
            select(ModelFile, Model, ServerModelDirectory)
            .join(Model, Model.id == ModelFile.model_id)
            .join(
                ServerModelDirectory,
                ServerModelDirectory.id == ModelFile.directory_id,
            )
            .where(ModelFile.id == model_file_id)
        )
    ).one_or_none()
    if row is None:
        raise ModelTaskError(
            "model_installation_not_found", "The model installation does not exist."
        )
    model_file, model, directory = row
    if confirmation != model.source_id:
        raise ModelTaskError(
            "delete_confirmation_mismatch",
            "Type the exact model source ID to confirm deletion.",
        )
    server, selected_directory = await _eligible_target(
        session,
        settings,
        model_file.server_id,
        directory.id,
    )
    if selected_directory.id != model_file.directory_id:
        raise ModelTaskError("model_directory_mismatch", "The model directory no longer matches.")
    deployed = await session.scalar(
        select(Deployment.id).where(Deployment.model_file_id == model_file.id).limit(1)
    )
    if deployed is not None:
        raise ModelTaskError(
            "model_installation_in_use",
            "Stop and delete deployments that use this installation first.",
        )
    active = await session.scalar(
        select(ModelDeleteTask).where(
            ModelDeleteTask.model_file_id == model_file.id,
            ModelDeleteTask.status.in_(ACTIVE_DELETE_STATUSES),
        )
    )
    if active is not None:
        raise ModelTaskError(
            "delete_already_active",
            "A deletion task already exists for this installation.",
        )
    task = ModelDeleteTask(
        model_file_id=model_file.id,
        server_id=server.id,
        directory_id=directory.id,
        requested_by_user_id=user.id,
        source=model.source,
        source_id=model.source_id,
        target_path=model_file.path,
        status="queued",
        attempt_count=0,
    )
    session.add(task)
    await session.flush()
    return task, server


async def get_delete_task(
    session: AsyncSession,
    task_id: uuid.UUID,
) -> tuple[ModelDeleteTask, Server] | None:
    row = (
        await session.execute(
            select(ModelDeleteTask, Server)
            .join(Server, Server.id == ModelDeleteTask.server_id)
            .where(ModelDeleteTask.id == task_id)
        )
    ).one_or_none()
    return None if row is None else (row[0], row[1])


async def _candidate_download(
    session: AsyncSession,
    server_id: uuid.UUID,
    now: datetime,
) -> ModelDownloadTask | None:
    return cast(
        ModelDownloadTask | None,
        await session.scalar(
            select(ModelDownloadTask)
            .where(
                ModelDownloadTask.server_id == server_id,
                or_(
                    ModelDownloadTask.status == "queued",
                    (
                        ModelDownloadTask.status.in_(("downloading", "cancelling"))
                        & (ModelDownloadTask.lease_expires_at < now)
                    ),
                ),
            )
            .order_by(ModelDownloadTask.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        ),
    )


async def _candidate_delete(
    session: AsyncSession,
    server_id: uuid.UUID,
    now: datetime,
) -> ModelDeleteTask | None:
    return cast(
        ModelDeleteTask | None,
        await session.scalar(
            select(ModelDeleteTask)
            .where(
                ModelDeleteTask.server_id == server_id,
                or_(
                    ModelDeleteTask.status == "queued",
                    (
                        (ModelDeleteTask.status == "deleting")
                        & (ModelDeleteTask.lease_expires_at < now)
                    ),
                ),
            )
            .order_by(ModelDeleteTask.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        ),
    )


async def claim_model_task(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> ModelTaskCommand | None:
    current = now or utc_now()
    active_download = await session.scalar(
        select(ModelDownloadTask.id).where(
            ModelDownloadTask.server_id == server_id,
            ModelDownloadTask.status.in_(("downloading", "cancelling")),
            ModelDownloadTask.lease_expires_at >= current,
        )
    )
    active_delete = await session.scalar(
        select(ModelDeleteTask.id).where(
            ModelDeleteTask.server_id == server_id,
            ModelDeleteTask.status == "deleting",
            ModelDeleteTask.lease_expires_at >= current,
        )
    )
    if active_download is not None or active_delete is not None:
        return None

    download = await _candidate_download(session, server_id, current)
    deletion = await _candidate_delete(session, server_id, current)
    candidates: list[tuple[datetime, Literal["download", "delete"], TaskRow]] = []
    if download is not None:
        candidates.append((_aware(download.created_at) or current, "download", download))
    if deletion is not None:
        candidates.append((_aware(deletion.created_at) or current, "delete", deletion))
    if not candidates:
        return None
    _, kind, selected = min(candidates, key=lambda item: item[0])
    directory = (
        await session.get(ServerModelDirectory, selected.directory_id)
        if selected.directory_id is not None
        else None
    )
    if (
        directory is None
        or directory.server_id != server_id
        or not directory.is_allowed
        or not directory.is_available
    ):
        selected.status = "failed"
        selected.error_code = "target_directory_unavailable"
        selected.error_message = "The selected Agent directory is no longer available."
        selected.completed_at = current
        await session.flush()
        return None

    lease_token = secrets.token_urlsafe(32)
    selected.lease_token_hash = _digest_lease(lease_token)
    selected.lease_expires_at = current + timedelta(seconds=settings.model_task_lease_seconds)
    selected.attempt_count += 1
    selected.started_at = selected.started_at or current
    selected.completed_at = None
    if kind == "download":
        task = selected
        assert isinstance(task, ModelDownloadTask)
        task.status = "cancelling" if task.cancel_requested_at is not None else "downloading"
        await session.flush()
        return DownloadTaskCommand(
            task_id=task.id,
            lease_token=lease_token,
            root_path=directory.path,
            provider=task.source,
            source_id=task.source_id,
            revision=task.revision,
            target_path=task.target_path,
            cancel_requested=task.cancel_requested_at is not None,
        )
    task = selected
    assert isinstance(task, ModelDeleteTask)
    task.status = "deleting"
    await session.flush()
    return DeleteTaskCommand(
        task_id=task.id,
        lease_token=lease_token,
        root_path=directory.path,
        model_file_id=task.model_file_id,
        source=task.source,
        source_id=task.source_id,
        target_path=task.target_path,
    )


def _verify_lease(
    task: TaskRow,
    lease_token: str,
    now: datetime,
) -> None:
    if task.lease_token_hash is None or not secrets.compare_digest(
        task.lease_token_hash,
        _digest_lease(lease_token),
    ):
        raise ModelTaskError("invalid_task_lease", "The task lease is invalid.")
    expires_at = _aware(task.lease_expires_at)
    if expires_at is None or expires_at < now:
        raise ModelTaskError("expired_task_lease", "The task lease has expired.")


async def report_download_progress(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    task_id: uuid.UUID,
    report: DownloadProgressRequest,
    *,
    now: datetime | None = None,
) -> DownloadProgressResponse:
    current = now or utc_now()
    task = await session.scalar(
        select(ModelDownloadTask).where(
            ModelDownloadTask.id == task_id,
            ModelDownloadTask.server_id == server_id,
        )
    )
    if task is None:
        raise ModelTaskError("download_task_not_found", "The download task does not exist.")
    if task.status not in {"downloading", "cancelling"}:
        raise ModelTaskError("download_not_active", "The download is not active.")
    _verify_lease(task, report.lease_token, current)
    if report.downloaded_size < task.downloaded_size:
        raise ModelTaskError("download_progress_regressed", "Downloaded bytes cannot decrease.")
    if report.total_size is not None and report.downloaded_size > report.total_size:
        raise ModelTaskError("invalid_download_progress", "Downloaded bytes exceed total bytes.")
    task.downloaded_size = report.downloaded_size
    task.total_size = report.total_size
    task.speed_bytes_per_second = report.speed_bytes_per_second
    task.last_progress_at = current
    task.lease_expires_at = current + timedelta(seconds=settings.model_task_lease_seconds)
    await session.flush()
    return DownloadProgressResponse(
        cancel_requested=task.cancel_requested_at is not None,
        lease_expires_at=task.lease_expires_at,
    )


async def complete_download_task(
    session: AsyncSession,
    server_id: uuid.UUID,
    task_id: uuid.UUID,
    report: DownloadTerminalRequest,
    *,
    now: datetime | None = None,
) -> ModelDownloadTask:
    current = now or utc_now()
    task = await session.scalar(
        select(ModelDownloadTask).where(
            ModelDownloadTask.id == task_id,
            ModelDownloadTask.server_id == server_id,
        )
    )
    if task is None:
        raise ModelTaskError("download_task_not_found", "The download task does not exist.")
    if task.status not in {"downloading", "cancelling"}:
        raise ModelTaskError("download_not_active", "The download is not active.")
    _verify_lease(task, report.lease_token, current)
    if report.outcome == "completed" and report.final_path != task.target_path:
        raise ModelTaskError(
            "download_path_mismatch", "The completed path does not match the task."
        )
    if report.total_size is not None and report.downloaded_size > report.total_size:
        raise ModelTaskError("invalid_download_progress", "Downloaded bytes exceed total bytes.")
    task.status = report.outcome
    task.downloaded_size = report.downloaded_size
    task.total_size = report.total_size
    task.speed_bytes_per_second = 0
    task.last_progress_at = current
    task.completed_at = current
    task.error_code = _safe_error(report.error_code)
    task.error_message = _safe_error(report.error_message)
    task.lease_token_hash = None
    task.lease_expires_at = None
    await session.flush()
    return task


async def complete_delete_task(
    session: AsyncSession,
    server_id: uuid.UUID,
    task_id: uuid.UUID,
    report: DeleteTerminalRequest,
    *,
    now: datetime | None = None,
) -> ModelDeleteTask:
    current = now or utc_now()
    task = await session.scalar(
        select(ModelDeleteTask).where(
            ModelDeleteTask.id == task_id,
            ModelDeleteTask.server_id == server_id,
        )
    )
    if task is None:
        raise ModelTaskError("delete_task_not_found", "The delete task does not exist.")
    if task.status != "deleting":
        raise ModelTaskError("delete_not_active", "The delete task is not active.")
    _verify_lease(task, report.lease_token, current)
    task.status = report.outcome
    task.completed_at = current
    task.error_code = _safe_error(report.error_code)
    task.error_message = _safe_error(report.error_message)
    task.lease_token_hash = None
    task.lease_expires_at = None
    if report.outcome == "completed" and task.model_file_id is not None:
        model_file = await session.get(ModelFile, task.model_file_id)
        if model_file is not None:
            model_file.status = "missing"
    await session.flush()
    return task
