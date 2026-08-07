import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CollectorStatus(BaseModel):
    available: bool
    version: str | None = None
    detail: str | None = Field(default=None, max_length=512)


class CPUSnapshot(BaseModel):
    model: str | None = Field(default=None, max_length=255)
    physical_cores: int | None = Field(default=None, ge=0)
    logical_cores: int | None = Field(default=None, ge=0)
    utilization: float | None = Field(default=None, ge=0, le=100)
    load_average: tuple[float, float, float] | None = None


class MemorySnapshot(BaseModel):
    total: int = Field(ge=0)
    used: int = Field(ge=0)
    percent: float = Field(ge=0, le=100)


class DiskSnapshot(BaseModel):
    mountpoint: str = Field(min_length=1, max_length=1024)
    filesystem: str | None = Field(default=None, max_length=64)
    total: int = Field(ge=0)
    used: int = Field(ge=0)
    percent: float = Field(ge=0, le=100)


class NetworkSnapshot(BaseModel):
    bytes_sent: int = Field(ge=0)
    bytes_received: int = Field(ge=0)


class RuntimeSnapshot(BaseModel):
    python: CollectorStatus
    docker: CollectorStatus
    ollama: CollectorStatus


class HostSnapshot(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    os: str = Field(min_length=1, max_length=128)
    kernel: str = Field(min_length=1, max_length=128)
    architecture: str = Field(min_length=1, max_length=64)
    boot_time: datetime | None = None
    cpu: CPUSnapshot
    memory: MemorySnapshot
    disks: list[DiskSnapshot]
    network: NetworkSnapshot
    runtimes: RuntimeSnapshot


class GPUProcessSnapshot(BaseModel):
    pid: int = Field(ge=1)
    username: str | None = Field(default=None, max_length=128)
    command: str | None = Field(default=None, max_length=512)
    memory_used: int | None = Field(default=None, ge=0)


class GPUSnapshot(BaseModel):
    index: int = Field(ge=0)
    uuid: str = Field(min_length=1, max_length=128)
    vendor: Literal["NVIDIA"] = "NVIDIA"
    name: str = Field(min_length=1, max_length=255)
    memory_total: int = Field(ge=0)
    memory_used: int | None = Field(default=None, ge=0)
    utilization: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = None
    power_usage: float | None = Field(default=None, ge=0)
    power_limit: float | None = Field(default=None, ge=0)
    fan_speed: float | None = Field(default=None, ge=0, le=100)
    driver_version: str | None = Field(default=None, max_length=64)
    cuda_version: str | None = Field(default=None, max_length=64)
    status: str = Field(default="available", min_length=1, max_length=32)
    processes: list[GPUProcessSnapshot] = Field(default_factory=list)


class AgentSnapshot(BaseModel):
    collected_at: datetime
    agent_version: str = Field(min_length=1, max_length=64)
    host: HostSnapshot
    gpus: list[GPUSnapshot]
    gpu_collector: CollectorStatus


class AgentReportResponse(BaseModel):
    server_id: uuid.UUID
    status: Literal["online"] = "online"
    offline_after_seconds: int


class ServerRegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: Literal["local", "cloud"] = "local"
    provider: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2048)
    tags: list[str] = Field(default_factory=list, max_length=32)


class ServerRegistrationResponse(BaseModel):
    server_id: uuid.UUID
    registration_token: str


class AgentTokenResponse(BaseModel):
    server_id: uuid.UUID
    registration_token: str


class ServerStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    hostname: str | None
    status: str
    agent_version: str | None
    last_seen: datetime | None
