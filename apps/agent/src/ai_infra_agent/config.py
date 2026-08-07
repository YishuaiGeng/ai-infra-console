from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, model_validator
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

    @model_validator(mode="after")
    def validate_production_transport(self) -> "AgentSettings":
        if self.environment == "production" and self.central_url.scheme != "https":
            raise ValueError("AI_INFRA_AGENT_CENTRAL_URL must use HTTPS in production")
        if self.environment == "production" and not self.tls_verify:
            raise ValueError("TLS verification cannot be disabled in production")
        return self

    @property
    def central_api_url(self) -> str:
        return str(self.central_url).rstrip("/")


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
