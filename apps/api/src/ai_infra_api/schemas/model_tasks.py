import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from ai_infra_api.schemas.model_inventory import ModelDirectoryResponse, ModelServerResponse

ModelProvider = Literal["huggingface", "modelscope"]
DownloadStatus = Literal[
    "queued",
    "downloading",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
]
DeleteStatus = Literal["queued", "deleting", "completed", "failed"]


def _bounded_text(value: str) -> str:
    if any(ord(character) < 32 for character in value):
        raise ValueError("control characters are not allowed")
    return value.strip()


class CatalogModelResponse(BaseModel):
    provider: ModelProvider
    source_id: str
    display_name: str
    model_type: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)
    downloads: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    license: str | None = None
    gated: bool = False
    private: bool = False
    revision: str | None = None
    size: int | None = Field(default=None, ge=0)
    architecture: str | None = None
    last_modified: datetime | None = None


class CatalogSearchResponse(BaseModel):
    items: list[CatalogModelResponse]
    provider_errors: dict[ModelProvider, str] = Field(default_factory=dict)


class DownloadCreateRequest(BaseModel):
    provider: ModelProvider
    source_id: str = Field(min_length=3, max_length=255)
    revision: str = Field(default="main", min_length=1, max_length=128)
    server_id: uuid.UUID
    directory_id: uuid.UUID

    @field_validator("source_id", "revision")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _bounded_text(value)


class DownloadTargetResponse(BaseModel):
    server: ModelServerResponse
    directories: list[ModelDirectoryResponse]


class DownloadTaskResponse(BaseModel):
    id: uuid.UUID
    model_id: uuid.UUID | None
    server: ModelServerResponse
    directory_id: uuid.UUID | None
    target_path: str
    source: ModelProvider
    source_id: str
    revision: str
    status: DownloadStatus
    downloaded_size: int
    total_size: int | None
    speed_bytes_per_second: int | None
    progress: float | None
    attempt_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    last_progress_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModelDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=255)

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, value: str) -> str:
        return _bounded_text(value)


class ModelDeleteTaskResponse(BaseModel):
    id: uuid.UUID
    model_file_id: uuid.UUID | None
    server: ModelServerResponse
    directory_id: uuid.UUID | None
    source: str
    source_id: str
    target_path: str
    status: DeleteStatus
    attempt_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DownloadTaskCommand(BaseModel):
    kind: Literal["download"] = "download"
    task_id: uuid.UUID
    lease_token: str = Field(min_length=32, max_length=128)
    root_path: str = Field(min_length=1, max_length=4_096)
    provider: ModelProvider
    source_id: str = Field(min_length=3, max_length=255)
    revision: str = Field(min_length=1, max_length=128)
    target_path: str = Field(min_length=1, max_length=4_096)
    cancel_requested: bool = False


class DeleteTaskCommand(BaseModel):
    kind: Literal["delete"] = "delete"
    task_id: uuid.UUID
    lease_token: str = Field(min_length=32, max_length=128)
    root_path: str = Field(min_length=1, max_length=4_096)
    model_file_id: uuid.UUID | None
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=255)
    target_path: str = Field(min_length=1, max_length=4_096)


ModelTaskCommand = Annotated[
    DownloadTaskCommand | DeleteTaskCommand,
    Field(discriminator="kind"),
]


class ModelTaskClaimResponse(BaseModel):
    task: ModelTaskCommand | None = None


class DownloadProgressRequest(BaseModel):
    lease_token: str = Field(min_length=32, max_length=128)
    downloaded_size: int = Field(ge=0)
    total_size: int | None = Field(default=None, ge=0)
    speed_bytes_per_second: int | None = Field(default=None, ge=0)


class DownloadProgressResponse(BaseModel):
    cancel_requested: bool
    lease_expires_at: datetime


class DownloadTerminalRequest(BaseModel):
    lease_token: str = Field(min_length=32, max_length=128)
    outcome: Literal["completed", "failed", "cancelled"]
    downloaded_size: int = Field(default=0, ge=0)
    total_size: int | None = Field(default=None, ge=0)
    final_path: str | None = Field(default=None, max_length=4_096)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=1_024)


class DeleteTerminalRequest(BaseModel):
    lease_token: str = Field(min_length=32, max_length=128)
    outcome: Literal["completed", "failed"]
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=1_024)
