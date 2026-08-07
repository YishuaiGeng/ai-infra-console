import hashlib
import ipaddress
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.core.config import Settings
from ai_infra_api.db.models import (
    GPU,
    Deployment,
    DeploymentGPU,
    DeploymentLog,
    DeploymentOperation,
    GPUMetric,
    Model,
    ModelDeleteTask,
    ModelFile,
    Server,
    ServerAgent,
    ServerMetric,
    ServerModelDirectory,
    User,
)
from ai_infra_api.schemas.deployments import (
    DeploymentCommand,
    DeploymentConfigRequest,
    DeploymentCreateCommand,
    DeploymentCreateRequest,
    DeploymentGPUResponse,
    DeploymentLifecycleCommand,
    DeploymentLogResponse,
    DeploymentModelResponse,
    DeploymentOperationProgressRequest,
    DeploymentOperationProgressResponse,
    DeploymentOperationResponse,
    DeploymentOperationTerminalRequest,
    DeploymentResponse,
    DeploymentRuntimeExpectation,
    DeploymentRuntimeReport,
    DeploymentTargetResponse,
)
from ai_infra_api.schemas.model_inventory import ModelServerResponse

ACTIVE_OPERATION_STATUSES = ("queued", "running")
ALLOCATING_DEPLOYMENT_STATUSES = (
    "queued",
    "starting",
    "running",
    "stopping",
    "restarting",
    "deleting",
    "unknown",
)
SUPPORTED_MODEL_FORMATS = ("safetensors", "pytorch")
ACTION_TRANSITION_STATUS = {
    "create": "starting",
    "start": "starting",
    "stop": "stopping",
    "restart": "restarting",
    "delete": "deleting",
}
FLAG_ARITY = {
    "--enable-prefix-caching": 0,
    "--disable-log-requests": 0,
    "--enforce-eager": 0,
    "--enable-chunked-prefill": 0,
    "--max-num-seqs": 1,
    "--task": 1,
    "--quantization": 1,
    "--tokenizer-mode": 1,
}
CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")


class DeploymentError(ValueError):
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


def _safe_text(value: str | None, *, limit: int = 1_024) -> str | None:
    if not value:
        return None
    return CONTROL_CHARACTERS.sub(" ", value).strip()[:limit] or None


def _lease_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _server_response(server: Server) -> ModelServerResponse:
    return ModelServerResponse(
        id=server.id,
        name=server.name,
        status=server.status,
        type=server.type,
        host=server.host,
        hostname=server.hostname,
    )


def _endpoint(server: Server, port: int) -> str:
    host = (server.host or server.hostname or server.name).strip()
    try:
        if ipaddress.ip_address(host).version == 6:
            host = f"[{host}]"
    except ValueError:
        pass
    return f"http://{host}:{port}/v1"


def container_name_for(deployment_id: uuid.UUID) -> str:
    return f"ai-infra-{deployment_id.hex}"


def validate_extra_arguments(arguments: list[str]) -> list[str]:
    index = 0
    normalized: list[str] = []
    while index < len(arguments):
        flag = arguments[index]
        arity = FLAG_ARITY.get(flag)
        if arity is None:
            raise DeploymentError(
                "unsupported_vllm_argument",
                f"The vLLM option {flag!r} is not allowed.",
            )
        normalized.append(flag)
        if arity:
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
                raise DeploymentError(
                    "invalid_vllm_argument",
                    f"The vLLM option {flag!r} requires one value.",
                )
            normalized.append(arguments[index + 1])
        index += arity + 1
    return normalized


def _runtime_capability(metric: ServerMetric | None) -> tuple[bool, str | None, bool]:
    runtime_info = metric.runtime_info if metric is not None else {}
    runtimes = runtime_info.get("runtimes") if isinstance(runtime_info, dict) else None
    if not isinstance(runtimes, dict):
        return False, None, False
    docker = runtimes.get("docker")
    docker_available = bool(isinstance(docker, dict) and docker.get("available") is True)
    docker_version = docker.get("version") if isinstance(docker, dict) else None
    deployment_enabled = runtimes.get("deployment_enabled") is True
    normalized_version = docker_version if isinstance(docker_version, str) else None
    return docker_available, normalized_version, deployment_enabled


