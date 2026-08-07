import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import (
    Deployment,
    ModelDownloadTask,
    Server,
    ServerAgent,
    User,
    UserRole,
)
from ai_infra_api.services.agent_tokens import rotate_agent_token


def snapshot(hostname: str, root: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    unavailable = {"available": False, "detail": "not installed"}
    return {
        "collected_at": now.isoformat(),
        "agent_version": "0.1.0-phase5-test",
        "host": {
            "hostname": hostname,
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
                "ollama": unavailable,
            },
        },
        "gpus": [],
        "gpu_collector": unavailable,
        "model_inventory": {
            "collected_at": now.isoformat(),
            "directories": [
                {
                    "path": root,
                    "is_default": True,
                    "available": True,
                    "error_code": None,
                    "scanned_at": now.isoformat(),
                }
            ],
            "installations": [
                {
                    "source": "huggingface",
                    "source_id": "Qwen/Existing-1B",
                    "name": "Qwen/Existing-1B",
                    "display_name": "Existing-1B",
                    "architecture": "QwenForCausalLM",
                    "model_type": "qwen",
                    "path": f"{root}/Qwen/Existing-1B",
                    "size": 1_000,
                    "format": "safetensors",
                    "quantization": "BF16",
                    "revision": "existing-revision",
                    "file_count": 2,
                    "metadata": {},
                }
            ],
            "ollama": unavailable,
        },
    }


