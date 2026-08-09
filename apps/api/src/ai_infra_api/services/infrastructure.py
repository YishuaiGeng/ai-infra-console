import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import (
    GPU,
    Deployment,
    DeploymentGPU,
    GPUMetric,
    GPUProcess,
    ModelFile,
    Server,
    ServerMetric,
)
from ai_infra_api.schemas.infrastructure import (
    GPUProcessResponse,
    GPUResponse,
    InfrastructureSummaryResponse,
    RuntimeAvailabilityResponse,
    ServerDetailResponse,
    ServerMetricResponse,
    ServerReferenceResponse,
    ServerSummaryResponse,
)
from ai_infra_api.services.agent_telemetry import mark_stale_servers_offline
from ai_infra_api.services.model_reads import (
    list_model_directories,
    list_model_installations,
)


def _runtime_availability(value: object) -> RuntimeAvailabilityResponse | None:
    if not isinstance(value, dict) or not isinstance(value.get("available"), bool):
        return None
    version = value.get("version")
    return RuntimeAvailabilityResponse(
        available=value["available"],
        version=version if isinstance(version, str) else None,
    )


def _server_metric(metric: ServerMetric | None) -> ServerMetricResponse | None:
    if metric is None:
        return None
    runtime_info: dict[str, Any] = metric.runtime_info or {}
    raw_runtimes = runtime_info.get("runtimes")
    runtimes: dict[str, RuntimeAvailabilityResponse] = {}
    if isinstance(raw_runtimes, dict):
        for name, value in raw_runtimes.items():
            normalized = _runtime_availability(value)
            if isinstance(name, str) and normalized is not None:
                runtimes[name] = normalized
    architecture = runtime_info.get("architecture")
    return ServerMetricResponse(
        collected_at=metric.collected_at,
        uptime_seconds=metric.uptime_seconds,
        cpu_utilization=metric.cpu_utilization,
        memory_used=metric.memory_used,
        memory_total=metric.memory_total,
        disk_used=metric.disk_used,
        disk_total=metric.disk_total,
        network_bytes_sent=metric.network_bytes_sent,
        network_bytes_received=metric.network_bytes_received,
        architecture=architecture if isinstance(architecture, str) else None,
        runtimes=runtimes,
    )


def _gpu_status(
    server: Server,
    gpu: GPU,
    metric: GPUMetric | None,
    processes: list[GPUProcess],
) -> Literal["available", "active", "high-load", "memory-full", "unavailable"]:
    if server.status != "online" or gpu.status in {"offline", "unavailable"}:
        return "unavailable"
    if processes:
        return "active"
    if metric is not None and metric.utilization is not None and metric.utilization >= 90:
        return "high-load"
    if (
        metric is not None
        and metric.memory_used is not None
        and gpu.memory_total > 0
        and metric.memory_used / gpu.memory_total >= 0.95
    ):
        return "memory-full"
    return "available"


async def _load_rows(
    session: AsyncSession,
    *,
    server_id: uuid.UUID | None = None,
) -> tuple[
    list[Server],
    dict[uuid.UUID, ServerMetric],
    list[GPU],
    dict[uuid.UUID, GPUMetric],
    dict[uuid.UUID, list[GPUProcess]],
]:
    server_query = select(Server).order_by(Server.name)
    metric_query = select(ServerMetric)
    gpu_query = select(GPU).order_by(GPU.server_id, GPU.gpu_index)
    if server_id is not None:
        server_query = server_query.where(Server.id == server_id)
        metric_query = metric_query.where(ServerMetric.server_id == server_id)
        gpu_query = gpu_query.where(GPU.server_id == server_id)

    servers = list(await session.scalars(server_query))
    metrics = {item.server_id: item for item in await session.scalars(metric_query)}
    gpus = list(await session.scalars(gpu_query))
    gpu_ids = [gpu.id for gpu in gpus]
    if not gpu_ids:
        return servers, metrics, gpus, {}, {}

    latest_metrics: dict[uuid.UUID, GPUMetric] = {}
    metric_rows = await session.scalars(
        select(GPUMetric)
        .where(GPUMetric.gpu_id.in_(gpu_ids))
        .order_by(GPUMetric.gpu_id, GPUMetric.timestamp.desc(), GPUMetric.id.desc())
    )
    for metric in metric_rows:
        latest_metrics.setdefault(metric.gpu_id, metric)

    processes: dict[uuid.UUID, list[GPUProcess]] = defaultdict(list)
    process_rows = await session.scalars(
        select(GPUProcess)
        .where(GPUProcess.gpu_id.in_(gpu_ids))
        .order_by(GPUProcess.gpu_id, GPUProcess.pid)
    )
    for process in process_rows:
        processes[process.gpu_id].append(process)
    return servers, metrics, gpus, latest_metrics, dict(processes)


