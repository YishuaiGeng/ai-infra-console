from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: SecretStr | None = None
    log_level: str = "INFO"

    @field_validator("bootstrap_admin_password", mode="before")
    @classmethod
    def empty_bootstrap_password_is_unset(cls, value: object) -> object:
        return None if value == "" else value

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
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