async def provision(
    app: FastAPI,
    client: AsyncClient,
) -> tuple[
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    str,
    str,
]:
    app.state.settings.mutable_server_names = ("xiao-pro6000", "xiao-cpu")
    admin = User(
        username="task-admin",
        password_hash=hash_password("unused-password"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    viewer = User(
        username="task-viewer",
        password_hash=hash_password("unused-password"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    primary = Server(name="xiao-pro6000", status="pending", type="local", tags=[])
    backup = Server(name="asus-4090", status="pending", type="local", tags=[])
    async with app.state.database.session_factory() as session:
        session.add_all([admin, viewer, primary, backup])
        await session.flush()
        primary_agent = ServerAgent(server_id=primary.id)
        primary_token = rotate_agent_token(primary_agent)
        backup_agent = ServerAgent(server_id=backup.id)
        backup_token = rotate_agent_token(backup_agent)
        session.add_all([primary_agent, backup_agent])
        await session.commit()
        await session.refresh(admin)
        await session.refresh(viewer)
        await session.refresh(primary)
        await session.refresh(backup)
    admin_token, _ = create_access_token(admin, app.state.settings)
    viewer_token, _ = create_access_token(viewer, app.state.settings)
    primary_headers = {"authorization": f"Bearer {primary_token}"}
    backup_headers = {"authorization": f"Bearer {backup_token}"}
    assert (
        await client.post(
            "/api/v1/agent/register",
            json=snapshot("xiao-pro6000-host", "/data/models"),
            headers=primary_headers,
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/agent/register",
            json=snapshot("asus-4090-host", "/backup/models"),
            headers=backup_headers,
        )
    ).status_code == 200
    return (
        {"authorization": f"Bearer {admin_token}"},
        {"authorization": f"Bearer {viewer_token}"},
        primary_headers,
        backup_headers,
        str(primary.id),
        str(backup.id),
    )


async def test_download_lifecycle_permissions_and_backup_policy(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    (
        admin_headers,
        viewer_headers,
        agent_headers,
        backup_agent_headers,
        server_id,
        backup_id,
    ) = await provision(app, client)
    directories = (
        await client.get(
            f"/api/v1/servers/{server_id}/model-directories",
            headers=viewer_headers,
        )
    ).json()
    directory_id = directories[0]["id"]
    targets = await client.get("/api/v1/download-targets", headers=viewer_headers)
    assert targets.status_code == 200
    assert [target["server"]["id"] for target in targets.json()] == [server_id]
    payload = {
        "provider": "huggingface",
        "source_id": "Qwen/Qwen3-8B",
        "revision": "revision-a",
        "server_id": server_id,
        "directory_id": directory_id,
    }
    denied = await client.post("/api/v1/downloads", json=payload, headers=viewer_headers)
    assert denied.status_code == 403
    created = await client.post("/api/v1/downloads", json=payload, headers=admin_headers)
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "queued"
    assert task["target_path"] == "/data/models/huggingface/Qwen/Qwen3-8B"
    assert "token" not in str(task).lower()

    duplicate = await client.post("/api/v1/downloads", json=payload, headers=admin_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "download_already_active"

    backup_directories = (
        await client.get(
            f"/api/v1/servers/{backup_id}/model-directories",
            headers=viewer_headers,
        )
    ).json()
    backup_payload = {
        **payload,
        "server_id": backup_id,
        "directory_id": backup_directories[0]["id"],
    }
    backup_denied = await client.post(
        "/api/v1/downloads", json=backup_payload, headers=admin_headers
    )
    assert backup_denied.status_code == 422
    assert backup_denied.json()["error"]["code"] == "server_mutation_not_allowed"

    claim = await client.post("/api/v1/agent/model-tasks/claim", headers=agent_headers)
    assert claim.status_code == 200
    command = claim.json()["task"]
    assert command["kind"] == "download"
    assert command["source_id"] == "Qwen/Qwen3-8B"
    assert "lease_token" in command
    assert (await client.post("/api/v1/agent/model-tasks/claim", headers=agent_headers)).json()[
        "task"
    ] is None

    cross_server = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=backup_agent_headers,
        json={
            "lease_token": command["lease_token"],
            "downloaded_size": 1,
            "total_size": 100,
        },
    )
    assert cross_server.status_code == 404

    async with app.state.database.session_factory() as session:
        leased_task = await session.get(ModelDownloadTask, uuid.UUID(task["id"]))
        assert leased_task is not None
        leased_task.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    reclaimed = (
        await client.post("/api/v1/agent/model-tasks/claim", headers=agent_headers)
    ).json()["task"]
    assert reclaimed["task_id"] == task["id"]
    assert reclaimed["lease_token"] != command["lease_token"]
    stale_claim = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=agent_headers,
        json={
            "lease_token": command["lease_token"],
            "downloaded_size": 1,
            "total_size": 100,
        },
    )
    assert stale_claim.status_code == 409
    command = reclaimed

    bad_lease = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=agent_headers,
        json={
            "lease_token": "x" * 40,
            "downloaded_size": 10,
            "total_size": 100,
            "speed_bytes_per_second": 10,
        },
    )
    assert bad_lease.status_code == 409
    progress = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=agent_headers,
        json={
            "lease_token": command["lease_token"],
            "downloaded_size": 10,
            "total_size": 100,
            "speed_bytes_per_second": 10,
        },
    )
    assert progress.status_code == 200
    regressed = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=agent_headers,
        json={
            "lease_token": command["lease_token"],
            "downloaded_size": 9,
            "total_size": 100,
        },
    )
    assert regressed.status_code == 409

    cancelling = await client.post(
        f"/api/v1/downloads/{task['id']}/cancel",
        headers=admin_headers,
    )
    assert cancelling.json()["status"] == "cancelling"
    cancel_signal = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/progress",
        headers=agent_headers,
        json={
            "lease_token": command["lease_token"],
            "downloaded_size": 20,
            "total_size": 100,
        },
    )
    assert cancel_signal.json()["cancel_requested"] is True
    terminal = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/complete",
        headers=agent_headers,
        json={
            "lease_token": command["lease_token"],
            "outcome": "cancelled",
            "downloaded_size": 20,
            "total_size": 100,
        },
    )
    assert terminal.status_code == 204
    retry = await client.post(
        f"/api/v1/downloads/{task['id']}/retry",
        headers=admin_headers,
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "queued"
    second_claim = (
        await client.post("/api/v1/agent/model-tasks/claim", headers=agent_headers)
    ).json()["task"]
    assert second_claim["task_id"] == task["id"]
    wrong_path = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/complete",
        headers=agent_headers,
        json={
            "lease_token": second_claim["lease_token"],
            "outcome": "completed",
            "downloaded_size": 100,
            "total_size": 100,
            "final_path": "/outside/model",
        },
    )
    assert wrong_path.status_code == 409
    completed = await client.post(
        f"/api/v1/agent/download-tasks/{task['id']}/complete",
        headers=agent_headers,
        json={
            "lease_token": second_claim["lease_token"],
            "outcome": "completed",
            "downloaded_size": 100,
            "total_size": 100,
            "final_path": task["target_path"],
        },
    )
    assert completed.status_code == 204
    detail = await client.get(f"/api/v1/downloads/{task['id']}", headers=viewer_headers)
    assert detail.json()["status"] == "completed"
    assert detail.json()["progress"] == 100.0
    not_cancellable = await client.post(
        f"/api/v1/downloads/{task['id']}/cancel",
        headers=admin_headers,
    )
    assert not_cancellable.status_code == 422
    filtered = await client.get(
        "/api/v1/downloads?status=completed&search=Qwen",
        headers=viewer_headers,
    )
    assert [item["id"] for item in filtered.json()] == [task["id"]]