def _server_reference(server: Server) -> ServerReferenceResponse:
    return ServerReferenceResponse(
        id=server.id,
        name=server.name,
        type=server.type,
        status=server.status,
        host=server.host,
        hostname=server.hostname,
    )


def _gpu_response(
    server: Server,
    gpu: GPU,
    metric: GPUMetric | None,
    processes: list[GPUProcess],
    allocation: tuple[uuid.UUID, str] | None = None,
) -> GPUResponse:
    gpu_status = _gpu_status(server, gpu, metric, processes)
    if allocation is not None and gpu_status == "available":
        gpu_status = "active"
    return GPUResponse(
        id=gpu.id,
        server=_server_reference(server),
        index=gpu.gpu_index,
        uuid=gpu.uuid,
        vendor=gpu.vendor,
        name=gpu.name,
        status=gpu_status,
        utilization=metric.utilization if metric else None,
        memory_used=metric.memory_used if metric else None,
        memory_total=gpu.memory_total,
        temperature=metric.temperature if metric else None,
        power_usage=metric.power_usage if metric else None,
        power_limit=metric.power_limit if metric else None,
        fan_speed=metric.fan_speed if metric else None,
        driver_version=gpu.driver_version,
        cuda_version=gpu.cuda_version,
        metric_collected_at=metric.timestamp if metric else None,
        process_count=len(processes),
        deployment_id=allocation[0] if allocation else None,
        deployment_name=allocation[1] if allocation else None,
    )


def _process_response(gpu: GPU, process: GPUProcess) -> GPUProcessResponse:
    return GPUProcessResponse(
        id=process.id,
        gpu_id=gpu.id,
        gpu_index=gpu.gpu_index,
        gpu_name=gpu.name,
        pid=process.pid,
        username=process.username,
        command=process.command,
        memory_used=process.memory_used,
        collected_at=process.collected_at,
    )


def _summary_response(
    server: Server,
    metric: ServerMetric | None,
    gpus: list[GPUResponse],
    model_count: int,
) -> ServerSummaryResponse:
    return ServerSummaryResponse(
        id=server.id,
        name=server.name,
        status=server.status,
        type=server.type,
        provider=server.provider,
        host=server.host,
        hostname=server.hostname,
        description=server.description,
        tags=server.tags or [],
        os=server.os,
        kernel=server.kernel,
        cpu_model=server.cpu_model,
        cpu_cores=server.cpu_cores,
        memory_total=server.memory_total,
        disk_total=server.disk_total,
        agent_version=server.agent_version,
        last_seen=server.last_seen,
        created_at=server.created_at,
        updated_at=server.updated_at,
        metric=_server_metric(metric),
        gpu_count=len(gpus),
        available_gpu_count=sum(item.status == "available" for item in gpus),
        gpu_memory_total=sum(item.memory_total for item in gpus),
        gpu_models=sorted({item.name for item in gpus}),
        model_count=model_count,
    )


async def _model_counts(session: AsyncSession) -> dict[uuid.UUID, int]:
    rows = (
        await session.execute(
            select(ModelFile.server_id, func.count(ModelFile.id))
            .where(ModelFile.status == "discovered")
            .group_by(ModelFile.server_id)
        )
    ).all()
    return {server_id: int(count) for server_id, count in rows}


async def _deployment_allocations(
    session: AsyncSession,
) -> dict[uuid.UUID, tuple[uuid.UUID, str]]:
    rows = (
        await session.execute(
            select(DeploymentGPU.gpu_id, Deployment.id, Deployment.name)
            .join(Deployment, Deployment.id == DeploymentGPU.deployment_id)
            .where(
                Deployment.status.in_(
                    ("queued", "starting", "running", "stopping", "restarting", "deleting")
                )
            )
            .order_by(DeploymentGPU.gpu_id, Deployment.created_at, Deployment.id)
        )
    ).all()
    allocations: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
    for gpu_id, deployment_id, deployment_name in rows:
        allocations.setdefault(gpu_id, (deployment_id, deployment_name))
    return allocations


