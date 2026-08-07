import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_infra_api.schemas.model_inventory import ModelServerResponse

DeploymentStatus = Literal[
    "queued",
    "starting",
    "running",
    "stopping",
    "stopped",
    "restarting",
    "deleting",
    "failed",
    "unknown",
]
DeploymentDesiredState = Literal["running", "stopped", "deleted"]
DeploymentHealth = Literal["healthy", "degraded", "unhealthy", "unknown"]
DeploymentAction = Literal["create", "start", "stop", "restart", "delete"]
OperationStatus = Literal["queued", "running", "completed", "failed"]
DataType = Literal["auto", "float16", "bfloat16"]
SelectionMode = Literal["automatic", "manual"]

NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,126}[a-zA-Z0-9]$")
EXTRA_ARGUMENT_PATTERN = re.compile(r"^[a-zA-Z0-9._:/=,+-]+$")


class DeploymentConfigRequest(BaseModel):
    tensor_parallel_size: int = Field(default=1, ge=1, le=8)
    gpu_memory_utilization: float = Field(default=0.9, ge=0.1, le=1)
    max_model_length: int = Field(default=32_768, ge=1_024, le=1_048_576)
    data_type: DataType = "auto"
    trust_remote_code: bool = False
    extra_arguments: list[str] = Field(default_factory=list, max_length=16)

    @field_validator("extra_arguments")
    @classmethod
    def validate_extra_arguments(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for token in value:
            clean = token.strip()
            if not clean or len(clean) > 128 or EXTRA_ARGUMENT_PATTERN.fullmatch(clean) is None:
                raise ValueError("extra arguments must be bounded shell-free tokens")
            normalized.append(clean)
        return normalized


class DeploymentCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=128)
    model_file_id: uuid.UUID
    selection_mode: SelectionMode = "automatic"
    gpu_ids: list[uuid.UUID] = Field(default_factory=list, max_length=8)
    port: int = Field(default=8_001, ge=1_024, le=65_535)
    config: DeploymentConfigRequest = Field(default_factory=DeploymentConfigRequest)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if NAME_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "name must use letters, numbers, dot, underscore, or dash and end alphanumeric"
            )
        return normalized

    @field_validator("gpu_ids")
    @classmethod
    def unique_gpu_ids(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("GPU IDs must be unique")
        return value

    @model_validator(mode="after")
    def validate_placement(self) -> "DeploymentCreateRequest":
        if self.selection_mode == "manual" and not self.gpu_ids:
            raise ValueError("manual placement requires at least one GPU")
        if (
            self.selection_mode == "manual"
            and len(self.gpu_ids) != self.config.tensor_parallel_size
        ):
            raise ValueError("manual GPU count must equal tensor parallel size")
        if self.selection_mode == "automatic" and self.gpu_ids:
            raise ValueError("automatic placement does not accept GPU IDs")
        return self


class DeploymentDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=3, max_length=128)

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        return value.strip()


class DeploymentGPUResponse(BaseModel):
    id: uuid.UUID
    index: int
    uuid: str
    name: str
    status: str
    memory_total: int
    memory_used: int | None = None
    utilization: float | None = None


class DeploymentModelResponse(BaseModel):
    id: uuid.UUID
    model_file_id: uuid.UUID
    source: str
    source_id: str
    name: str
    display_name: str
    path: str
    format: str | None
    quantization: str | None
    revision: str | None
    size: int | None


class DeploymentOperationResponse(BaseModel):
    id: uuid.UUID
    action: DeploymentAction
    status: OperationStatus
    generation: int
    attempt_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeploymentResponse(BaseModel):
    id: uuid.UUID
    name: str
    model: DeploymentModelResponse
    server: ModelServerResponse
    gpus: list[DeploymentGPUResponse]
    backend: Literal["vllm"]
    selection_mode: SelectionMode
    desired_state: DeploymentDesiredState
    status: DeploymentStatus
    generation: int
    port: int
    endpoint: str
    config: DeploymentConfigRequest
    health_status: DeploymentHealth
    health_latency_ms: float | None
    last_health_checked_at: datetime | None
    last_reconciled_at: datetime | None
    uptime_seconds: int | None
    error_code: str | None
    error_message: str | None
    current_operation: DeploymentOperationResponse | None
    started_at: datetime | None
    stopped_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeploymentTargetResponse(BaseModel):
    server: ModelServerResponse
    docker_available: bool
    docker_version: str | None
    model_files: list[DeploymentModelResponse]
    gpus: list[DeploymentGPUResponse]


class DeploymentLogResponse(BaseModel):
    sequence: int
    timestamp: datetime
    stream: Literal["stdout", "stderr"]
    message: str


class DeploymentCreateCommand(BaseModel):
    kind: Literal["create"] = "create"
    operation_id: uuid.UUID
    deployment_id: uuid.UUID
    generation: int
    lease_token: str = Field(min_length=32, max_length=128)
    container_name: str = Field(min_length=1, max_length=128)
    image: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1, max_length=4_096)
    model_file_id: uuid.UUID
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=255)
    model_path: str = Field(min_length=1, max_length=4_096)
    port: int = Field(ge=1_024, le=65_535)
    gpu_indexes: list[int] = Field(min_length=1, max_length=8)
    gpu_uuids: list[str] = Field(min_length=1, max_length=8)
    config: DeploymentConfigRequest


class DeploymentLifecycleCommand(BaseModel):
    kind: Literal["start", "stop", "restart", "delete"]
    operation_id: uuid.UUID
    deployment_id: uuid.UUID
    generation: int
    lease_token: str = Field(min_length=32, max_length=128)
    container_name: str = Field(min_length=1, max_length=128)


DeploymentCommand = Annotated[
    DeploymentCreateCommand | DeploymentLifecycleCommand,
    Field(discriminator="kind"),
]


class DeploymentTaskClaimResponse(BaseModel):
    task: DeploymentCommand | None = None


class DeploymentOperationProgressRequest(BaseModel):
    lease_token: str = Field(min_length=32, max_length=128)
    generation: int = Field(ge=1)


class DeploymentOperationProgressResponse(BaseModel):
    lease_expires_at: datetime


class DeploymentOperationTerminalRequest(BaseModel):
    lease_token: str = Field(min_length=32, max_length=128)
    generation: int = Field(ge=1)
    outcome: Literal["completed", "failed"]
    observed_state: Literal["running", "stopped", "missing", "failed"]
    container_id: str | None = Field(default=None, max_length=128)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=1_024)


class DeploymentLogReport(BaseModel):
    sequence: int = Field(ge=1)
    timestamp: datetime
    stream: Literal["stdout", "stderr"] = "stdout"
    message: str = Field(min_length=1, max_length=4_096)


class DeploymentRuntimeObservation(BaseModel):
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    container_id: str | None = Field(default=None, max_length=128)
    state: Literal["running", "stopped", "missing", "failed"]
    exit_code: int | None = None
    health_status: DeploymentHealth = "unknown"
    health_latency_ms: float | None = Field(default=None, ge=0)
    checked_at: datetime
    logs: list[DeploymentLogReport] = Field(default_factory=list, max_length=200)


class DeploymentRuntimeReport(BaseModel):
    observations: list[DeploymentRuntimeObservation] = Field(default_factory=list, max_length=100)


class DeploymentRuntimeExpectation(BaseModel):
    deployment_id: uuid.UUID
    generation: int = Field(ge=1)
    container_name: str = Field(min_length=1, max_length=128)
    port: int = Field(ge=1_024, le=65_535)
    desired_state: Literal["running", "stopped"]
