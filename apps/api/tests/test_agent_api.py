import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import (
    GPU,
    AuditLog,
    GPUMetric,
    GPUProcess,
    Server,
    ServerAgent,
    ServerMetric,
    User,
    UserRole,
)


async def user_headers(app: FastAPI, *, role: UserRole = UserRole.ADMIN) -> dict[str, str]:
    user = User(
        username=f"{role.value}-user",
        password_hash=hash_password("not-used"),
        role=role,
        is_active=True,
    )
    async with app.state.database.session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    token, _ = create_access_token(user, app.state.settings)
    return {"authorization": f"Bearer {token}"}


def agent_headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def snapshot_payload(*, hostname: str = "agent-node", process_pid: int = 1200) -> dict[str, Any]:
    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "agent_version": "0.1.0",
        "host": {
            "hostname": hostname,
            "os": "Linux",
            "kernel": "6.8.0",
            "architecture": "x86_64",
            "boot_time": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            "cpu": {
                "model": "Test CPU",
                "physical_cores": 8,
                "logical_cores": 16,
                "utilization": 25.5,
                "load_average": [0.5, 0.4, 0.3],
            },
            "memory": {"total": 64_000, "used": 32_000, "percent": 50},
            "disks": [
                {
                    "mountpoint": "/",
                    "filesystem": "ext4",
                    "total": 1_000_000,
                    "used": 400_000,
                    "percent": 40,
                }
            ],
            "network": {"bytes_sent": 1000, "bytes_received": 2000},
            "runtimes": {
                "python": {"available": True, "version": "3.12.0"},
                "docker": {"available": True, "version": "27.0.0"},
                "ollama": {"available": False, "detail": "not installed"},
            },
        },
        "gpus": [
            {
                "index": 0,
                "uuid": "GPU-test-0",
                "name": "NVIDIA Test GPU",
                "memory_total": 24_000,
                "memory_used": 12_000,
                "utilization": 50,
                "temperature": 62,
                "power_usage": 250,
                "power_limit": 450,
                "fan_speed": 40,
                "driver_version": "580.00",
                "cuda_version": "13.0",
                "processes": [
                    {
                        "pid": process_pid,
                        "username": "researcher",
                        "command": "python",
                        "memory_used": 10_000,
                    }
                ],
            }
        ],
        "gpu_collector": {"available": True, "version": "NVML 13"},
    }


async def create_registration(
    client: AsyncClient, app: FastAPI, *, name: str = "test-server"
) -> tuple[uuid.UUID, str, dict[str, str]]:
    headers = await user_headers(app)
    response = await client.post(
        "/api/v1/servers/registrations",
        headers=headers,
        json={"name": name, "type": "local", "tags": ["test"]},
    )
    assert response.status_code == 201
    return (
        uuid.UUID(response.json()["server_id"]),
        response.json()["registration_token"],
        headers,
    )


async def test_registration_heartbeat_and_plaintext_token_absence(
    client: AsyncClient, app: FastAPI
) -> None:
    server_id, token, _ = await create_registration(client, app)

    registered = await client.post(
        "/api/v1/agent/register",
        headers=agent_headers(token),
        json=snapshot_payload(),
    )

    assert registered.status_code == 200
    assert registered.json() == {
        "server_id": str(server_id),
        "status": "online",
        "offline_after_seconds": 30,
    }
    async with app.state.database.session_factory() as session:
        server = await session.get(Server, server_id)
        agent = await session.scalar(select(ServerAgent).where(ServerAgent.server_id == server_id))
        metric = await session.scalar(
            select(ServerMetric).where(ServerMetric.server_id == server_id)
        )
        gpu = await session.scalar(select(GPU).where(GPU.server_id == server_id))
        process = await session.scalar(select(GPUProcess))
        audit = await session.scalar(
            select(AuditLog).where(AuditLog.action == "agent.registration.created")
        )
        assert server is not None and server.status == "online"
        assert server.hostname == "agent-node"
        assert agent is not None and agent.token_hash not in {None, token}
        assert token not in repr(agent.__dict__)
        assert metric is not None and metric.memory_used == 32_000
        assert gpu is not None and gpu.uuid == "GPU-test-0"
        assert process is not None and process.pid == 1200
        assert audit is not None and token not in repr(audit.details)


