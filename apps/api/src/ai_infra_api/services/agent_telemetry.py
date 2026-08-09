from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import (
    GPU,
    GPUMetric,
    GPUProcess,
    Server,
    ServerAgent,
    ServerMetric,
    ServerMetricSample,
)
from ai_infra_api.schemas.agent import AgentSnapshot, GPUProcessSnapshot
from ai_infra_api.services.model_inventory import persist_model_inventory


@dataclass(slots=True)
class AgentPersistenceResult:
    server: Server
    model_inventory_changed: bool


async def persist_agent_snapshot(
    session: AsyncSession,
    agent: ServerAgent,
    snapshot: AgentSnapshot,
    *,
    received_at: datetime | None = None,
    metrics_retention_days: int = 14,
) -> AgentPersistenceResult:
    now = received_at or datetime.now(UTC)
    server = await session.get(Server, agent.server_id)
    if server is None:
        raise RuntimeError("Agent is not attached to a server")
    if server.hostname is not None and server.hostname != snapshot.host.hostname:
        raise ValueError("Agent hostname does not match the registered server")

    disk_total = sum(item.total for item in snapshot.host.disks)
    disk_used = sum(item.used for item in snapshot.host.disks)
    server.hostname = snapshot.host.hostname
    server.status = "online"
    server.os = snapshot.host.os
    server.kernel = snapshot.host.kernel
    server.cpu_model = snapshot.host.cpu.model
    server.cpu_cores = snapshot.host.cpu.logical_cores
    server.memory_total = snapshot.host.memory.total
    server.disk_total = disk_total
    server.agent_version = snapshot.agent_version
    server.last_seen = now
    agent.version = snapshot.agent_version
    agent.last_seen = now

    metric = await session.scalar(select(ServerMetric).where(ServerMetric.server_id == server.id))
    if metric is None:
        metric = ServerMetric(server_id=server.id)
        session.add(metric)
    metric.collected_at = now
    metric.uptime_seconds = (
        max(0, int((now - snapshot.host.boot_time).total_seconds()))
        if snapshot.host.boot_time is not None
        else None
    )
    metric.cpu_utilization = snapshot.host.cpu.utilization
    metric.memory_used = snapshot.host.memory.used
    metric.memory_total = snapshot.host.memory.total
    metric.disk_used = disk_used
    metric.disk_total = disk_total
    metric.network_bytes_sent = snapshot.host.network.bytes_sent
    metric.network_bytes_received = snapshot.host.network.bytes_received
    metric.runtime_info = {
        "architecture": snapshot.host.architecture,
        "collected_at": snapshot.collected_at.isoformat(),
        "disks": [item.model_dump(mode="json") for item in snapshot.host.disks],
        "gpu_collector": snapshot.gpu_collector.model_dump(mode="json"),
        "load_average": snapshot.host.cpu.load_average,
        "runtimes": snapshot.host.runtimes.model_dump(mode="json"),
    }
    session.add(
        ServerMetricSample(
            server_id=server.id,
            collected_at=now,
            cpu_utilization=metric.cpu_utilization,
            memory_used=metric.memory_used,
            memory_total=metric.memory_total,
            disk_used=metric.disk_used,
            disk_total=metric.disk_total,
            network_bytes_sent=metric.network_bytes_sent,
            network_bytes_received=metric.network_bytes_received,
        )
    )

    existing_gpus = list(await session.scalars(select(GPU).where(GPU.server_id == server.id)))
    by_uuid = {item.uuid: item for item in existing_gpus}
    by_index = {item.gpu_index: item for item in existing_gpus}
    for existing in existing_gpus:
        existing.gpu_index += 10_000
    if existing_gpus:
        await session.flush()
    reported_uuids: set[str] = set()
    gpu_process_rows: list[tuple[GPU, GPUProcessSnapshot]] = []
    for reported in snapshot.gpus:
        reported_uuids.add(reported.uuid)
        gpu = by_uuid.get(reported.uuid) or by_index.get(reported.index)
        if gpu is None:
            gpu = GPU(
                server_id=server.id,
                gpu_index=reported.index,
                uuid=reported.uuid,
                vendor=reported.vendor,
                name=reported.name,
                memory_total=reported.memory_total,
                status=reported.status,
            )
            session.add(gpu)
            by_uuid[reported.uuid] = gpu
        else:
            gpu.uuid = reported.uuid
            by_uuid[reported.uuid] = gpu
        gpu.gpu_index = reported.index
        gpu.vendor = reported.vendor
        gpu.name = reported.name
        gpu.memory_total = reported.memory_total
        gpu.driver_version = reported.driver_version
        gpu.cuda_version = reported.cuda_version
        gpu.status = reported.status
        await session.flush()
        session.add(
            GPUMetric(
                gpu_id=gpu.id,
                timestamp=now,
                utilization=reported.utilization,
                memory_used=reported.memory_used,
                temperature=reported.temperature,
                power_usage=reported.power_usage,
                power_limit=reported.power_limit,
                fan_speed=reported.fan_speed,
            )
        )
        processes_by_pid: dict[int, GPUProcessSnapshot] = {}
        for process in reported.processes:
            current = processes_by_pid.get(process.pid)
            if current is None or (process.memory_used or 0) > (current.memory_used or 0):
                processes_by_pid[process.pid] = process
        gpu_process_rows.extend((gpu, process) for process in processes_by_pid.values())

    for missing in existing_gpus:
        if missing.uuid not in reported_uuids:
            missing.status = "offline"

    gpu_ids = [item.id for item in by_uuid.values()]
    if gpu_ids:
        await session.execute(delete(GPUProcess).where(GPUProcess.gpu_id.in_(gpu_ids)))
    for gpu, process_value in gpu_process_rows:
        process = process_value
        session.add(
            GPUProcess(
                gpu_id=gpu.id,
                pid=process.pid,
                username=process.username,
                command=process.command,
                memory_used=process.memory_used,
                collected_at=now,
            )
        )

    inventory_result = await persist_model_inventory(session, server, snapshot.model_inventory)
    retention_cutoff = now - timedelta(days=metrics_retention_days)
    await session.execute(
        delete(ServerMetricSample).where(ServerMetricSample.collected_at < retention_cutoff)
    )
    await session.execute(delete(GPUMetric).where(GPUMetric.timestamp < retention_cutoff))

    await session.commit()
    await session.refresh(server)
    return AgentPersistenceResult(
        server=server,
        model_inventory_changed=inventory_result.changed,
    )


async def mark_stale_servers_offline(
    session: AsyncSession,
    *,
    threshold_seconds: int,
    now: datetime | None = None,
) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(seconds=threshold_seconds)
    stale_ids = list(
        await session.scalars(
            select(Server.id).where(
                Server.last_seen.is_not(None),
                Server.last_seen < cutoff,
                Server.status != "offline",
            )
        )
    )
    if stale_ids:
        await session.execute(
            update(Server).where(Server.id.in_(stale_ids)).values(status="offline")
        )
    await session.commit()
    return len(stale_ids)
