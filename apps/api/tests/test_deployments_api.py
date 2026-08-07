import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import ModelFile, Server, ServerAgent, User, UserRole
from ai_infra_api.services.agent_tokens import rotate_agent_token


def deployment_snapshot(hostname: str, root: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    unavailable = {"available": False, "detail": "not installed"}
    return {
        "collected_at": now.isoformat(),
        "agent_version": "0.1.0-phase6-test",
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
                "docker": {"available": True, "version": "27.0"},
                "ollama": unavailable,
                "deployment_enabled": True,
            },
        },
        "gpus": [
            {
                "index": 0,
                "uuid": f"GPU-{hostname}-0",
                "name": "NVIDIA Test GPU",
                "memory_total": 24_000,
                "memory_used": 2_000,
                "utilization": 5,
                "temperature": 40,
                "power_usage": 30,
                "power_limit": 300,
                "fan_speed": 20,
                "driver_version": "570",
                "cuda_version": "12.8",
                "status": "available",
                "processes": [],
            }
        ],
        "gpu_collector": {"available": True, "version": "test"},
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
                    "source_id": "Qwen/Qwen3-8B",
                    "name": "Qwen/Qwen3-8B",
                    "display_name": "Qwen3-8B",
                    "architecture": "QwenForCausalLM",
                    "model_type": "qwen",
                    "path": f"{root}/Qwen/Qwen3-8B",
                    "size": 1_000,
                    "format": "safetensors",
                    "quantization": "BF16",
                    "revision": "main",
                    "file_count": 2,
                    "metadata": {},
                }
            ],
            "ollama": unavailable,
        },
    }


