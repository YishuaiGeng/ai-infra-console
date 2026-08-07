import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ModelServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    type: str
    host: str | None
    hostname: str | None


class ModelDirectoryResponse(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    path: str
    is_default: bool
    is_allowed: bool
    is_available: bool
    error_code: str | None
    last_scanned_at: datetime | None
    model_count: int = Field(ge=0)


class ModelInstallationResponse(BaseModel):
    id: uuid.UUID
    model_id: uuid.UUID
    source: str
    source_id: str
    name: str
    display_name: str | None
    description: str | None
    architecture: str | None
    model_type: str | None
    metadata: dict[str, str]
    server: ModelServerResponse
    directory_id: uuid.UUID | None
    path: str
    size: int | None
    file_count: int = Field(ge=1)
    format: str | None
    quantization: str | None
    revision: str | None
    status: str
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModelDetailResponse(BaseModel):
    id: uuid.UUID
    source: str
    source_id: str
    name: str
    display_name: str | None
    description: str | None
    architecture: str | None
    model_type: str | None
    metadata: dict[str, str]
    locations: list[ModelInstallationResponse]


class ModelInventorySummaryResponse(BaseModel):
    model_count: int = Field(ge=0)
    installation_count: int = Field(ge=0)
    current_installation_count: int = Field(ge=0)
    server_count: int = Field(ge=0)
    total_size: int = Field(ge=0)
    formats: dict[str, int]
    latest_scanned_at: datetime | None


class DefaultModelDirectoryRequest(BaseModel):
    directory_id: uuid.UUID
