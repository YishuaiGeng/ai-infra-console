import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ai_infra_api.schemas.model_inventory import (
    ModelDirectoryResponse,
    ModelInstallationResponse,
)


class RuntimeAvailabilityResponse(BaseModel):
    available: bool
    version: str | None = None


class ServerMetricResponse(BaseModel):
    collected_at: datetime
    uptime_seconds: int | None
    cpu_utilization: float | None
    memory_used: int | None
    memory_total: int | None
    disk_used: int | None
    disk_total: int | None
    network_bytes_sent: int | None
    network_bytes_received: int | None
    architecture: str | None
    runtimes: dict[str, RuntimeAvailabilityResponse]


class ServerReferenceResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    status: str
    host: str | None
    hostname: str | None


class GPUProcessResponse(BaseModel):
    id: uuid.UUID
    gpu_id: uuid.UUID
    gpu_index: int
    gpu_name: str
    pid: int
    username: str | None
    command: str | None
    memory_used: int | None
    collected_at: datetime


class GPUResponse(BaseModel):
    id: uuid.UUID
    server: ServerReferenceResponse
    index: int
    uuid: str
    vendor: str
    name: str
    status: Literal[
        "available",
        "active",
        "high-load",
        "memory-full",
        "unavailable",
    ]
    utilization: float | None
    memory_used: int | None
    memory_total: int
    temperature: float | None
    power_usage: float | None
    power_limit: float | None
    fan_speed: float | None
    driver_version: str | None
    cuda_version: str | None
    metric_collected_at: datetime | None
    process_count: int


class ServerSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    type: str
    provider: str | None
    host: str | None
    hostname: str | None
    description: str | None
    tags: list[str]
    os: str | None
    kernel: str | None
    cpu_model: str | None
    cpu_cores: int | None
    memory_total: int | None
    disk_total: int | None
    agent_version: str | None
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime
    metric: ServerMetricResponse | None
    gpu_count: int = Field(ge=0)
    available_gpu_count: int = Field(ge=0)
    gpu_memory_total: int = Field(ge=0)
    gpu_models: list[str]
    model_count: int = Field(default=0, ge=0)


class ServerDetailResponse(ServerSummaryResponse):
    gpus: list[GPUResponse]
    processes: list[GPUProcessResponse]
    models: list[ModelInstallationResponse]
    model_directories: list[ModelDirectoryResponse]


class InfrastructureSummaryResponse(BaseModel):
    server_count: int = Field(ge=0)
    online_server_count: int = Field(ge=0)
    offline_server_count: int = Field(ge=0)
    gpu_count: int = Field(ge=0)
    available_gpu_count: int = Field(ge=0)
    gpu_memory_used: int = Field(ge=0)
    gpu_memory_total: int = Field(ge=0)
    latest_collected_at: datetime | None


class InfrastructureEvent(BaseModel):
    id: str
    kind: Literal["server.updated", "server.offline", "model.inventory.updated"]
    server_id: uuid.UUID
    occurred_at: datetime
