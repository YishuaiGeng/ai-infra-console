import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy import delete, select

from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import GPU, GPUMetric, GPUProcess, Server, User, UserRole
from ai_infra_api.schemas.infrastructure import InfrastructureEvent
from ai_infra_api.services.infrastructure_events import (
    INFRASTRUCTURE_EVENT_CHANNEL,
    encode_sse,
    publish_server_update,
    stream_infrastructure_events,
)


async def auth_headers(app: FastAPI, role: UserRole) -> dict[str, str]:
    user = User(
        username=f"infrastructure-{role.value}",
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


def snapshot(
    hostname: str,
    *,
    gpu_uuid: str | None,
    utilization: float = 50,
) -> dict[str, object]:
    gpus: list[dict[str, object]] = []
    if gpu_uuid is not None:
        gpus.append(
            {
                "index": 0,
                "uuid": gpu_uuid,
                "name": "NVIDIA Test GPU",
                "memory_total": 24_000,
                "memory_used": 12_000,
                "utilization": utilization,
                "temperature": 61,
                "power_usage": 220,
                "power_limit": 450,
                "fan_speed": 35,
                "driver_version": "580.00",
                "cuda_version": "13.0",
                "processes": [],
            }
        )
    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "agent_version": "0.1.0",
        "host": {
            "hostname": hostname,
            "os": "Linux",
            "kernel": "6.8.0",
            "architecture": "x86_64",
            "boot_time": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "cpu": {
                "model": "Test CPU",
                "physical_cores": 8,
                "logical_cores": 16,
                "utilization": 25,
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
                "docker": {
                    "available": False,
                    "detail": "private collector detail must not escape",
                },
                "ollama": {"available": False, "detail": "not installed"},
            },
        },
        "gpus": gpus,
        "gpu_collector": {
            "available": gpu_uuid is not None,
            "detail": None if gpu_uuid is not None else "no NVIDIA GPU",
        },
    }


async def register_server(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    hostname: str,
    gpu_uuid: str | None,
) -> uuid.UUID:
    created = await client.post(
        "/api/v1/servers/registrations",
        headers=headers,
        json={"name": name, "type": "local", "tags": ["phase-3"]},
    )
    assert created.status_code == 201
    payload = created.json()
    reported = await client.post(
        "/api/v1/agent/register",
        headers={"authorization": f"Bearer {payload['registration_token']}"},
        json=snapshot(hostname, gpu_uuid=gpu_uuid),
    )
    assert reported.status_code == 200
    return uuid.UUID(payload["server_id"])


async def test_infrastructure_reads_aggregate_multiple_servers_and_hide_secrets(
    client: AsyncClient, app: FastAPI
) -> None:
    admin_headers = await auth_headers(app, UserRole.ADMIN)
    first_id = await register_server(
        client,
        admin_headers,
        name="lab-server-01",
        hostname="lab-01",
        gpu_uuid="GPU-phase3-0",
    )
    await register_server(
        client,
        admin_headers,
        name="lab-server-02",
        hostname="lab-02",
        gpu_uuid=None,
    )
    third_id = await register_server(
        client,
        admin_headers,
        name="cloud-server-01",
        hostname="cloud-01",
        gpu_uuid="GPU-phase3-1",
    )
    async with app.state.database.session_factory() as session:
        third = await session.get(Server, third_id)
        assert third is not None
        third.last_seen = datetime.now(UTC) - timedelta(seconds=31)
        await session.commit()

    viewer_headers = await auth_headers(app, UserRole.VIEWER)
    servers = await client.get("/api/v1/servers", headers=viewer_headers)
    gpus = await client.get("/api/v1/gpus", headers=viewer_headers)
    summary = await client.get("/api/v1/infrastructure/summary", headers=viewer_headers)
    detail = await client.get(f"/api/v1/servers/{first_id}", headers=viewer_headers)

    assert servers.status_code == gpus.status_code == summary.status_code == 200
    assert detail.status_code == 200
    assert [item["name"] for item in servers.json()] == [
        "cloud-server-01",
        "lab-server-01",
        "lab-server-02",
    ]
    assert [item["status"] for item in servers.json()] == ["offline", "online", "online"]
    assert summary.json() | {} == {
        **summary.json(),
        "server_count": 3,
        "online_server_count": 2,
        "offline_server_count": 1,
        "gpu_count": 2,
        "available_gpu_count": 1,
        "gpu_memory_used": 24_000,
        "gpu_memory_total": 48_000,
    }
    assert detail.json()["metric"]["runtimes"]["docker"] == {
        "available": False,
        "version": None,
    }
    serialized = servers.text + gpus.text + detail.text
    assert "registration_token" not in serialized
    assert "token_hash" not in serialized
    assert "private collector detail" not in serialized


