import pytest
from pydantic import SecretStr, ValidationError

from ai_infra_agent.config import AgentSettings


def test_defaults_match_phase_contract() -> None:
    settings = AgentSettings(environment="test", token=SecretStr("agent-secret"))

    assert settings.heartbeat_seconds == 10
    assert settings.central_api_url == "http://127.0.0.1:8000"
    assert "agent-secret" not in repr(settings)


def test_production_requires_https() -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        AgentSettings.model_validate(
            {"environment": "production", "central_url": "http://central.example.com"}
        )


def test_production_requires_tls_verification() -> None:
    with pytest.raises(ValidationError, match="cannot be disabled"):
        AgentSettings.model_validate(
            {
                "environment": "production",
                "central_url": "https://central.example.com",
                "tls_verify": False,
            }
        )
