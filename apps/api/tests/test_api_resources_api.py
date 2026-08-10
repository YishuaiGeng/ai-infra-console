from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import User, UserRole


async def headers_for(app: FastAPI, role: UserRole, username: str) -> dict[str, str]:
    user = User(
        username=username,
        password_hash=hash_password("unused-password"),
        role=role,
        is_active=True,
    )
    async with app.state.database.session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    token, _ = create_access_token(user, app.state.settings)
    return {"authorization": f"Bearer {token}"}


async def test_api_resource_account_credentials_usage_and_permissions(
    app: FastAPI, client: AsyncClient
) -> None:
    admin_headers = await headers_for(app, UserRole.ADMIN, "api-resource-admin")
    viewer_headers = await headers_for(app, UserRole.VIEWER, "api-resource-viewer")

    providers = await client.get("/api/v1/api-resources/providers", headers=viewer_headers)
    assert providers.status_code == 200
    assert {item["slug"] for item in providers.json()} == {
        "openai",
        "codex",
        "anthropic",
        "claude-code",
        "aliyun-bailian",
        "generic-openai",
    }
    anthropic = next(item for item in providers.json() if item["slug"] == "anthropic")
    assert anthropic["adapter_kind"] == "anthropic"
    assert anthropic["credential_header"] == "x-api-key"
    assert anthropic["static_headers"] == {"anthropic-version": "2023-06-01"}

    provider_denied = await client.post(
        "/api/v1/api-resources/providers",
        headers=viewer_headers,
        json={"slug": "viewer-provider", "display_name": "Denied"},
    )
    assert provider_denied.status_code == 403

    custom_provider = await client.post(
        "/api/v1/api-resources/providers",
        headers=admin_headers,
        json={
            "slug": "internal-claude",
            "display_name": "Internal Claude Gateway",
            "adapter_kind": "anthropic",
            "default_base_url": "https://8.8.4.4/v1",
            "credential_header": "x-api-key",
            "static_headers": {"anthropic-version": "2023-06-01"},
            "capabilities": {
                "credential_validation": True,
                "model_discovery": True,
                "balance_sync": False,
                "usage_sync": False,
                "usage_by_model": False,
                "usage_by_credential": False,
                "manual_usage_import": True,
            },
        },
    )
    assert custom_provider.status_code == 201, custom_provider.text
    assert custom_provider.json()["provider_type"] == "custom"

    updated_provider = await client.patch(
        "/api/v1/api-resources/providers/internal-claude",
        headers=admin_headers,
        json={
            "display_name": "Claude Gateway",
            "is_enabled": False,
            "capabilities": {
                "credential_validation": True,
                "model_discovery": True,
                "balance_sync": False,
                "usage_sync": True,
                "usage_by_model": True,
                "usage_by_credential": True,
                "manual_usage_import": True,
            },
        },
    )
    assert updated_provider.status_code == 200, updated_provider.text
    assert updated_provider.json()["display_name"] == "Claude Gateway"
    assert updated_provider.json()["is_enabled"] is False
    assert updated_provider.json()["capabilities"]["usage_sync"] is True

    unsafe_provider = await client.post(
        "/api/v1/api-resources/providers",
        headers=admin_headers,
        json={
            "slug": "unsafe-provider",
            "display_name": "Unsafe",
            "static_headers": {"Authorization": "secret"},
        },
    )
    assert unsafe_provider.status_code == 422

    denied = await client.post(
        "/api/v1/api-resources/accounts",
        headers=viewer_headers,
        json={"provider_slug": "openai", "name": "Denied"},
    )
    assert denied.status_code == 403

    created = await client.post(
        "/api/v1/api-resources/accounts",
        headers=admin_headers,
        json={
            "provider_slug": "openai",
            "name": "Research API",
            "purpose": "Model evaluation",
            "owner": "AI Platform",
            "base_url": "https://8.8.8.8/v1",
            "billing_currency": "USD",
            "monthly_budget": 200,
            "tags": ["research", "external", "research"],
            "credential_name": "Primary",
            "credential_value": "sk-super-secret-value",
        },
    )
    assert created.status_code == 201, created.text
    account = created.json()
    account_id = account["id"]
    assert account["credential_count"] == 1
    assert account["tags"] == ["research", "external"]
    assert "credential_value" not in created.text
    assert "sk-super-secret-value" not in created.text

    credentials = await client.get(
        f"/api/v1/api-resources/accounts/{account_id}/credentials", headers=viewer_headers
    )
    assert credentials.status_code == 200
    credential = credentials.json()[0]
    assert credential["masked_value"] == "sk-s****alue"
    assert "encrypted_value" not in credential
    assert "fingerprint" not in credential

    duplicate = await client.post(
        f"/api/v1/api-resources/accounts/{account_id}/credentials",
        headers=admin_headers,
        json={"name": "Duplicate", "value": "sk-super-secret-value"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "api_credential_duplicate"

    now = datetime.now(UTC)
    usage = await client.post(
        f"/api/v1/api-resources/accounts/{account_id}/usage/manual",
        headers=admin_headers,
        json={
            "period_start": (now - timedelta(days=1)).isoformat(),
            "period_end": now.isoformat(),
            "request_count": 12,
            "input_tokens": 1000,
            "output_tokens": 250,
            "total_tokens": 1250,
            "cost_amount": 1.25,
            "currency": "USD",
        },
    )
    assert usage.status_code == 201, usage.text
    summary = await client.get("/api/v1/api-resources/usage/summary", headers=viewer_headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "account_count": 1,
        "request_count": 12,
        "input_tokens": 1000,
        "output_tokens": 250,
        "total_tokens": 1250,
        "costs_by_currency": {"USD": 1.25},
    }

    archived = await client.post(
        f"/api/v1/api-resources/accounts/{account_id}/archive", headers=admin_headers
    )
    assert archived.status_code == 200
    visible = await client.get("/api/v1/api-resources/accounts", headers=viewer_headers)
    assert visible.json() == []
    all_accounts = await client.get(
        "/api/v1/api-resources/accounts?include_archived=true", headers=viewer_headers
    )
    assert all_accounts.json()[0]["status"] == "archived"


async def test_api_resource_manual_model_and_balance(app: FastAPI, client: AsyncClient) -> None:
    headers = await headers_for(app, UserRole.ADMIN, "api-resource-model-admin")
    created = await client.post(
        "/api/v1/api-resources/accounts",
        headers=headers,
        json={
            "provider_slug": "generic-openai",
            "name": "Internal compatible API",
            "base_url": "https://8.8.4.4/v1",
        },
    )
    account_id = created.json()["id"]

    model = await client.post(
        f"/api/v1/api-resources/accounts/{account_id}/models/manual",
        headers=headers,
        json={
            "provider_model_id": "Qwen/Qwen3-32B",
            "display_name": "Qwen3 32B",
            "capabilities": ["chat"],
            "context_window": 32768,
        },
    )
    assert model.status_code == 201
    assert model.json()["source"] == "manual"

    balance = await client.post(
        f"/api/v1/api-resources/accounts/{account_id}/balance/manual",
        headers=headers,
        json={"balance_amount": 42.5, "currency": "USD"},
    )
    assert balance.status_code == 201
    detail = await client.get(f"/api/v1/api-resources/accounts/{account_id}", headers=headers)
    assert detail.json()["model_count"] == 1
    assert detail.json()["latest_balance"] == 42.5
