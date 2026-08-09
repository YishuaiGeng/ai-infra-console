from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator, model_validator
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
    enable_model_mutations: bool = False
    model_task_progress_seconds: float = Field(default=2, ge=0.25, le=60)
    model_download_max_workers: int = Field(default=4, ge=1, le=16)
    hf_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_INFRA_AGENT_HF_TOKEN", "HF_TOKEN"),
    )
    hf_endpoint: HttpUrl = Field(
        default=HttpUrl("https://huggingface.co"),
        validation_alias=AliasChoices("AI_INFRA_AGENT_HF_ENDPOINT", "HF_ENDPOINT"),
    )
    modelscope_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_INFRA_AGENT_MODELSCOPE_TOKEN",
            "MODELSCOPE_TOKEN",
        ),
    )
    modelscope_endpoint: HttpUrl = Field(
        default=HttpUrl("https://modelscope.cn"),
        validation_alias=AliasChoices(
            "AI_INFRA_AGENT_MODELSCOPE_ENDPOINT",
            "MODELSCOPE_ENDPOINT",
        ),
    )
    http_proxy: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_INFRA_AGENT_HTTP_PROXY", "HTTP_PROXY"),
    )
    https_proxy: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_INFRA_AGENT_HTTPS_PROXY", "HTTPS_PROXY"),
    )
    model_download_fixture_source: Path | None = None
    enable_deployments: bool = False
    vllm_image: str = Field(default="vllm/vllm-openai:latest", min_length=1, max_length=255)
    deployment_operation_progress_seconds: float = Field(default=5, ge=0.5, le=60)
    deployment_reconcile_seconds: float = Field(default=5, ge=1, le=300)
    deployment_stop_timeout_seconds: int = Field(default=20, ge=1, le=300)
    deployment_health_timeout_seconds: float = Field(default=2, ge=0.1, le=30)
    deployment_log_max_lines: int = Field(default=200, ge=10, le=1_000)
    deployment_log_max_bytes: int = Field(default=262_144, ge=4_096, le=4_194_304)
    deployment_runtime_fixture: bool = False
    deployment_gpu_fixture: bool = False

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
        if self.environment == "production" and (
            self.hf_endpoint.scheme != "https" or self.modelscope_endpoint.scheme != "https"
        ):
            raise ValueError("model provider endpoints must use HTTPS in production")
        if self.environment == "production" and self.model_download_fixture_source is not None:
            raise ValueError("fixture model downloads cannot be enabled in production")
        if self.environment == "production" and self.deployment_runtime_fixture:
            raise ValueError("fixture deployment runtime cannot be enabled in production")
        if self.environment == "production" and self.deployment_gpu_fixture:
            raise ValueError("fixture deployment GPU cannot be enabled in production")
        if self.enable_model_mutations and not self.allowed_model_directories:
            raise ValueError("model mutations require at least one allowed model directory")
        if self.enable_deployments and not self.allowed_model_directories:
            raise ValueError("deployments require at least one allowed model directory")
        if (
            self.environment == "production"
            and self.enable_deployments
            and "@sha256:" not in self.vllm_image
        ):
            raise ValueError("production deployments require an immutable vLLM image digest")
        if self.model_download_fixture_source is not None:
            if not self.model_download_fixture_source.is_absolute():
                raise ValueError("fixture model source must be an absolute path")
            self.model_download_fixture_source = self.model_download_fixture_source.resolve(
                strict=False
            )
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
