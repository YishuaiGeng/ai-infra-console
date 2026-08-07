from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_INFRA_AGENT_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "production"] = "development"
    central_url: HttpUrl = HttpUrl("http://127.0.0.1:8000")
    token: SecretStr | None = None
    heartbeat_seconds: float = Field(default=10, ge=1, le=3600)
    request_timeout_seconds: float = Field(default=10, ge=1, le=300)
    tls_verify: bool = True
    log_level: str = "INFO"
    allowed_model_directories: tuple[Path, ...] = ()
    default_model_directory: Path | None = None
    model_scan_interval_seconds: float = Field(default=300, ge=10, le=86_400)
    model_scan_max_depth: int = Field(default=6, ge=1, le=32)
    model_scan_max_installations: int = Field(default=2_000, ge=1, le=10_000)
    model_metadata_max_bytes: int = Field(default=1_048_576, ge=1_024, le=16_777_216)
    ollama_timeout_seconds: float = Field(default=2, ge=0.1, le=30)

    @field_validator("allowed_model_directories")
    @classmethod
    def validate_allowed_model_directories(
        cls,
        value: tuple[Path, ...],
    ) -> tuple[Path, ...]:
        normalized: list[Path] = []
        for candidate in value:
            if not candidate.is_absolute():
                raise ValueError("allowed model directories must be absolute paths")
            resolved = candidate.resolve(strict=False)
            if resolved not in normalized:
                normalized.append(resolved)
        for index, path in enumerate(normalized):
            for other in normalized[index + 1 :]:
                if path.is_relative_to(other) or other.is_relative_to(path):
                    raise ValueError("allowed model directories must not overlap")
        return tuple(normalized)

    @model_validator(mode="after")
    def validate_production_transport(self) -> "AgentSettings":
        if self.environment == "production" and self.central_url.scheme != "https":
            raise ValueError("AI_INFRA_AGENT_CENTRAL_URL must use HTTPS in production")
        if self.environment == "production" and not self.tls_verify:
            raise ValueError("TLS verification cannot be disabled in production")
        if self.default_model_directory is not None:
            if not self.default_model_directory.is_absolute():
                raise ValueError("default model directory must be an absolute path")
            default = self.default_model_directory.resolve(strict=False)
            if default not in self.allowed_model_directories:
                raise ValueError("default model directory must be in the allowed directory list")
            self.default_model_directory = default
        return self

    @property
    def central_api_url(self) -> str:
        return str(self.central_url).rstrip("/")


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
