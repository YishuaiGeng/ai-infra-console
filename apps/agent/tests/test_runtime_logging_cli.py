import json
import logging

import httpx
from docker.errors import DockerException

from ai_infra_agent.cli import parser
from ai_infra_agent.collectors import runtimes
from ai_infra_agent.logging import JsonFormatter


class FakeDockerClient:
    def __init__(self) -> None:
        self.closed = False

    def version(self) -> dict[str, str]:
        return {"Version": "27.1.0"}

    def close(self) -> None:
        self.closed = True


def test_docker_runtime_success_closes_client(monkeypatch: object) -> None:
    client = FakeDockerClient()
    monkeypatch.setattr(runtimes.docker, "from_env", lambda timeout: client)  # type: ignore[attr-defined]

    status = runtimes.docker_status()

    assert status.available is True
    assert status.version == "27.1.0"
    assert client.closed is True


def test_docker_runtime_unavailable_is_nonfatal(monkeypatch: object) -> None:
    def unavailable(*, timeout: int) -> None:
        raise DockerException(f"unavailable after {timeout}s")

    monkeypatch.setattr(runtimes.docker, "from_env", unavailable)  # type: ignore[attr-defined]

    status = runtimes.docker_status()

    assert status.available is False
    assert status.detail == "DockerException"


def test_ollama_runtime_success_and_unavailable(monkeypatch: object) -> None:
    request = httpx.Request("GET", runtimes.OLLAMA_VERSION_URL)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        runtimes.httpx,
        "get",
        lambda _url, timeout: httpx.Response(200, request=request, json={"version": "0.11.0"}),
    )
    available = runtimes.ollama_status()

    def connection_error(_url: str, timeout: int) -> httpx.Response:
        raise httpx.ConnectError(f"unavailable after {timeout}s", request=request)

    monkeypatch.setattr(runtimes.httpx, "get", connection_error)  # type: ignore[attr-defined]
    unavailable = runtimes.ollama_status()

    assert available.available is True
    assert available.version == "0.11.0"
    assert unavailable.available is False
    assert unavailable.detail == "ConnectError"


def test_structured_log_contains_agent_and_request_context() -> None:
    record = logging.LogRecord("agent", logging.INFO, "", 0, "accepted", (), None)
    record.event = "agent.report.accepted"
    record.request_id = "request-123"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["agent_version"] == "0.1.0"
    assert payload["request_id"] == "request-123"
    assert payload["event"] == "agent.report.accepted"


def test_cli_exposes_only_explicit_commands() -> None:
    command_parser = parser()

    assert command_parser.parse_args(["register"]).command == "register"
    assert command_parser.parse_args(["heartbeat"]).command == "heartbeat"
