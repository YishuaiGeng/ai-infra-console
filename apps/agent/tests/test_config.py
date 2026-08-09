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


def test_model_directories_are_normalized_and_default_is_allowed(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(str(tmp_path)) / "models"
    settings = AgentSettings(
        environment="test",
        allowed_model_directories=(root, root),
        default_model_directory=root,
    )

    assert settings.allowed_model_directories == (root.resolve(),)
    assert settings.default_model_directory == root.resolve()


def test_model_directories_reject_relative_overlap_and_unknown_default(
    tmp_path: object,
) -> None:
    from pathlib import Path

    root = Path(str(tmp_path)) / "models"
    with pytest.raises(ValidationError, match="absolute paths"):
        AgentSettings(environment="test", allowed_model_directories=(Path("models"),))
    with pytest.raises(ValidationError, match="must not overlap"):
        AgentSettings(
            environment="test",
            allowed_model_directories=(root, root / "nested"),
        )
    with pytest.raises(ValidationError, match="must be in the allowed"):
        AgentSettings(
            environment="test",
            allowed_model_directories=(root,),
            default_model_directory=Path(str(tmp_path)) / "other",
        )


@pytest.mark.parametrize(
    "fixture_field",
    ["deployment_runtime_fixture", "deployment_gpu_fixture"],
)
def test_production_rejects_deployment_fixtures(fixture_field: str) -> None:
    with pytest.raises(ValidationError, match="fixture deployment"):
        AgentSettings.model_validate(
            {
                "environment": "production",
                "central_url": "https://central.example.com",
                fixture_field: True,
            }
        )