async def list_server_summaries(
    session: AsyncSession,
    *,
    offline_seconds: int,
) -> list[ServerSummaryResponse]:
    await mark_stale_servers_offline(session, threshold_seconds=offline_seconds)
    servers, metrics, gpus, gpu_metrics, processes = await _load_rows(session)
    model_counts = await _model_counts(session)
    allocations = await _deployment_allocations(session)
    servers_by_id = {server.id: server for server in servers}
    responses_by_server: dict[uuid.UUID, list[GPUResponse]] = defaultdict(list)
    for gpu in gpus:
        server = servers_by_id[gpu.server_id]
        responses_by_server[gpu.server_id].append(
            _gpu_response(
                server,
                gpu,
                gpu_metrics.get(gpu.id),
                processes.get(gpu.id, []),
                allocations.get(gpu.id),
            )
        )
    return [
        _summary_response(
            server,
            metrics.get(server.id),
            responses_by_server[server.id],
            model_counts.get(server.id, 0),
        )
        for server in servers
    ]


async def get_server_detail(
    session: AsyncSession,
    server_id: uuid.UUID,
    *,
    offline_seconds: int,
) -> ServerDetailResponse | None:
    await mark_stale_servers_offline(session, threshold_seconds=offline_seconds)
    servers, metrics, gpus, gpu_metrics, processes = await _load_rows(session, server_id=server_id)
    if not servers:
        return None
    server = servers[0]
    allocations = await _deployment_allocations(session)
    gpu_responses = [
        _gpu_response(
            server,
            gpu,
            gpu_metrics.get(gpu.id),
            processes.get(gpu.id, []),
            allocations.get(gpu.id),
        )
        for gpu in gpus
    ]
    process_responses = [
        _process_response(gpu, process) for gpu in gpus for process in processes.get(gpu.id, [])
    ]
    model_counts = await _model_counts(session)
    model_installations = await list_model_installations(session, server_id=server.id)
    model_directories = await list_model_directories(session, server.id)
    summary = _summary_response(
        server,
        metrics.get(server.id),
        gpu_responses,
        model_counts.get(server.id, 0),
    )
    return ServerDetailResponse(
        **summary.model_dump(),
        gpus=gpu_responses,
        processes=process_responses,
        models=model_installations,
        model_directories=model_directories,
    )


async def list_gpus(
    session: AsyncSession,
    *,
    offline_seconds: int,
) -> list[GPUResponse]:
    await mark_stale_servers_offline(session, threshold_seconds=offline_seconds)
    servers, _, gpus, gpu_metrics, processes = await _load_rows(session)
    servers_by_id = {server.id: server for server in servers}
    allocations = await _deployment_allocations(session)
    return [
        _gpu_response(
            servers_by_id[gpu.server_id],
            gpu,
            gpu_metrics.get(gpu.id),
            processes.get(gpu.id, []),
            allocations.get(gpu.id),
        )
        for gpu in gpus
    ]


async def infrastructure_summary(
    session: AsyncSession,
    *,
    offline_seconds: int,
) -> InfrastructureSummaryResponse:
    servers = await list_server_summaries(session, offline_seconds=offline_seconds)
    gpus = await list_gpus(session, offline_seconds=offline_seconds)
    online = sum(server.status == "online" for server in servers)
    latest: list[datetime] = [
        gpu.metric_collected_at for gpu in gpus if gpu.metric_collected_at is not None
    ]
    return InfrastructureSummaryResponse(
        server_count=len(servers),
        online_server_count=online,
        offline_server_count=len(servers) - online,
        gpu_count=len(gpus),
        available_gpu_count=sum(gpu.status == "available" for gpu in gpus),
        gpu_memory_used=sum(gpu.memory_used or 0 for gpu in gpus),
        gpu_memory_total=sum(gpu.memory_total for gpu in gpus),
        latest_collected_at=max(latest, default=None),
    )
