from typing import Literal

from pydantic import BaseModel, Field


class SystemSettingsResponse(BaseModel):
    console_name: str = Field(min_length=2, max_length=128)
    timezone: str = Field(min_length=2, max_length=128)
    language: str = Field(min_length=2, max_length=64)
    heartbeat_interval: int = Field(ge=5, le=300)
    offline_threshold: int = Field(ge=10, le=900)
    metrics_retention_days: int = Field(ge=1, le=3_650)
    default_model_directory: str = Field(min_length=1, max_length=4_096)
    default_backend: Literal["vLLM", "Ollama"]
    default_port: int = Field(ge=1_024, le=65_535)
    default_gpu_memory_utilization: float = Field(ge=0.1, le=1)
    require_delete_confirmation: bool
    audit_log_retention_days: int = Field(ge=1, le=3_650)


class SystemSettingsUpdate(SystemSettingsResponse):
    pass
