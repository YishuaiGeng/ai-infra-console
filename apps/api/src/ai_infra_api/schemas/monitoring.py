import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ServerMetricPointResponse(BaseModel):
    server_id: uuid.UUID
    server_name: str
    collected_at: datetime
    cpu_utilization: float | None
    memory_used: int | None
    memory_total: int | None
    disk_used: int | None
    disk_total: int | None
    network_bytes_sent: int | None
    network_bytes_received: int | None


class GPUMetricPointResponse(BaseModel):
    gpu_id: uuid.UUID
    server_id: uuid.UUID
    server_name: str
    gpu_index: int
    gpu_name: str
    collected_at: datetime
    utilization: float | None
    memory_used: int | None
    memory_total: int
    temperature: float | None
    power_usage: float | None


class MetricsHistoryResponse(BaseModel):
    window_hours: int = Field(ge=1, le=720)
    server_points: list[ServerMetricPointResponse]
    gpu_points: list[GPUMetricPointResponse]


class NotificationResponse(BaseModel):
    id: str
    level: Literal["info", "warning", "critical"]
    title: str
    message: str
    is_read: bool
    source: Literal["derived", "stored"]
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int = Field(ge=0)
    items: list[NotificationResponse]
