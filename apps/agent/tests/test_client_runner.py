import asyncio
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from ai_infra_agent.client import (
    AgentAuthenticationError,
    CentralClient,
    CentralRequestError,
)
from ai_infra_agent.config import AgentSettings
from ai_infra_agent.runner import AgentRunner
from ai_infra_agent.schemas import (
    AgentReportResponse,
    AgentSnapshot,
    CollectorStatus,
    CPUSnapshot,
    DeleteTaskCommand,
    DownloadTaskCommand,
    HostSnapshot,
    MemorySnapshot,
    NetworkSnapshot,
    RuntimeSnapshot,
)


def sample_snapshot() -> AgentSnapshot:
    unavailable = CollectorStatus(available=False, detail="not installed")
    return AgentSnapshot(
        collected_at=datetime.now(UTC),
        agent_version="0.1.0",
        host=HostSnapshot(
            hostname="client-node",
            os="Linux",
            kernel="6.8.0",
            architecture="x86_64",
            cpu=CPUSnapshot(logical_cores=8, utilization=12),
            memory=MemorySnapshot(total=1000, used=500, percent=50),
            disks=[],
            network=NetworkSnapshot(bytes_sent=10, bytes_received=20),
            runtimes=RuntimeSnapshot(
                python=CollectorStatus(available=True, version="3.12.0"),
                docker=unavailable,
                ollama=unavailable,
            ),
        ),
        gpus=[],
        gpu_collector=CollectorStatus(available=False, detail="CPU-only host"),
    )


def client_settings(token: str = "private-agent-token") -> AgentSettings:
    return AgentSettings.model_validate(
        {
            "environment": "test",
            "central_url": "https://central.test",
            "token": SecretStr(token),
        }
    )


async def test_client_sends_token_only_in_header_and_validates_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["request_id"] = request.headers["x-request-id"]
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "server_id": "cb134a2d-99e0-4898-bf72-66d3db01ab34",
                "status": "online",
                "offline_after_seconds": 30,
            },
        )

    async with CentralClient(client_settings(), transport=httpx.MockTransport(handler)) as client:
        response = await client.register(sample_snapshot())

    assert response.status == "online"
    assert captured["authorization"] == "Bearer private-agent-token"
    assert captured["request_id"]
    assert "private-agent-token" not in str(captured["body"])


async def test_client_redacts_token_from_authentication_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": "invalid_agent_token"}})

    token = "must-never-appear-in-errors"
    async with CentralClient(
        client_settings(token), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(AgentAuthenticationError) as raised:
            await client.heartbeat(sample_snapshot())

    assert token not in str(raised.value)


async def test_client_redacts_token_from_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    token = "must-never-appear-in-network-errors"
    async with CentralClient(
        client_settings(token), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(CentralRequestError) as raised:
            await client.heartbeat(sample_snapshot())

    assert token not in str(raised.value)


async def test_client_model_task_protocol_keeps_leases_in_agent_headers_and_bodies() -> None:
    requests: list[httpx.Request] = []
    task_id = uuid.uuid4()
    lease = "task-lease-that-is-at-least-thirty-two-characters"

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/model-tasks/claim"):
            return httpx.Response(
                200,
                json={
                    "task": {
                        "kind": "download",
                        "task_id": str(task_id),
                        "lease_token": lease,
                        "root_path": "/data/models",
                        "provider": "huggingface",
                        "source_id": "Qwen/Qwen3-8B",
                        "revision": "main",
                        "target_path": "/data/models/huggingface/Qwen/Qwen3-8B",
                        "cancel_requested": False,
                    }
                },
            )
        if request.url.path.endswith("/progress"):
            return httpx.Response(
                200,
                json={
                    "cancel_requested": True,
                    "lease_expires_at": "2026-08-08T00:00:00Z",
                },
            )
        return httpx.Response(204)

    async with CentralClient(client_settings(), transport=httpx.MockTransport(handler)) as client:
        command = await client.claim_model_task()
        assert isinstance(command, DownloadTaskCommand)
        progress = await client.report_download_progress(
            command,
            downloaded_size=5,
            total_size=10,
            speed_bytes_per_second=2,
        )
        assert progress.cancel_requested is True
        await client.complete_download_task(
            command,
            outcome="cancelled",
            downloaded_size=5,
            total_size=10,
        )
        deletion = DeleteTaskCommand(
            kind="delete",
            task_id=uuid.uuid4(),
            lease_token=SecretStr(lease),
            root_path="/data/models",
            model_file_id=None,
            source="local",
            source_id="tiny-model",
            target_path="/data/models/tiny-model.gguf",
        )
        await client.complete_delete_task(deletion, outcome="completed")

    assert len(requests) == 4
    assert all(
        request.headers["authorization"] == "Bearer private-agent-token" for request in requests
    )
    assert lease in requests[1].content.decode("utf-8")


def test_client_requires_token() -> None:
    settings = AgentSettings(environment="test", token=None)

    with pytest.raises(ValueError, match="TOKEN is required"):
        CentralClient(settings)


class RecoveringReporter:
    def __init__(self) -> None:
        self.registration_attempts = 0
        self.heartbeats = 0

    async def register(self, _snapshot: AgentSnapshot) -> AgentReportResponse:
        self.registration_attempts += 1
        if self.registration_attempts == 1:
            raise httpx.ConnectError(
                "central unavailable", request=httpx.Request("POST", "https://central.test")
            )
        return AgentReportResponse(
            server_id=uuid.UUID("cb134a2d-99e0-4898-bf72-66d3db01ab34"),
            status="online",
            offline_after_seconds=30,
        )

    async def heartbeat(self, _snapshot: AgentSnapshot) -> AgentReportResponse:
        self.heartbeats += 1
        return AgentReportResponse(
            server_id=uuid.UUID("cb134a2d-99e0-4898-bf72-66d3db01ab34"),
            status="online",
            offline_after_seconds=30,
        )


async def test_runner_retries_then_recovers_without_overlapping_cycles() -> None:
    reporter = RecoveringReporter()
    stop_event = asyncio.Event()
    delays: list[float] = []
    collections = 0

    def collector() -> AgentSnapshot:
        nonlocal collections
        collections += 1
        return sample_snapshot()

    async def waiter(delay: float, event: asyncio.Event) -> None:
        delays.append(delay)
        if len(delays) == 2:
            event.set()

    runner = AgentRunner(
        reporter,
        collector,
        heartbeat_seconds=10,
        stop_event=stop_event,
        waiter=waiter,
        random_value=lambda: 0,
    )

    await runner.run()

    assert reporter.registration_attempts == 2
    assert reporter.heartbeats == 0
    assert collections == 2
    assert delays == [2, 10]


class RejectingReporter:
    async def register(self, _snapshot: AgentSnapshot) -> AgentReportResponse:
        raise AgentAuthenticationError("authentication rejected")

    async def heartbeat(self, _snapshot: AgentSnapshot) -> AgentReportResponse:
        raise AssertionError("heartbeat should not be attempted")


async def test_runner_stops_retrying_on_authentication_rejection() -> None:
    runner = AgentRunner(
        RejectingReporter(),
        sample_snapshot,
        heartbeat_seconds=10,
    )

    with pytest.raises(AgentAuthenticationError):
        await runner.run()