async def _latest_gpu_metrics(
    session: AsyncSession,
    gpus: list[GPU],
) -> dict[uuid.UUID, GPUMetric]:
    if not gpus:
        return {}
    rows = await session.scalars(
        select(GPUMetric)
        .where(GPUMetric.gpu_id.in_([gpu.id for gpu in gpus]))
        .order_by(GPUMetric.gpu_id, GPUMetric.timestamp.desc(), GPUMetric.id.desc())
    )
    latest: dict[uuid.UUID, GPUMetric] = {}
    for metric in rows:
        latest.setdefault(metric.gpu_id, metric)
    return latest


def _gpu_response(gpu: GPU, metric: GPUMetric | None) -> DeploymentGPUResponse:
    return DeploymentGPUResponse(
        id=gpu.id,
        index=gpu.gpu_index,
        uuid=gpu.uuid,
        name=gpu.name,
        status=gpu.status,
        memory_total=gpu.memory_total,
        memory_used=metric.memory_used if metric else None,
        utilization=metric.utilization if metric else None,
    )


def _model_response(model_file: ModelFile, model: Model) -> DeploymentModelResponse:
    return DeploymentModelResponse(
        id=model.id,
        model_file_id=model_file.id,
        source=model.source,
        source_id=model.source_id,
        name=model.name,
        display_name=model.display_name or model.name,
        path=model_file.path,
        format=model_file.format,
        quantization=model_file.quantization,
        revision=model_file.revision,
        size=model_file.size,
    )


