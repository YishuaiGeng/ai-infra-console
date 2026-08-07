import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

import ai_infra_api.api.agent as agent_api
from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import Server, ServerAgent, User, UserRole
from ai_infra_api.services.agent_tokens import rotate_agent_token


async def provision(
    app: FastAPI,
) -> tuple[dict[str, str], dict[str, str], str, uuid.UUID]:
    admin = User(
        username="model-admin",
        password_hash=hash_password("unused-password"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    viewer = User(
        username="model-viewer",
        password_hash=hash_password("unused-password"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    server = Server(name="model-node", status="pending", type="local", tags=[])
    async with app.state.database.session_factory() as session:
        session.add_all([admin, viewer, server])
        await session.flush()
        agent = ServerAgent(server_id=server.id)
        agent_token = rotate_agent_token(agent)
        session.add(agent)
        await session.commit()
        await session.refresh(admin)
        await session.refresh(viewer)
        await session.refresh(server)
    admin_token, _ = create_access_token(admin, app.state.settings)
    viewer_token, _ = create_access_token(viewer, app.state.settings)
    return (
        {"authorization": f"Bearer {admin_token}"},
        {"authorization": f"Bearer {viewer_token}"},
        agent_token,
        server.id,
    )


def heartbeat(
    *,
    directories: list[dict[str, Any]],
    installations: list[dict[str, Any]],
    ollama_available: bool = True,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    unavailable = {"available": False, "detail": "not installed"}
    return {
        "collected_at": now.isoformat(),
        "agent_version": "0.1.0",
        "host": {
            "hostname": "model-node-host",
            "os": "Linux",
            "kernel": "6.8.0",
            "architecture": "x86_64",
            "boot_time": (now - timedelta(hours=1)).isoformat(),
            "cpu": {
                "model": "Test CPU",
                "physical_cores": 8,
                "logical_cores": 16,
                "utilization": 10,
                "load_average": [0.1, 0.2, 0.3],
            },
            "memory": {"total": 64_000, "used": 16_000, "percent": 25},
            "disks": [],
            "network": {"bytes_sent": 1, "bytes_received": 2},
            "runtimes": {
                "python": {"available": True, "version": "3.12"},
                "docker": unavailable,
                "ollama": {"available": ollama_available, "version": "0.11"},
            },
        },
        "gpus": [],
        "gpu_collector": unavailable,
        "model_inventory": {
            "collected_at": now.isoformat(),
            "directories": directories,
            "installations": installations,
            "ollama": {
                "available": ollama_available,
                "version": "api-tags" if ollama_available else None,
                "detail": None if ollama_available else "unavailable",
            },
        },
    }


def directory(*, available: bool = True, path: str = "/data/models") -> dict[str, Any]:
    return {
        "path": path,
        "is_default": True,
        "available": available,
        "error_code": None if available else "unavailable",
        "scanned_at": datetime.now(UTC).isoformat(),
    }


def installation(
    *,
    path: str = "/data/models/Qwen3-8B",
    source: str = "huggingface",
    source_id: str = "Qwen/Qwen3-8B",
    format_name: str = "safetensors",
) -> dict[str, Any]:
    return {
        "source": source,
        "source_id": source_id,
        "name": source_id,
        "display_name": "Qwen3 8B",
        "architecture": "Qwen3ForCausalLM",
        "model_type": "qwen3",
        "path": path,
        "size": 8_000,
        "format": format_name,
        "quantization": "BF16",
        "revision": "revision-1",
        "file_count": 2,
        "metadata": {"dtype": "bfloat16"},
    }


async def test_inventory_heartbeat_reads_permissions_and_reconciliation(
    app: FastAPI,
    client: AsyncClient,
    monkeypatch: Any,
) -> None:
    admin_headers, viewer_headers, agent_token, server_id = await provision(app)
    model_events: list[uuid.UUID] = []

    async def capture_model_event(_redis: object, event_server_id: uuid.UUID) -> None:
        model_events.append(event_server_id)

    monkeypatch.setattr(agent_api, "publish_model_inventory_update", capture_model_event)
    agent_headers = {"authorization": f"Bearer {agent_token}"}
    first_payload = heartbeat(
        directories=[directory()],
        installations=[
            installation(),
            installation(
                path="ollama://qwen3:8b",
                source="ollama",
                source_id="qwen3:8b",
                format_name="ollama",
            ),
        ],
    )
    first = await client.post("/api/v1/agent/register", json=first_payload, headers=agent_headers)
    assert first.status_code == 200
    assert model_events == [server_id]

    repeated = await client.post(
        "/api/v1/agent/heartbeat",
        json=first_payload,
        headers=agent_headers,
    )
    assert repeated.status_code == 200
    assert model_events == [server_id]

    viewer_models = await client.get("/api/v1/models", headers=viewer_headers)
    assert viewer_models.status_code == 200
    assert len(viewer_models.json()) == 2
    assert viewer_models.json()[0]["server"]["name"] == "model-node"
    assert "token" not in str(viewer_models.json()).lower()

    filtered = await client.get(
        "/api/v1/models?format=ollama&search=qwen3",
        headers=viewer_headers,
    )
    assert filtered.status_code == 200
    assert [item["format"] for item in filtered.json()] == ["ollama"]

    summary = await client.get("/api/v1/model-inventory/summary", headers=viewer_headers)
    assert summary.status_code == 200
    assert summary.json()["model_count"] == 2
    assert summary.json()["installation_count"] == 2

    server_detail = await client.get(f"/api/v1/servers/{server_id}", headers=viewer_headers)
    assert server_detail.status_code == 200
    assert server_detail.json()["model_count"] == 2
    assert len(server_detail.json()["models"]) == 2
    assert len(server_detail.json()["model_directories"]) == 1

    directories = await client.get(
        f"/api/v1/servers/{server_id}/model-directories",
        headers=viewer_headers,
    )
    directory_id = directories.json()[0]["id"]
    denied = await client.put(
        f"/api/v1/servers/{server_id}/model-directories/default",
        json={"directory_id": directory_id},
        headers=viewer_headers,
    )
    assert denied.status_code == 403
    changed = await client.put(
        f"/api/v1/servers/{server_id}/model-directories/default",
        json={"directory_id": directory_id},
        headers=admin_headers,
    )
    assert changed.status_code == 200
    assert changed.json()["is_default"] is True
    invalid = await client.put(
        f"/api/v1/servers/{server_id}/model-directories/default",
        json={"directory_id": str(uuid.uuid4())},
        headers=admin_headers,
    )
    assert invalid.status_code == 422

    failed_scan = heartbeat(
        directories=[directory(available=False)],
        installations=[],
        ollama_available=False,
    )
    assert (
        await client.post(
            "/api/v1/agent/heartbeat",
            json=failed_scan,
            headers=agent_headers,
        )
    ).status_code == 200
    stale = (await client.get("/api/v1/models", headers=viewer_headers)).json()
    assert {item["status"] for item in stale} == {"stale"}
    unavailable_default = await client.put(
        f"/api/v1/servers/{server_id}/model-directories/default",
        json={"directory_id": directory_id},
        headers=admin_headers,
    )
    assert unavailable_default.status_code == 422
    assert unavailable_default.json()["error"]["code"] == "model_directory_not_selectable"

    recovered_empty = heartbeat(
        directories=[directory()],
        installations=[],
        ollama_available=True,
    )
    assert (
        await client.post(
            "/api/v1/agent/heartbeat",
            json=recovered_empty,
            headers=agent_headers,
        )
    ).status_code == 200
    missing = (await client.get("/api/v1/models", headers=viewer_headers)).json()
    assert {item["status"] for item in missing} == {"missing"}


async def test_same_logical_model_has_distinct_server_locations(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    admin_headers, viewer_headers, agent_token, _ = await provision(app)
    first = heartbeat(directories=[directory()], installations=[installation()])
    assert (
        await client.post(
            "/api/v1/agent/register",
            json=first,
            headers={"authorization": f"Bearer {agent_token}"},
        )
    ).status_code == 200

    registration = await client.post(
        "/api/v1/servers/registrations",
        json={"name": "model-node-two", "tags": []},
        headers=admin_headers,
    )
    assert registration.status_code == 201
    second_payload = heartbeat(
        directories=[directory(path="/mnt/models")],
        installations=[installation(path="/mnt/models/Qwen3-8B")],
    )
    second_payload["host"]["hostname"] = "model-node-two-host"
    assert (
        await client.post(
            "/api/v1/agent/register",
            json=second_payload,
            headers={"authorization": f"Bearer {registration.json()['registration_token']}"},
        )
    ).status_code == 200

    models = (await client.get("/api/v1/models", headers=viewer_headers)).json()
    assert len(models) == 2
    assert len({item["model_id"] for item in models}) == 1
    detail = await client.get(f"/api/v1/models/{models[0]['model_id']}", headers=viewer_headers)
    assert detail.status_code == 200
    assert {item["server"]["name"] for item in detail.json()["locations"]} == {
        "model-node",
        "model-node-two",
    }
