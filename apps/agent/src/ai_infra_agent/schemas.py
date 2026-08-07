import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


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
    deployment_enabled: bool = False


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


class ModelDirectorySnapshot(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    is_default: bool = False
    available: bool
    error_code: str | None = Field(default=None, max_length=64)
    scanned_at: datetime


class ModelInstallationSnapshot(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    architecture: str | None = Field(default=None, max_length=128)
    model_type: str | None = Field(default=None, max_length=64)
    path: str = Field(min_length=1, max_length=4096)
    size: int = Field(ge=0)
    format: Literal["safetensors", "pytorch", "gguf", "ollama"]
    quantization: str | None = Field(default=None, max_length=64)
    revision: str | None = Field(default=None, max_length=128)
    file_count: int = Field(default=1, ge=1, le=100_000)
    metadata: dict[str, str] = Field(default_factory=dict)


class ModelInventorySnapshot(BaseModel):
    collected_at: datetime
    directories: list[ModelDirectorySnapshot] = Field(default_factory=list, max_length=64)
    installations: list[ModelInstallationSnapshot] = Field(
        default_factory=list,
        max_length=10_000,
    )
    ollama: CollectorStatus


class AgentSnapshot(BaseModel):
    collected_at: datetime
    agent_version: str = Field(min_length=1, max_length=64)
    host: HostSnapshot
    gpus: list[GPUSnapshot]
    gpu_collector: CollectorStatus
    model_inventory: ModelInventorySnapshot | None = None


class AgentReportResponse(BaseModel):
    server_id: uuid.UUID
    status: Literal["online"]
    offline_after_seconds: int = Field(ge=1)


class DownloadTaskCommand(BaseModel):
    kind: Literal["download"]
    task_id: uuid.UUID
    lease_token: SecretStr = Field(min_length=32, max_length=128)
    root_path: str = Field(min_length=1, max_length=4096)
    provider: Literal["huggingface", "modelscope"]
    source_id: str = Field(min_length=3, max_length=255)
    revision: str = Field(min_length=1, max_length=128)
    target_path: str = Field(min_length=1, max_length=4096)
    cancel_requested: bool = False


class DeleteTaskCommand(BaseModel):
    kind: Literal["delete"]
    task_id: uuid.UUID
    lease_token: SecretStr = Field(min_length=32, max_length=128)
    root_path: str = Field(min_length=1, max_length=4096)
    model_file_id: uuid.UUID | None
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=255)
    target_path: str = Field(min_length=1, max_length=4096)


ModelTaskCommand = Annotated[
    DownloadTaskCommand | DeleteTaskCommand,
    Field(discriminator="kind"),
]


class ModelTaskClaimResponse(BaseModel):
    task: ModelTaskCommand | None = None


class DownloadProgressResponse(BaseModel):
    cancel_requested: bool
    lease_expires_at: datetime


class DeploymentConfig(BaseModel):
    tensor_parallel_size: int = Field(ge=1, le=8)
    gpu_memory_utilization: float = Field(ge=0.1, le=1)
    max_model_length: int = Field(ge=1_024, le=1_048_576)
    data_type: Literal["auto", "float16", "bfloat16"]
    trust_remote_code: bool
    extra_arguments: list[str] = Field(default_factory=list, max_length=16)


class DeploymentCreateCommand(BaseModel):
    kind: Literal["create"]
    operation_id: uuid.UUID
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    lease_token: SecretStr = Field(min_length=32, max_length=128)
    container_name: str = Field(min_length=1, max_length=128)
    image: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1, max_length=4096)
    model_file_id: uuid.UUID
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=255)
    model_path: str = Field(min_length=1, max_length=4096)
    port: int = Field(ge=1024, le=65535)
    gpu_indexes: list[int] = Field(min_length=1, max_length=8)
    gpu_uuids: list[str] = Field(min_length=1, max_length=8)
    config: DeploymentConfig


class DeploymentLifecycleCommand(BaseModel):
    kind: Literal["start", "stop", "restart", "delete"]
    operation_id: uuid.UUID
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    lease_token: SecretStr = Field(min_length=32, max_length=128)
    container_name: str = Field(min_length=1, max_length=128)


DeploymentCommand = Annotated[
    DeploymentCreateCommand | DeploymentLifecycleCommand,
    Field(discriminator="kind"),
]


class DeploymentTaskClaimResponse(BaseModel):
    task: DeploymentCommand | None = None


class DeploymentOperationProgressResponse(BaseModel):
    lease_expires_at: datetime


class DeploymentLogReport(BaseModel):
    sequence: int = Field(ge=1)
    timestamp: datetime
    stream: Literal["stdout", "stderr"] = "stdout"
    message: str = Field(min_length=1, max_length=4096)


class DeploymentRuntimeObservation(BaseModel):
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    container_id: str | None = Field(default=None, max_length=128)
    state: Literal["running", "stopped", "missing", "failed"]
    exit_code: int | None = None
    health_status: Literal["healthy", "degraded", "unhealthy", "unknown"] = "unknown"
    health_latency_ms: float | None = Field(default=None, ge=0)
    checked_at: datetime
    logs: list[DeploymentLogReport] = Field(default_factory=list, max_length=200)


class DeploymentRuntimeReport(BaseModel):
    observations: list[DeploymentRuntimeObservation] = Field(default_factory=list, max_length=100)


class DeploymentRuntimeExpectation(BaseModel):
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    container_name: str = Field(min_length=1, max_length=128)
    port: int = Field(ge=1024, le=65535)
    desired_state: Literal["running", "stopped"]