async def provision_deployments(
    app: FastAPI,
    client: AsyncClient,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], str]:
    app.state.settings.mutable_server_names = ("xiao-pro6000",)
    admin = User(
        username="deployment-admin",
        password_hash=hash_password("unused-password"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    viewer = User(
        username="deployment-viewer",
        password_hash=hash_password("unused-password"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    server = Server(
        name="xiao-pro6000",
        host="10.20.0.60",
        status="pending",
        type="local",
        tags=[],
    )
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
    agent_headers = {"authorization": f"Bearer {agent_token}"}
    registered = await client.post(
        "/api/v1/agent/register",
        json=deployment_snapshot("xiao-pro6000-host", "/models"),
        headers=agent_headers,
    )
    assert registered.status_code == 200
    return (
        {"authorization": f"Bearer {admin_token}"},
        {"authorization": f"Bearer {viewer_token}"},
        agent_headers,
        str(server.id),
    )


async def test_deployment_lifecycle_health_logs_and_permissions(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    admin, viewer, agent, server_id = await provision_deployments(app, client)
    targets = await client.get("/api/v1/deployment-targets", headers=viewer)
    assert targets.status_code == 200
    target = targets.json()[0]
    assert target["server"]["id"] == server_id
    assert target["docker_available"] is True
    assert target["docker_version"] == "27.0"
    model_file_id = target["model_files"][0]["model_file_id"]
    gpu_id = target["gpus"][0]["id"]
    payload = {
        "name": "qwen3-8b-test",
        "model_file_id": model_file_id,
        "selection_mode": "automatic",
        "gpu_ids": [],
        "port": 8001,
        "config": {
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.8,
            "max_model_length": 8192,
            "data_type": "float16",
            "trust_remote_code": False,
            "extra_arguments": ["--enable-prefix-caching"],
        },
    }
    viewer_response = await client.post(
        "/api/v1/deployments",
        json=payload,
        headers=viewer,
    )
    assert viewer_response.status_code == 403
    created = await client.post("/api/v1/deployments", json=payload, headers=admin)
    assert created.status_code == 201
    deployment = created.json()
    deployment_id = deployment["id"]
    assert deployment["status"] == "queued"
    assert deployment["gpus"][0]["id"] == gpu_id
    assert deployment["endpoint"] == "http://10.20.0.60:8001/v1"
    assert "container" not in str(deployment).lower()

    duplicate = await client.post(
        "/api/v1/deployments",
        json={**payload, "name": "qwen3-8b-other"},
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "deployment_port_conflict"

    claim = await client.post("/api/v1/agent/deployment-tasks/claim", headers=agent)
    assert claim.status_code == 200
    command = claim.json()["task"]
    assert command["kind"] == "create"
    assert command["model_path"] == "/models/Qwen/Qwen3-8B"
    assert command["gpu_indexes"] == [0]
    assert command["image"] == app.state.settings.vllm_image
    assert (
        await client.post("/api/v1/agent/deployment-tasks/claim", headers=agent)
    ).json()["task"] is None

    bad_lease = await client.post(
        f"/api/v1/agent/deployment-operations/{command['operation_id']}/progress",
        headers=agent,
        json={"lease_token": "x" * 40, "generation": 1},
    )
    assert bad_lease.status_code == 409
    completed = await client.post(
        f"/api/v1/agent/deployment-operations/{command['operation_id']}/complete",
        headers=agent,
        json={
            "lease_token": command["lease_token"],
            "generation": 1,
            "outcome": "completed",
            "observed_state": "running",
            "container_id": "fixture-container-id",
        },
    )
    assert completed.status_code == 204
    detail = (await client.get(f"/api/v1/deployments/{deployment_id}", headers=viewer)).json()
    assert detail["status"] == "running"

    expected = await client.post("/api/v1/agent/deployment-runtimes/expected", headers=agent)
    assert expected.status_code == 200
    assert expected.json()[0]["deployment_id"] == deployment_id
    runtime_report = await client.post(
        "/api/v1/agent/deployment-runtimes/report",
        headers=agent,
        json={
            "observations": [
                {
                    "deployment_id": deployment_id,
                    "generation": 1,
                    "container_id": "fixture-container-id",
                    "state": "running",
                    "exit_code": 0,
                    "health_status": "healthy",
                    "health_latency_ms": 3.5,
                    "checked_at": datetime.now(UTC).isoformat(),
                    "logs": [
                        {
                            "sequence": 1,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "stream": "stdout",
                            "message": "INFO runtime ready\u001b[0m",
                        }
                    ],
                }
            ]
        },
    )
    assert runtime_report.status_code == 204
    detail = (await client.get(f"/api/v1/deployments/{deployment_id}", headers=viewer)).json()
    assert detail["health_status"] == "healthy"
    logs = await client.get(f"/api/v1/deployments/{deployment_id}/logs", headers=viewer)
    assert logs.status_code == 200
    assert logs.json()[0]["message"] == "INFO runtime ready [0m"

    stop = await client.post(f"/api/v1/deployments/{deployment_id}/stop", headers=admin)
    assert stop.status_code == 200
    stop_command = (
        await client.post("/api/v1/agent/deployment-tasks/claim", headers=agent)
    ).json()["task"]
    assert stop_command["kind"] == "stop"
    stopped = await client.post(
        f"/api/v1/agent/deployment-operations/{stop_command['operation_id']}/complete",
        headers=agent,
        json={
            "lease_token": stop_command["lease_token"],
            "generation": 1,
            "outcome": "completed",
            "observed_state": "stopped",
            "container_id": "fixture-container-id",
        },
    )
    assert stopped.status_code == 204
    assert (
        await client.get(f"/api/v1/deployments/{deployment_id}", headers=viewer)
    ).json()["status"] == "stopped"

    bad_confirm = await client.request(
        "DELETE",
        f"/api/v1/deployments/{deployment_id}",
        headers=admin,
        json={"confirmation": "wrong"},
    )
    assert bad_confirm.status_code == 422
    assert (
        await client.request(
            "DELETE",
            f"/api/v1/deployments/{deployment_id}",
            headers=viewer,
            json={"confirmation": "qwen3-8b-test"},
        )
    ).status_code == 403
    queued_delete = await client.request(
        "DELETE",
        f"/api/v1/deployments/{deployment_id}",
        headers=admin,
        json={"confirmation": "qwen3-8b-test"},
    )
    assert queued_delete.status_code == 200
    delete_command = (
        await client.post("/api/v1/agent/deployment-tasks/claim", headers=agent)
    ).json()["task"]
    assert delete_command["kind"] == "delete"
    deleted = await client.post(
        f"/api/v1/agent/deployment-operations/{delete_command['operation_id']}/complete",
        headers=agent,
        json={
            "lease_token": delete_command["lease_token"],
            "generation": 1,
            "outcome": "completed",
            "observed_state": "missing",
        },
    )
    assert deleted.status_code == 204
    assert (
        await client.get(f"/api/v1/deployments/{deployment_id}", headers=viewer)
    ).status_code == 404
    async with app.state.database.session_factory() as session:
        model_file = await session.get(ModelFile, uuid.UUID(model_file_id))
        assert model_file is not None
        assert model_file.status == "discovered"


async def test_manual_placement_validation_and_argument_policy(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    admin, _viewer, _agent, _server_id = await provision_deployments(app, client)
    target = (await client.get("/api/v1/deployment-targets", headers=admin)).json()[0]
    model_file_id = target["model_files"][0]["model_file_id"]
    gpu_id = target["gpus"][0]["id"]
    invalid_argument = await client.post(
        "/api/v1/deployments",
        headers=admin,
        json={
            "name": "unsafe-arguments",
            "model_file_id": model_file_id,
            "selection_mode": "manual",
            "gpu_ids": [gpu_id],
            "port": 8002,
            "config": {
                "tensor_parallel_size": 1,
                "gpu_memory_utilization": 0.9,
                "max_model_length": 4096,
                "data_type": "auto",
                "trust_remote_code": False,
                "extra_arguments": ["--model", "/etc"],
            },
        },
    )
    assert invalid_argument.status_code == 422
    assert invalid_argument.json()["error"]["code"] == "unsupported_vllm_argument"