async def test_repeated_heartbeat_replaces_processes_and_keeps_gpu_identity(
    client: AsyncClient, app: FastAPI
) -> None:
    _, token, _ = await create_registration(client, app)
    first = await client.post(
        "/api/v1/agent/register", headers=agent_headers(token), json=snapshot_payload()
    )
    second = await client.post(
        "/api/v1/agent/heartbeat",
        headers=agent_headers(token),
        json=snapshot_payload(process_pid=2200),
    )

    assert first.status_code == second.status_code == 200
    async with app.state.database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(GPU)) == 1
        assert await session.scalar(select(func.count()).select_from(GPUMetric)) == 2
        processes = list(await session.scalars(select(GPUProcess)))
        assert [item.pid for item in processes] == [2200]


async def test_gpu_replacement_reuses_slot_and_deduplicates_processes(
    client: AsyncClient, app: FastAPI
) -> None:
    _, token, _ = await create_registration(client, app)
    await client.post(
        "/api/v1/agent/register", headers=agent_headers(token), json=snapshot_payload()
    )
    replacement = snapshot_payload(process_pid=3300)
    replacement_gpu = replacement["gpus"][0]
    replacement_gpu["uuid"] = "GPU-replacement"
    replacement_gpu["processes"].append(
        {
            "pid": 3300,
            "username": "researcher",
            "command": "python",
            "memory_used": 12_000,
        }
    )

    response = await client.post(
        "/api/v1/agent/heartbeat", headers=agent_headers(token), json=replacement
    )

    assert response.status_code == 200
    async with app.state.database.session_factory() as session:
        gpus = list(await session.scalars(select(GPU)))
        processes = list(await session.scalars(select(GPUProcess)))
        assert len(gpus) == 1
        assert gpus[0].uuid == "GPU-replacement"
        assert len(processes) == 1
        assert processes[0].memory_used == 12_000


async def test_rotation_and_revocation_invalidate_old_tokens(
    client: AsyncClient, app: FastAPI
) -> None:
    server_id, first_token, admin_headers = await create_registration(client, app)
    rotated = await client.post(f"/api/v1/servers/{server_id}/agent-token", headers=admin_headers)
    second_token = rotated.json()["registration_token"]

    old_attempt = await client.post(
        "/api/v1/agent/register",
        headers=agent_headers(first_token),
        json=snapshot_payload(),
    )
    new_attempt = await client.post(
        "/api/v1/agent/register",
        headers=agent_headers(second_token),
        json=snapshot_payload(),
    )
    revoked = await client.post(
        f"/api/v1/servers/{server_id}/agent-token/revoke", headers=admin_headers
    )
    revoked_attempt = await client.post(
        "/api/v1/agent/heartbeat",
        headers=agent_headers(second_token),
        json=snapshot_payload(),
    )

    assert rotated.status_code == 200
    assert first_token != second_token
    assert old_attempt.status_code == 401
    assert new_attempt.status_code == 200
    assert revoked.status_code == 204
    assert revoked_attempt.status_code == 401
    assert revoked_attempt.json()["error"]["code"] == "invalid_agent_token"
    async with app.state.database.session_factory() as session:
        actions = set(await session.scalars(select(AuditLog.action)))
        assert {
            "agent.registration.created",
            "agent.token.rotated",
            "agent.registered",
            "agent.token.revoked",
            "agent.authentication.rejected",
        } <= actions


async def test_registration_requires_admin_and_agent_identity_is_stable(
    client: AsyncClient, app: FastAPI
) -> None:
    viewer_headers = await user_headers(app, role=UserRole.VIEWER)
    forbidden = await client.post(
        "/api/v1/servers/registrations",
        headers=viewer_headers,
        json={"name": "forbidden"},
    )
    _, token, _ = await create_registration(client, app)
    first = await client.post(
        "/api/v1/agent/register", headers=agent_headers(token), json=snapshot_payload()
    )
    conflict = await client.post(
        "/api/v1/agent/heartbeat",
        headers=agent_headers(token),
        json=snapshot_payload(hostname="different-host"),
    )

    assert forbidden.status_code == 403
    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "agent_identity_conflict"


async def test_stale_server_is_marked_offline(client: AsyncClient, app: FastAPI) -> None:
    server_id, token, admin_headers = await create_registration(client, app)
    await client.post(
        "/api/v1/agent/register", headers=agent_headers(token), json=snapshot_payload()
    )
    async with app.state.database.session_factory() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        server.last_seen = datetime.now(UTC) - timedelta(seconds=31)
        await session.commit()

    listed = await client.get("/api/v1/servers", headers=admin_headers)

    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "offline"


async def test_agent_token_is_required(client: AsyncClient) -> None:
    missing = await client.post("/api/v1/agent/register", json=snapshot_payload())
    invalid = await client.post(
        "/api/v1/agent/register",
        headers=agent_headers("not-a-real-token"),
        json=snapshot_payload(),
    )

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "agent_authentication_required"
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_agent_token"
