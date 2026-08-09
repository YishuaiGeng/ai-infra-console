import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import (
    GPU,
    Deployment,
    GPUMetric,
    ModelDownloadTask,
    Notification,
    Server,
    ServerMetric,
    ServerMetricSample,
)
from ai_infra_api.schemas.monitoring import (
    GPUMetricPointResponse,
    MetricsHistoryResponse,
    NotificationListResponse,
    NotificationResponse,
    ServerMetricPointResponse,
)


async def metrics_history(
    session: AsyncSession,
    *,
    window_hours: int = 24,
    server_id: uuid.UUID | None = None,
) -> MetricsHistoryResponse:
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    server_query = (
        select(ServerMetricSample, Server)
        .join(Server, Server.id == ServerMetricSample.server_id)
        .where(ServerMetricSample.collected_at >= since)
        .order_by(ServerMetricSample.collected_at)
    )
    gpu_query = (
        select(GPUMetric, GPU, Server)
        .join(GPU, GPU.id == GPUMetric.gpu_id)
        .join(Server, Server.id == GPU.server_id)
        .where(GPUMetric.timestamp >= since)
        .order_by(GPUMetric.timestamp)
    )
    if server_id is not None:
        server_query = server_query.where(ServerMetricSample.server_id == server_id)
        gpu_query = gpu_query.where(GPU.server_id == server_id)
    server_rows = (await session.execute(server_query)).all()
    gpu_rows = (await session.execute(gpu_query)).all()
    return MetricsHistoryResponse(
        window_hours=window_hours,
        server_points=[
            ServerMetricPointResponse(
                server_id=sample.server_id,
                server_name=server.name,
                collected_at=sample.collected_at,
                cpu_utilization=sample.cpu_utilization,
                memory_used=sample.memory_used,
                memory_total=sample.memory_total,
                disk_used=sample.disk_used,
                disk_total=sample.disk_total,
                network_bytes_sent=sample.network_bytes_sent,
                network_bytes_received=sample.network_bytes_received,
            )
            for sample, server in server_rows
        ],
        gpu_points=[
            GPUMetricPointResponse(
                gpu_id=gpu.id,
                server_id=server.id,
                server_name=server.name,
                gpu_index=gpu.gpu_index,
                gpu_name=gpu.name,
                collected_at=metric.timestamp,
                utilization=metric.utilization,
                memory_used=metric.memory_used,
                memory_total=gpu.memory_total,
                temperature=metric.temperature,
                power_usage=metric.power_usage,
            )
            for metric, gpu, server in gpu_rows
        ],
    )


def _derived_notification(
    *,
    key: str,
    level: str,
    title: str,
    message: str,
    created_at: datetime,
) -> NotificationResponse:
    return NotificationResponse(
        id=f"derived:{key}",
        level=level,
        title=title,
        message=message,
        is_read=False,
        source="derived",
        created_at=created_at,
    )


async def list_notifications(
    session: AsyncSession,
    *,
    limit: int = 20,
) -> NotificationListResponse:
    now = datetime.now(UTC)
    items: list[NotificationResponse] = []
    servers = list(await session.scalars(select(Server).order_by(Server.name)))
    for server in servers:
        if server.status == "offline":
            items.append(
                _derived_notification(
                    key=f"server-offline:{server.id}",
                    level="critical",
                    title=f"{server.name} is offline",
                    message="The Agent heartbeat is outside the configured online window.",
                    created_at=server.last_seen or now,
                )
            )
    latest_server_metrics = (
        await session.execute(
            select(ServerMetric, Server)
            .join(Server, Server.id == ServerMetric.server_id)
            .where(ServerMetric.disk_used.is_not(None), ServerMetric.disk_total.is_not(None))
        )
    ).all()
    for metric, server in latest_server_metrics:
        if (
            metric.disk_used is not None
            and metric.disk_total is not None
            and metric.disk_total > 0
            and metric.disk_used / metric.disk_total >= 0.9
        ):
            items.append(
                _derived_notification(
                    key=f"server-disk:{server.id}",
                    level="warning",
                    title=f"{server.name} disk space is low",
                    message="The latest Agent report shows disk usage above 90%.",
                    created_at=metric.collected_at,
                )
            )
    latest_gpu_rows = (
        await session.execute(
            select(GPUMetric, GPU, Server)
            .join(GPU, GPU.id == GPUMetric.gpu_id)
            .join(Server, Server.id == GPU.server_id)
            .order_by(GPUMetric.gpu_id, GPUMetric.timestamp.desc(), GPUMetric.id.desc())
        )
    ).all()
    seen_gpu_ids: set[uuid.UUID] = set()
    for metric, gpu, server in latest_gpu_rows:
        if gpu.id in seen_gpu_ids:
            continue
        seen_gpu_ids.add(gpu.id)
        if metric.temperature is not None and metric.temperature >= 85:
            items.append(
                _derived_notification(
                    key=f"gpu-temp:{gpu.id}",
                    level="warning",
                    title=f"{server.name} GPU {gpu.gpu_index} temperature is high",
                    message=f"{gpu.name} is reporting {metric.temperature:.0f} C.",
                    created_at=metric.timestamp,
                )
            )
        if (
            metric.memory_used is not None
            and gpu.memory_total > 0
            and metric.memory_used / gpu.memory_total >= 0.95
        ):
            items.append(
                _derived_notification(
                    key=f"gpu-memory:{gpu.id}",
                    level="warning",
                    title=f"{server.name} GPU {gpu.gpu_index} VRAM is nearly full",
                    message=f"{gpu.name} has less than 5% VRAM available.",
                    created_at=metric.timestamp,
                )
            )
    failed_downloads = list(
        await session.scalars(
            select(ModelDownloadTask)
            .where(ModelDownloadTask.status == "failed")
            .order_by(ModelDownloadTask.updated_at.desc(), ModelDownloadTask.id.desc())
            .limit(5)
        )
    )
    for task in failed_downloads:
        items.append(
            _derived_notification(
                key=f"download-failed:{task.id}",
                level="warning",
                title=f"Download failed: {task.source_id}",
                message=task.error_message or "The model download task failed.",
                created_at=task.updated_at,
            )
        )
    failed_deployments = list(
        await session.scalars(
            select(Deployment)
            .where(Deployment.status == "failed")
            .order_by(Deployment.updated_at.desc(), Deployment.id.desc())
            .limit(5)
        )
    )
    for deployment in failed_deployments:
        items.append(
            _derived_notification(
                key=f"deployment-failed:{deployment.id}",
                level="critical",
                title=f"Deployment failed: {deployment.name}",
                message=deployment.error_message or "The deployment runtime failed.",
                created_at=deployment.updated_at,
            )
        )
    stored = list(
        await session.scalars(
            select(Notification)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        )
    )
    items.extend(
        NotificationResponse(
            id=str(item.id),
            level=item.level if item.level in {"info", "warning", "critical"} else "info",
            title=item.title,
            message=item.message,
            is_read=item.is_read,
            source="stored",
            created_at=item.created_at,
        )
        for item in stored
    )
    items.sort(key=lambda item: item.created_at, reverse=True)
    sliced = items[:limit]
    return NotificationListResponse(
        unread_count=sum(not item.is_read for item in items),
        items=sliced,
    )
