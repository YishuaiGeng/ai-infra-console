from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_INFRA_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI Infra Console API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://ai_infra:ai_infra@localhost:5432/ai_infra"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "default"

    jwt_secret: SecretStr = SecretStr("development-only-change-me")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "ai-infra-console"
    jwt_audience: str = "ai-infra-console-web"
    access_token_minutes: int = 30
    agent_offline_seconds: int = Field(default=30, ge=10, le=86400)
    mutable_server_names: tuple[str, ...] = ()
    model_task_lease_seconds: int = Field(default=60, ge=15, le=3_600)
    deployment_task_lease_seconds: int = Field(default=90, ge=15, le=3_600)
    deployment_telemetry_fresh_seconds: int = Field(default=30, ge=10, le=3_600)
    deployment_log_retention_lines: int = Field(default=2_000, ge=100, le=20_000)
    api_test_timeout_seconds: float = Field(default=30, ge=1, le=120)
    credential_encryption_key: SecretStr | None = None
    credential_encryption_key_version: str = Field(default="v1", min_length=1, max_length=32)
    external_api_allow_private_networks: bool = False
    external_api_allowed_hosts: tuple[str, ...] = ()
    external_api_allowed_cidrs: tuple[str, ...] = ()
    api_resource_sync_enabled: bool = True
    api_resource_request_timeout_seconds: float = Field(default=15, ge=1, le=120)
    api_resource_max_response_bytes: int = Field(default=2_097_152, ge=1_024, le=20_971_520)
    metrics_retention_days: int = Field(default=14, ge=1, le=3_650)
    vllm_image: str = Field(default="vllm/vllm-openai:latest", min_length=1, max_length=255)
    model_catalog_timeout_seconds: float = Field(default=10, ge=1, le=60)
    model_catalog_cache_seconds: int = Field(default=60, ge=0, le=3_600)
    model_catalog_max_results: int = Field(default=20, ge=1, le=100)
    hf_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_INFRA_HF_TOKEN", "HF_TOKEN"),
    )
    hf_endpoint: HttpUrl = Field(
        default=HttpUrl("https://huggingface.co"),
        validation_alias=AliasChoices("AI_INFRA_HF_ENDPOINT", "HF_ENDPOINT"),
    )
    modelscope_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_INFRA_MODELSCOPE_TOKEN", "MODELSCOPE_TOKEN"),
    )
    modelscope_endpoint: HttpUrl = Field(
        default=HttpUrl("https://modelscope.cn"),
        validation_alias=AliasChoices(
            "AI_INFRA_MODELSCOPE_ENDPOINT",
            "MODELSCOPE_ENDPOINT",
        ),
    )

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: SecretStr | None = None
    log_level: str = "INFO"

    @field_validator("bootstrap_admin_password", mode="before")
    @classmethod
    def empty_bootstrap_password_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator(
        "mutable_server_names", "external_api_allowed_hosts", "external_api_allowed_cidrs"
    )
    @classmethod
    def normalize_mutable_server_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        if any(len(item) > 128 for item in normalized):
            raise ValueError("mutable server names must be at most 128 characters")
        return normalized

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment != "production":
            return self

        secret = self.jwt_secret.get_secret_value()
        if len(secret) < 32 or secret == "development-only-change-me":  # noqa: S105
            raise ValueError("AI_INFRA_JWT_SECRET must be at least 32 characters in production")
        database_password = make_url(self.database_url).password or ""
        if len(database_password) < 12 or database_password in {"ai_infra", "ai_infra_dev"}:
            raise ValueError("AI_INFRA_DATABASE_URL must use a strong password in production")
        if self.hf_endpoint.scheme != "https" or self.modelscope_endpoint.scheme != "https":
            raise ValueError("model provider endpoints must use HTTPS in production")
        if self.credential_encryption_key is None:
            raise ValueError("AI_INFRA_CREDENTIAL_ENCRYPTION_KEY is required in production")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
