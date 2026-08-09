import pytest
from pydantic import SecretStr, ValidationError

from ai_infra_api.core.config import Settings


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            environment="production",
            bootstrap_admin_password=SecretStr("temporary-password"),
        )


def test_production_requires_strong_database_password() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            environment="production",
            jwt_secret=SecretStr("a-production-secret-with-more-than-32-characters"),
        )


def test_empty_bootstrap_password_is_unset() -> None:
    settings = Settings(bootstrap_admin_password="")

    assert settings.bootstrap_admin_password is None