def _operation_response(operation: DeploymentOperation) -> DeploymentOperationResponse:
    return DeploymentOperationResponse(
        id=operation.id,
        action=operation.action,
        status=operation.status,
        generation=operation.generation,
        attempt_count=operation.attempt_count,
        error_code=operation.error_code,
        error_message=operation.error_message,
        started_at=operation.started_at,
        completed_at=operation.completed_at,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


async def _current_operation(
    session: AsyncSession,
    deployment_id: uuid.UUID,
) -> DeploymentOperation | None:
    return cast(
        DeploymentOperation | None,
        await session.scalar(
            select(DeploymentOperation)
            .where(DeploymentOperation.deployment_id == deployment_id)
            .order_by(DeploymentOperation.created_at.desc(), DeploymentOperation.id.desc())
            .limit(1)
        ),
    )


async def deployment_response(
    session: AsyncSession,
    deployment: Deployment,
) -> DeploymentResponse:
    row = (
        await session.execute(
            select(ModelFile, Model, Server)
            .join(Model, Model.id == ModelFile.model_id)
            .join(Server, Server.id == deployment.server_id)
            .where(ModelFile.id == deployment.model_file_id)
        )
    ).one()
    model_file, model, server = row
    gpus = list(
        await session.scalars(
            select(GPU)
            .join(DeploymentGPU, DeploymentGPU.gpu_id == GPU.id)
            .where(DeploymentGPU.deployment_id == deployment.id)
            .order_by(GPU.gpu_index)
        )
    )
    metrics = await _latest_gpu_metrics(session, gpus)
    operation = await _current_operation(session, deployment.id)
    started_at = _aware(deployment.started_at)
    uptime_seconds = None
    if deployment.status == "running" and started_at is not None:
        uptime_seconds = max(0, int((utc_now() - started_at).total_seconds()))
    return DeploymentResponse(
        id=deployment.id,
        name=deployment.name,
        model=_model_response(model_file, model),
        server=_server_response(server),
        gpus=[_gpu_response(gpu, metrics.get(gpu.id)) for gpu in gpus],
        backend="vllm",
        selection_mode=deployment.selection_mode,
        desired_state=deployment.desired_state,
        status=deployment.status,
        generation=deployment.generation,
        port=deployment.port,
        endpoint=deployment.endpoint or _endpoint(server, deployment.port),
        config=DeploymentConfigRequest.model_validate(deployment.config),
        health_status=deployment.health_status,
        health_latency_ms=deployment.health_latency_ms,
        last_health_checked_at=deployment.last_health_checked_at,
        last_reconciled_at=deployment.last_reconciled_at,
        uptime_seconds=uptime_seconds,
        error_code=deployment.error_code,
        error_message=deployment.error_message,
        current_operation=_operation_response(operation) if operation else None,
        started_at=deployment.started_at,
        stopped_at=deployment.stopped_at,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
    )


async def list_deployments(
    session: AsyncSession,
    *,
    server_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[DeploymentResponse]:
    query = select(Deployment).order_by(Deployment.created_at.desc(), Deployment.id.desc())
    if server_id is not None:
        query = query.where(Deployment.server_id == server_id)
    if status is not None:
        query = query.where(Deployment.status == status)
    if search:
        query = query.where(Deployment.name.ilike(f"%{search.strip()}%"))
    rows = list(await session.scalars(query))
    return [await deployment_response(session, deployment) for deployment in rows]


async def get_deployment(
    session: AsyncSession,
    deployment_id: uuid.UUID,
) -> Deployment | None:
    return await session.get(Deployment, deployment_id)


async def _eligible_server(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
) -> tuple[Server, ServerMetric]:
    server = await session.get(Server, server_id)
    if server is None:
        raise DeploymentError("server_not_found", "The deployment server does not exist.")
    if server.name not in settings.mutable_server_names:
        raise DeploymentError(
            "server_deployment_not_allowed",
            "Deployment mutations are disabled for this server.",
        )
    if server.status != "online":
        raise DeploymentError("server_offline", "The deployment server is not online.")
    agent = await session.scalar(
        select(ServerAgent).where(
            ServerAgent.server_id == server.id,
            ServerAgent.token_hash.is_not(None),
            ServerAgent.revoked_at.is_(None),
        )
    )
    if agent is None:
        raise DeploymentError("agent_unavailable", "The server has no active Agent.")
    metric = await session.scalar(select(ServerMetric).where(ServerMetric.server_id == server.id))
    docker_available, _, deployment_enabled = _runtime_capability(metric)
    if metric is None or not docker_available:
        raise DeploymentError("docker_unavailable", "Docker is not available on this server.")
    if not deployment_enabled:
        raise DeploymentError(
            "agent_deployment_disabled",
            "The Agent has not opted in to deployment mutations.",
        )
    return server, metric


async def _active_gpu_allocations(
    session: AsyncSession,
    server_id: uuid.UUID,
    *,
    exclude_deployment_id: uuid.UUID | None = None,
) -> set[uuid.UUID]:
    query = (
        select(DeploymentGPU.gpu_id)
        .join(Deployment, Deployment.id == DeploymentGPU.deployment_id)
        .where(
            Deployment.server_id == server_id,
            Deployment.status.in_(ALLOCATING_DEPLOYMENT_STATUSES),
        )
    )
    if exclude_deployment_id is not None:
        query = query.where(Deployment.id != exclude_deployment_id)
    return set(await session.scalars(query))


async def _plan_gpus(
    session: AsyncSession,
    settings: Settings,
    server: Server,
    request: DeploymentCreateRequest,
) -> list[GPU]:
    gpus = list(
        await session.scalars(
            select(GPU).where(GPU.server_id == server.id).order_by(GPU.gpu_index)
        )
    )
    if not gpus:
        raise DeploymentError("gpu_unavailable", "The server has no reported GPUs.")
    metrics = await _latest_gpu_metrics(session, gpus)
    cutoff = utc_now() - timedelta(seconds=settings.deployment_telemetry_fresh_seconds)
    allocated = await _active_gpu_allocations(session, server.id)

    def selectable(gpu: GPU) -> bool:
        metric = metrics.get(gpu.id)
        timestamp = _aware(metric.timestamp) if metric else None
        return (
            gpu.id not in allocated
            and gpu.status not in {"offline", "unavailable"}
            and timestamp is not None
            and timestamp >= cutoff
        )

    if request.selection_mode == "manual":
        by_id = {gpu.id: gpu for gpu in gpus}
        selected: list[GPU] = []
        for gpu_id in request.gpu_ids:
            gpu = by_id.get(gpu_id)
            if gpu is None:
                raise DeploymentError(
                    "gpu_server_mismatch",
                    "Every selected GPU must belong to the model server.",
                )
            if not selectable(gpu):
                raise DeploymentError("gpu_unavailable", "A selected GPU is stale or allocated.")
            selected.append(gpu)
        return selected

    candidates = [gpu for gpu in gpus if selectable(gpu)]
    candidates.sort(
        key=lambda gpu: (
            -(
                gpu.memory_total
                - ((metrics[gpu.id].memory_used or 0) if gpu.id in metrics else gpu.memory_total)
            ),
            metrics[gpu.id].utilization if metrics[gpu.id].utilization is not None else 101,
            gpu.gpu_index,
        )
    )
    count = request.config.tensor_parallel_size
    if len(candidates) < count:
        raise DeploymentError(
            "insufficient_gpus",
            "The server does not have enough fresh unallocated GPUs.",
        )
    return candidates[:count]


async def list_deployment_targets(
    session: AsyncSession,
    settings: Settings,
) -> list[DeploymentTargetResponse]:
    if not settings.mutable_server_names:
        return []
    rows = (
        await session.execute(
            select(Server, ServerMetric)
            .join(ServerMetric, ServerMetric.server_id == Server.id)
            .join(ServerAgent, ServerAgent.server_id == Server.id)
            .where(
                Server.name.in_(settings.mutable_server_names),
                Server.status == "online",
                ServerAgent.token_hash.is_not(None),
                ServerAgent.revoked_at.is_(None),
            )
            .order_by(Server.name)
        )
    ).all()
    targets: list[DeploymentTargetResponse] = []
    for server, metric in rows:
        docker_available, docker_version, deployment_enabled = _runtime_capability(metric)
        if not docker_available or not deployment_enabled:
            continue
        model_rows = (
            await session.execute(
                select(ModelFile, Model)
                .join(Model, Model.id == ModelFile.model_id)
                .join(
                    ServerModelDirectory,
                    ServerModelDirectory.id == ModelFile.directory_id,
                )
                .where(
                    ModelFile.server_id == server.id,
                    ModelFile.status == "discovered",
                    ModelFile.format.in_(SUPPORTED_MODEL_FORMATS),
                    ServerModelDirectory.is_allowed.is_(True),
                    ServerModelDirectory.is_available.is_(True),
                )
                .order_by(Model.name, ModelFile.path)
            )
        ).all()
        gpus = list(
            await session.scalars(
                select(GPU).where(GPU.server_id == server.id).order_by(GPU.gpu_index)
            )
        )
        metrics = await _latest_gpu_metrics(session, gpus)
        if model_rows and gpus:
            targets.append(
                DeploymentTargetResponse(
                    server=_server_response(server),
                    docker_available=True,
                    docker_version=docker_version,
                    model_files=[
                        _model_response(model_file, model)
                        for model_file, model in model_rows
                    ],
                    gpus=[_gpu_response(gpu, metrics.get(gpu.id)) for gpu in gpus],
                )
            )
    return targets


async def create_deployment(
    session: AsyncSession,
    settings: Settings,
    request: DeploymentCreateRequest,
    user: User,
    *,
    request_id: str | None = None,
) -> tuple[Deployment, DeploymentOperation]:
    validate_extra_arguments(request.config.extra_arguments)
    row = (
        await session.execute(
            select(ModelFile, Model, ServerModelDirectory)
            .join(Model, Model.id == ModelFile.model_id)
            .join(ServerModelDirectory, ServerModelDirectory.id == ModelFile.directory_id)
            .where(ModelFile.id == request.model_file_id)
        )
    ).one_or_none()
    if row is None:
        raise DeploymentError("model_file_not_found", "The model installation does not exist.")
    model_file, _model, directory = row
    if model_file.status != "discovered":
        raise DeploymentError("model_file_unavailable", "The model installation is not available.")
    if model_file.format not in SUPPORTED_MODEL_FORMATS:
        raise DeploymentError(
            "unsupported_model_format",
            "This model format is not supported by vLLM.",
        )
    if not directory.is_allowed or not directory.is_available:
        raise DeploymentError("model_directory_unavailable", "The model directory is unavailable.")
    active_delete = await session.scalar(
        select(ModelDeleteTask.id).where(
            ModelDeleteTask.model_file_id == model_file.id,
            ModelDeleteTask.status.in_(("queued", "deleting")),
        )
    )
    if active_delete is not None:
        raise DeploymentError("model_deletion_active", "The model installation is being deleted.")
    server, _metric = await _eligible_server(session, settings, model_file.server_id)
    duplicate_name = await session.scalar(
        select(Deployment.id).where(Deployment.name == request.name)
    )
    if duplicate_name is not None:
        raise DeploymentError("deployment_name_conflict", "A deployment already uses this name.")
    port_conflict = await session.scalar(
        select(Deployment.id).where(
            Deployment.server_id == server.id,
            Deployment.port == request.port,
        )
    )
    if port_conflict is not None:
        raise DeploymentError("deployment_port_conflict", "The server port is already reserved.")
    selected_gpus = await _plan_gpus(session, settings, server, request)
    deployment = Deployment(
        name=request.name,
        model_file_id=model_file.id,
        server_id=server.id,
        requested_by_user_id=user.id,
        backend="vllm",
        selection_mode=request.selection_mode,
        desired_state="running",
        status="queued",
        generation=1,
        port=request.port,
        endpoint=_endpoint(server, request.port),
        config=request.config.model_dump(mode="json"),
        health_status="unknown",
    )
    session.add(deployment)
    await session.flush()
    for gpu in selected_gpus:
        session.add(DeploymentGPU(deployment_id=deployment.id, gpu_id=gpu.id))
    operation = DeploymentOperation(
        deployment_id=deployment.id,
        server_id=server.id,
        requested_by_user_id=user.id,
        action="create",
        status="queued",
        generation=deployment.generation,
        attempt_count=0,
        request_id=request_id,
    )
    session.add(operation)
    await session.flush()
    return deployment, operation


async def queue_deployment_action(
    session: AsyncSession,
    deployment: Deployment,
    action: str,
    user: User,
    *,
    request_id: str | None = None,
) -> DeploymentOperation:
    if action not in {"start", "stop", "restart", "delete"}:
        raise DeploymentError("invalid_deployment_action", "The lifecycle action is invalid.")
    active = await session.scalar(
        select(DeploymentOperation)
        .where(
            DeploymentOperation.deployment_id == deployment.id,
            DeploymentOperation.status.in_(ACTIVE_OPERATION_STATUSES),
        )
        .order_by(DeploymentOperation.created_at.desc())
        .limit(1)
    )
    if active is not None:
        if active.action == action:
            return active
        raise DeploymentError(
            "deployment_operation_conflict",
            "Another lifecycle operation is already active.",
        )
    if action == "start" and deployment.status in {"running", "starting"}:
        previous = await _current_operation(session, deployment.id)
        if previous is not None:
            return previous
    if action == "stop" and deployment.status in {"stopped", "stopping"}:
        previous = await _current_operation(session, deployment.id)
        if previous is not None:
            return previous
    if action == "restart" and deployment.status != "running":
        raise DeploymentError(
            "deployment_not_running",
            "Only a running deployment can be restarted.",
        )
    deployment.desired_state = {
        "start": "running",
        "stop": "stopped",
        "restart": "running",
        "delete": "deleted",
    }[action]
    deployment.error_code = None
    deployment.error_message = None
    operation = DeploymentOperation(
        deployment_id=deployment.id,
        server_id=deployment.server_id,
        requested_by_user_id=user.id,
        action=action,
        status="queued",
        generation=deployment.generation,
        attempt_count=0,
        request_id=request_id,
    )
    session.add(operation)
    await session.flush()
    return operation


async def validate_deployment_action_target(
    session: AsyncSession,
    settings: Settings,
    deployment: Deployment,
    action: str,
) -> None:
    await _eligible_server(session, settings, deployment.server_id)
    if action not in {"start", "restart"}:
        return
    selected = set(
        await session.scalars(
            select(DeploymentGPU.gpu_id).where(
                DeploymentGPU.deployment_id == deployment.id
            )
        )
    )
    allocated = await _active_gpu_allocations(
        session,
        deployment.server_id,
        exclude_deployment_id=deployment.id,
    )
    if selected & allocated:
        raise DeploymentError(
            "deployment_gpu_conflict",
            "A selected GPU is allocated to another active deployment.",
        )


async def retry_deployment(
    session: AsyncSession,
    deployment: Deployment,
    user: User,
    *,
    request_id: str | None = None,
) -> DeploymentOperation:
    if deployment.status != "failed":
        raise DeploymentError("deployment_not_retryable", "Only failed deployments can retry.")
    previous = await _current_operation(session, deployment.id)
    if previous is None or previous.status != "failed":
        raise DeploymentError("deployment_not_retryable", "No failed operation can be retried.")
    action = previous.action
    if action == "create":
        deployment.status = "queued"
        deployment.desired_state = "running"
        deployment.error_code = None
        deployment.error_message = None
        operation = DeploymentOperation(
            deployment_id=deployment.id,
            server_id=deployment.server_id,
            requested_by_user_id=user.id,
            action="create",
            status="queued",
            generation=deployment.generation,
            attempt_count=0,
            request_id=request_id,
        )
        session.add(operation)
        await session.flush()
        return operation
    return await queue_deployment_action(
        session,
        deployment,
        action,
        user,
        request_id=request_id,
    )


async def claim_deployment_operation(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> DeploymentCommand | None:
    current = now or utc_now()
    active = await session.scalar(
        select(DeploymentOperation.id).where(
            DeploymentOperation.server_id == server_id,
            DeploymentOperation.status == "running",
            DeploymentOperation.lease_expires_at >= current,
        )
    )
    if active is not None:
        return None
    operation = await session.scalar(
        select(DeploymentOperation)
        .where(
            DeploymentOperation.server_id == server_id,
            or_(
                DeploymentOperation.status == "queued",
                (
                    (DeploymentOperation.status == "running")
                    & (DeploymentOperation.lease_expires_at < current)
                ),
            ),
        )
        .order_by(DeploymentOperation.created_at, DeploymentOperation.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if operation is None:
        return None
    deployment = await session.get(Deployment, operation.deployment_id)
    if deployment is None or deployment.server_id != server_id:
        operation.status = "failed"
        operation.error_code = "deployment_missing"
        operation.error_message = "The deployment no longer exists."
        operation.completed_at = current
        await session.flush()
        return None
    if operation.generation != deployment.generation:
        operation.status = "failed"
        operation.error_code = "stale_deployment_generation"
        operation.error_message = "The operation belongs to an older deployment generation."
        operation.completed_at = current
        await session.flush()
        return None
    lease_token = secrets.token_urlsafe(32)
    operation.status = "running"
    operation.attempt_count += 1
    operation.lease_token_hash = _lease_digest(lease_token)
    operation.lease_expires_at = current + timedelta(seconds=settings.deployment_task_lease_seconds)
    operation.started_at = operation.started_at or current
    operation.completed_at = None
    deployment.status = ACTION_TRANSITION_STATUS[operation.action]
    deployment.health_status = "unknown"
    await session.flush()
    if operation.action != "create":
        return DeploymentLifecycleCommand(
            kind=operation.action,
            operation_id=operation.id,
            deployment_id=deployment.id,
            generation=deployment.generation,
            lease_token=lease_token,
            container_name=container_name_for(deployment.id),
        )
    model_row = (
        await session.execute(
            select(ModelFile, Model, ServerModelDirectory)
            .join(Model, Model.id == ModelFile.model_id)
            .join(ServerModelDirectory, ServerModelDirectory.id == ModelFile.directory_id)
            .where(ModelFile.id == deployment.model_file_id)
        )
    ).one_or_none()
    if model_row is None:
        raise DeploymentError("model_file_not_found", "The deployment model no longer exists.")
    model_file, model, directory = model_row
    gpus = list(
        await session.scalars(
            select(GPU)
            .join(DeploymentGPU, DeploymentGPU.gpu_id == GPU.id)
            .where(DeploymentGPU.deployment_id == deployment.id)
            .order_by(GPU.gpu_index)
        )
    )
    return DeploymentCreateCommand(
        operation_id=operation.id,
        deployment_id=deployment.id,
        generation=deployment.generation,
        lease_token=lease_token,
        container_name=container_name_for(deployment.id),
        image=settings.vllm_image,
        root_path=directory.path,
        model_file_id=model_file.id,
        source=model.source,
        source_id=model.source_id,
        model_path=model_file.path,
        port=deployment.port,
        gpu_indexes=[gpu.gpu_index for gpu in gpus],
        gpu_uuids=[gpu.uuid for gpu in gpus],
        config=DeploymentConfigRequest.model_validate(deployment.config),
    )


def _verify_operation_lease(
    operation: DeploymentOperation,
    lease_token: str,
    generation: int,
    now: datetime,
) -> None:
    if operation.generation != generation:
        raise DeploymentError(
            "stale_deployment_generation",
            "The operation belongs to an older deployment generation.",
        )
    if operation.lease_token_hash is None or not secrets.compare_digest(
        operation.lease_token_hash,
        _lease_digest(lease_token),
    ):
        raise DeploymentError("invalid_deployment_lease", "The deployment lease is invalid.")
    expires_at = _aware(operation.lease_expires_at)
    if expires_at is None or expires_at < now:
        raise DeploymentError("expired_deployment_lease", "The deployment lease has expired.")


async def renew_deployment_operation(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    operation_id: uuid.UUID,
    report: DeploymentOperationProgressRequest,
    *,
    now: datetime | None = None,
) -> DeploymentOperationProgressResponse:
    current = now or utc_now()
    operation = await session.scalar(
        select(DeploymentOperation).where(
            DeploymentOperation.id == operation_id,
            DeploymentOperation.server_id == server_id,
        )
    )
    if operation is None:
        raise DeploymentError("deployment_operation_not_found", "The operation does not exist.")
    if operation.status != "running":
        raise DeploymentError("deployment_operation_not_active", "The operation is not active.")
    _verify_operation_lease(operation, report.lease_token, report.generation, current)
    operation.lease_expires_at = current + timedelta(seconds=settings.deployment_task_lease_seconds)
    await session.flush()
    return DeploymentOperationProgressResponse(lease_expires_at=operation.lease_expires_at)


async def complete_deployment_operation(
    session: AsyncSession,
    server_id: uuid.UUID,
    operation_id: uuid.UUID,
    report: DeploymentOperationTerminalRequest,
    *,
    now: datetime | None = None,
) -> tuple[uuid.UUID, uuid.UUID, bool]:
    current = now or utc_now()
    operation = await session.scalar(
        select(DeploymentOperation).where(
            DeploymentOperation.id == operation_id,
            DeploymentOperation.server_id == server_id,
        )
    )
    if operation is None:
        raise DeploymentError("deployment_operation_not_found", "The operation does not exist.")
    if operation.status != "running":
        raise DeploymentError("deployment_operation_not_active", "The operation is not active.")
    _verify_operation_lease(operation, report.lease_token, report.generation, current)
    deployment = await session.get(Deployment, operation.deployment_id)
    if deployment is None or deployment.generation != report.generation:
        raise DeploymentError("deployment_not_found", "The deployment no longer exists.")
    operation.status = report.outcome
    operation.completed_at = current
    operation.error_code = _safe_text(report.error_code, limit=64)
    operation.error_message = _safe_text(report.error_message)
    operation.lease_token_hash = None
    operation.lease_expires_at = None
    deleted = False
    if report.outcome == "failed":
        deployment.status = "failed"
        deployment.health_status = "unhealthy" if report.observed_state == "failed" else "unknown"
        deployment.error_code = operation.error_code or "deployment_operation_failed"
        deployment.error_message = (
            operation.error_message or "The Agent deployment operation failed."
        )
    elif operation.action == "delete":
        await session.delete(deployment)
        deleted = True
    elif operation.action == "stop":
        deployment.status = "stopped"
        deployment.health_status = "unknown"
        deployment.stopped_at = current
        deployment.last_reconciled_at = current
    else:
        if report.observed_state != "running":
            raise DeploymentError(
                "deployment_state_mismatch",
                "A successful start must report a running container.",
            )
        deployment.status = "running"
        deployment.desired_state = "running"
        deployment.health_status = "unknown"
        deployment.container_id = _safe_text(report.container_id, limit=128)
        deployment.started_at = current
        deployment.stopped_at = None
        deployment.last_reconciled_at = current
        deployment.error_code = None
        deployment.error_message = None
    await session.flush()
    return server_id, operation.deployment_id, deleted


async def apply_runtime_report(
    session: AsyncSession,
    settings: Settings,
    server_id: uuid.UUID,
    report: DeploymentRuntimeReport,
) -> tuple[set[uuid.UUID], bool]:
    changed: set[uuid.UUID] = set()
    logs_changed = False
    for observation in report.observations:
        deployment = await session.scalar(
            select(Deployment).where(
                Deployment.id == observation.deployment_id,
                Deployment.server_id == server_id,
            )
        )
        if deployment is None or deployment.generation != observation.generation:
            continue
        active_operation = await session.scalar(
            select(DeploymentOperation.id).where(
                DeploymentOperation.deployment_id == deployment.id,
                DeploymentOperation.status.in_(ACTIVE_OPERATION_STATUSES),
            )
        )
        if active_operation is None:
            mapped = {
                "running": "running",
                "stopped": "stopped",
                "missing": "failed" if deployment.desired_state == "running" else "stopped",
                "failed": "failed",
            }[observation.state]
            if deployment.status != mapped:
                deployment.status = mapped
                changed.add(deployment.id)
            if observation.state == "missing" and deployment.desired_state == "running":
                deployment.error_code = "runtime_missing"
                deployment.error_message = "The Agent cannot find the managed container."
            elif observation.state == "failed":
                deployment.error_code = "runtime_exited"
                deployment.error_message = (
                    f"The managed container exited with code {observation.exit_code}."
                    if observation.exit_code is not None
                    else "The managed container exited."
                )
        deployment.container_id = _safe_text(observation.container_id, limit=128)
        deployment.health_status = observation.health_status
        deployment.health_latency_ms = observation.health_latency_ms
        deployment.last_health_checked_at = observation.checked_at
        deployment.last_reconciled_at = observation.checked_at
        changed.add(deployment.id)
        for entry in observation.logs:
            exists = await session.scalar(
                select(DeploymentLog.id).where(
                    DeploymentLog.deployment_id == deployment.id,
                    DeploymentLog.sequence == entry.sequence,
                )
            )
            message = _safe_text(entry.message, limit=4_096)
            if exists is None and message:
                session.add(
                    DeploymentLog(
                        deployment_id=deployment.id,
                        sequence=entry.sequence,
                        timestamp=entry.timestamp,
                        stream=entry.stream,
                        message=message,
                    )
                )
                logs_changed = True
        await session.flush()
        if observation.logs:
            stale_ids = list(
                await session.scalars(
                    select(DeploymentLog.id)
                    .where(DeploymentLog.deployment_id == deployment.id)
                    .order_by(DeploymentLog.sequence.desc())
                    .offset(settings.deployment_log_retention_lines)
                )
            )
            if stale_ids:
                await session.execute(delete(DeploymentLog).where(DeploymentLog.id.in_(stale_ids)))
    await session.flush()
    return changed, logs_changed


async def list_runtime_expectations(
    session: AsyncSession,
    server_id: uuid.UUID,
) -> list[DeploymentRuntimeExpectation]:
    deployments = list(
        await session.scalars(
            select(Deployment)
            .where(
                Deployment.server_id == server_id,
                Deployment.desired_state.in_(("running", "stopped")),
            )
            .order_by(Deployment.created_at, Deployment.id)
        )
    )
    return [
        DeploymentRuntimeExpectation(
            deployment_id=deployment.id,
            generation=deployment.generation,
            container_name=container_name_for(deployment.id),
            port=deployment.port,
            desired_state=deployment.desired_state,
        )
        for deployment in deployments
    ]


async def list_deployment_logs(
    session: AsyncSession,
    deployment_id: uuid.UUID,
    *,
    after: int = 0,
    limit: int = 200,
    search: str | None = None,
) -> list[DeploymentLogResponse]:
    exists = await session.get(Deployment, deployment_id)
    if exists is None:
        raise DeploymentError("deployment_not_found", "The deployment does not exist.")
    query = select(DeploymentLog).where(
        DeploymentLog.deployment_id == deployment_id,
        DeploymentLog.sequence > after,
    )
    if search:
        query = query.where(DeploymentLog.message.ilike(f"%{search.strip()}%"))
    rows = list(
        await session.scalars(query.order_by(DeploymentLog.sequence).limit(limit))
    )
    return [
        DeploymentLogResponse(
            sequence=row.sequence,
            timestamp=row.timestamp,
            stream=row.stream,
            message=row.message,
        )
        for row in rows
    ]