async def test_latest_gpu_metric_status_and_process_shape(
    client: AsyncClient, app: FastAPI
) -> None:
    admin_headers = await auth_headers(app, UserRole.ADMIN)
    server_id = await register_server(
        client,
        admin_headers,
        name="metric-server",
        hostname="metric-node",
        gpu_uuid="GPU-latest",
    )
    async with app.state.database.session_factory() as session:
        gpu = await session.scalar(select(GPU).where(GPU.server_id == server_id))
        assert gpu is not None
        await session.execute(delete(GPUProcess).where(GPUProcess.gpu_id == gpu.id))
        session.add(
            GPUMetric(
                gpu_id=gpu.id,
                timestamp=datetime.now(UTC) + timedelta(seconds=1),
                utilization=96,
                memory_used=23_000,
                temperature=70,
                power_usage=300,
                power_limit=450,
                fan_speed=50,
            )
        )
        await session.commit()

    response = await client.get("/api/v1/gpus", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "high-load"
    assert response.json()[0]["utilization"] == 96
    assert response.json()[0]["process_count"] == 0


async def test_infrastructure_auth_not_found_and_admin_boundary(
    client: AsyncClient, app: FastAPI
) -> None:
    viewer_headers = await auth_headers(app, UserRole.VIEWER)

    anonymous = await client.get("/api/v1/gpus")
    missing = await client.get(
        f"/api/v1/servers/{uuid.uuid4()}", headers=viewer_headers
    )
    forbidden = await client.post(
        "/api/v1/servers/registrations",
        headers=viewer_headers,
        json={"name": "viewer-cannot-create"},
    )

    assert anonymous.status_code == 401
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "server_not_found"
    assert forbidden.status_code == 403


async def test_redis_event_publish_encode_and_stream_cleanup(app: FastAPI) -> None:
    server_id = uuid.uuid4()
    pubsub = app.state.redis.pubsub()
    await pubsub.subscribe(INFRASTRUCTURE_EVENT_CHANNEL)
    await pubsub.get_message(timeout=1)
    await publish_server_update(app.state.redis, server_id)
    published = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
    assert published is not None
    event = InfrastructureEvent.model_validate_json(published["data"])
    assert event.server_id == server_id
    assert encode_sse(event).startswith(f"id: {event.id}\nevent: infrastructure\ndata: ")
    await pubsub.unsubscribe(INFRASTRUCTURE_EVENT_CHANNEL)
    await pubsub.aclose()

    class DisconnectingRequest:
        disconnected = False

        async def is_disconnected(self) -> bool:
            return self.disconnected

    fake_request = DisconnectingRequest()
    stream = stream_infrastructure_events(
        cast(Request, cast(Any, fake_request)),
        app.state.redis,
        keepalive_seconds=0.01,
    )
    assert await anext(stream) == "retry: 5000\n\n"
    await publish_server_update(app.state.redis, server_id)
    streamed = ""
    for _ in range(3):
        streamed = await anext(stream)
        if streamed.startswith("id: "):
            break
    assert f'"server_id":"{server_id}"' in streamed
    fake_request.disconnected = True
    with pytest.raises(StopAsyncIteration):
        await anext(stream)


async def test_redis_event_failure_degrades_to_polling() -> None:
    class BrokenPubSub:
        closed = False

        async def subscribe(self, _channel: str) -> None:
            raise ConnectionError("redis unavailable")

        async def unsubscribe(self, _channel: str) -> None:
            raise AssertionError("an unsubscribed stream must not unsubscribe")

        async def aclose(self) -> None:
            self.closed = True

    class BrokenRedis:
        def __init__(self) -> None:
            self.stream = BrokenPubSub()

        async def publish(self, _channel: str, _payload: str) -> None:
            raise ConnectionError("redis unavailable")

        def pubsub(self) -> BrokenPubSub:
            return self.stream

    class ConnectedRequest:
        async def is_disconnected(self) -> bool:
            return False

    redis = BrokenRedis()
    await publish_server_update(cast(Any, redis), uuid.uuid4())
    stream = stream_infrastructure_events(
        cast(Request, cast(Any, ConnectedRequest())), cast(Any, redis)
    )

    assert await anext(stream) == "retry: 5000\n\n"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert redis.stream.closed is True
