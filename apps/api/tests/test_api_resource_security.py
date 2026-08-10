import base64
import uuid

import pytest
from cryptography.exceptions import InvalidTag
from pydantic import SecretStr

from ai_infra_api.core.config import Settings
from ai_infra_api.services.api_resources.adapters.generic_openai import OpenAIAdapter
from ai_infra_api.services.api_resources.encryption import CredentialEncryption, mask_credential
from ai_infra_api.services.api_resources.network_policy import (
    NetworkPolicyError,
    validate_external_base_url,
)


def settings(*, external_api_allowed_cidrs: tuple[str, ...] = ()) -> Settings:
    return Settings(
        environment="test",
        jwt_secret=SecretStr("test-secret-that-is-long-enough-for-tests"),
        credential_encryption_key=SecretStr(base64.b64encode(b"x" * 32).decode()),
        external_api_allowed_cidrs=external_api_allowed_cidrs,
        bootstrap_admin_password=None,
    )


def test_credential_encryption_round_trip_and_aad() -> None:
    encryption = CredentialEncryption(settings())
    account_id = uuid.uuid4()
    credential_id = uuid.uuid4()
    encrypted = encryption.encrypt(account_id, credential_id, "sk-secret-value")

    assert b"sk-secret-value" not in encrypted
    assert encryption.decrypt(account_id, credential_id, encrypted) == "sk-secret-value"
    assert encryption.fingerprint("sk-secret-value") == encryption.fingerprint("sk-secret-value")
    assert mask_credential("sk-secret-value") == "sk-s****alue"
    with pytest.raises(InvalidTag):
        encryption.decrypt(account_id, uuid.uuid4(), encrypted)


async def test_network_policy_rejects_metadata_loopback_and_url_credentials() -> None:
    for url in (
        "http://169.254.169.254/latest/meta-data",
        "http://127.0.0.1:8000/v1",
        "https://user:password@example.com/v1",
        "file:///etc/passwd",
    ):
        with pytest.raises(NetworkPolicyError):
            await validate_external_base_url(url, settings())


async def test_network_policy_allows_explicit_private_cidr() -> None:
    value = await validate_external_base_url(
        "http://10.20.30.40:8000/v1/",
        settings(external_api_allowed_cidrs=("10.20.30.0/24",)),
    )

    assert value == "http://10.20.30.40:8000/v1"


def test_openai_usage_and_cost_payloads_are_normalized() -> None:
    records = OpenAIAdapter.parse_usage(
        {
            "data": [
                {
                    "start_time": 1_754_784_000,
                    "end_time": 1_754_870_400,
                    "results": [
                        {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "num_model_requests": 3,
                            "model": "gpt-test",
                            "api_key_id": "key-test",
                        }
                    ],
                }
            ]
        },
        {
            "data": [
                {
                    "start_time": 1_754_784_000,
                    "end_time": 1_754_870_400,
                    "results": [{"amount": {"value": 1.25, "currency": "usd"}}],
                }
            ]
        },
    )

    assert len(records) == 2
    assert records[0].request_count == 3
    assert records[0].total_tokens == 120
    assert records[0].model_id == "gpt-test"
    assert records[1].cost_amount == 1.25
    assert records[1].currency == "usd"