async def test_delete_requires_confirmation_and_rejects_deployed_model(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    admin_headers, viewer_headers, agent_headers, _, server_id, _ = await provision(app, client)
    installation = (
        await client.get(
            f"/api/v1/models?server_id={server_id}",
            headers=viewer_headers,
        )
    ).json()[0]
    model_file_id = installation["id"]
    denied = await client.post(
        f"/api/v1/model-files/{model_file_id}/delete",
        json={"confirmation": "Qwen/Existing-1B"},
        headers=viewer_headers,
    )
    assert denied.status_code == 403
    mismatch = await client.post(
        f"/api/v1/model-files/{model_file_id}/delete",
        json={"confirmation": "wrong/model"},
        headers=admin_headers,
    )
    assert mismatch.status_code == 422

    async with app.state.database.session_factory() as session:
        deployment = Deployment(
            name="deletion-blocker",
            model_file_id=uuid.UUID(model_file_id),
            server_id=uuid.UUID(server_id),
            backend="vllm",
            status="stopped",
            port=19001,
            config={},
        )
        session.add(deployment)
        await session.commit()
        deployment_id = deployment.id
    in_use = await client.post(
        f"/api/v1/model-files/{model_file_id}/delete",
        json={"confirmation": "Qwen/Existing-1B"},
        headers=admin_headers,
    )
    assert in_use.status_code == 409
    assert in_use.json()["error"]["code"] == "model_installation_in_use"
    async with app.state.database.session_factory() as session:
        deployment = await session.get(Deployment, deployment_id)
        assert deployment is not None
        await session.delete(deployment)
        await session.commit()

    queued = await client.post(
        f"/api/v1/model-files/{model_file_id}/delete",
        json={"confirmation": "Qwen/Existing-1B"},
        headers=admin_headers,
    )
    assert queued.status_code == 202
    delete_task = queued.json()
    claim = (await client.post("/api/v1/agent/model-tasks/claim", headers=agent_headers)).json()[
        "task"
    ]
    assert claim["kind"] == "delete"
    assert claim["target_path"] == "/data/models/Qwen/Existing-1B"
    completed = await client.post(
        f"/api/v1/agent/delete-tasks/{delete_task['id']}/complete",
        headers=agent_headers,
        json={"lease_token": claim["lease_token"], "outcome": "completed"},
    )
    assert completed.status_code == 204
    detail = await client.get(
        f"/api/v1/model-deletions/{delete_task['id']}",
        headers=viewer_headers,
    )
    assert detail.json()["status"] == "completed"
    models = await client.get(f"/api/v1/models?server_id={server_id}", headers=viewer_headers)
    assert models.json()[0]["status"] == "missing"
