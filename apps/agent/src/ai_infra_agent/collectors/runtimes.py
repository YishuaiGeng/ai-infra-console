from typing import Any

import docker
import httpx
from docker.errors import DockerException

from ai_infra_agent.collectors.system import python_version
from ai_infra_agent.schemas import CollectorStatus, RuntimeSnapshot

OLLAMA_VERSION_URL = "http://127.0.0.1:11434/api/version"


def docker_status() -> CollectorStatus:
    client: Any = None
    try:
        client = docker.from_env(timeout=2)
        details = client.version()
        return CollectorStatus(available=True, version=str(details.get("Version") or "unknown"))
    except DockerException as exc:
        return CollectorStatus(available=False, detail=type(exc).__name__)
    finally:
        if client is not None:
            client.close()


def ollama_status() -> CollectorStatus:
    try:
        response = httpx.get(OLLAMA_VERSION_URL, timeout=2)
        response.raise_for_status()
        payload = response.json()
        version = payload.get("version") if isinstance(payload, dict) else None
        return CollectorStatus(available=True, version=str(version or "unknown"))
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return CollectorStatus(available=False, detail=type(exc).__name__)


def collect_runtime_snapshot() -> RuntimeSnapshot:
    return RuntimeSnapshot(
        python=CollectorStatus(available=True, version=python_version()),
        docker=docker_status(),
        ollama=ollama_status(),
    )
