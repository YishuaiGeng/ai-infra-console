from __future__ import annotations

import hashlib
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import docker
import httpx
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from docker.types import DeviceRequest

from ai_infra_agent.collectors.models import scan_model_directory
from ai_infra_agent.config import AgentSettings
from ai_infra_agent.schemas import (
    DeploymentCommand,
    DeploymentCreateCommand,
    DeploymentLogReport,
    DeploymentRuntimeExpectation,
    DeploymentRuntimeObservation,
)

MANAGED_LABEL = "ai.infra.console.managed"
DEPLOYMENT_LABEL = "ai.infra.console.deployment-id"
GENERATION_LABEL = "ai.infra.console.generation"
PORT_LABEL = "ai.infra.console.port"
FLAG_ARITY = {
    "--enable-prefix-caching": 0,
    "--disable-log-requests": 0,
    "--enforce-eager": 0,
    "--enable-chunked-prefill": 0,
    "--max-num-seqs": 1,
    "--task": 1,
    "--quantization": 1,
    "--tokenizer-mode": 1,
}


class DeploymentExecutionError(RuntimeError):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


@dataclass(frozen=True, slots=True)
class DeploymentExecutionResult:
    state: str
    container_id: str | None


class DeploymentRuntime(Protocol):
    def execute(self, command: DeploymentCommand) -> DeploymentExecutionResult: ...

    def observe(
        self,
        expectations: list[DeploymentRuntimeExpectation],
    ) -> list[DeploymentRuntimeObservation]: ...

    def close(self) -> None: ...


def _validate_extra_arguments(arguments: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(arguments):
        flag = arguments[index]
        arity = FLAG_ARITY.get(flag)
        if arity is None:
            raise DeploymentExecutionError(
                "unsupported_vllm_argument",
                "The deployment contains an unsupported vLLM option.",
            )
        normalized.append(flag)
        if arity:
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
                raise DeploymentExecutionError(
                    "invalid_vllm_argument",
                    "A vLLM option is missing its value.",
                )
            normalized.append(arguments[index + 1])
        index += arity + 1
    return normalized


def _validated_model_path(
    settings: AgentSettings,
    command: DeploymentCreateCommand,
) -> Path:
    root = Path(command.root_path)
    model_path = Path(command.model_path)
    try:
        if root.is_symlink() or model_path.is_symlink():
            raise DeploymentExecutionError(
                "deployment_model_symlink",
                "Deployment model paths cannot be symbolic links.",
            )
        resolved_root = root.resolve(strict=True)
        resolved_model = model_path.resolve(strict=True)
    except OSError as exc:
        raise DeploymentExecutionError(
            "deployment_model_unavailable",
            "The deployment model path is unavailable.",
        ) from exc
    if resolved_root not in settings.allowed_model_directories or not resolved_root.is_dir():
        raise DeploymentExecutionError(
            "deployment_root_not_allowed",
            "The deployment root is not in the local Agent allowlist.",
        )
    if resolved_model == resolved_root or not resolved_model.is_relative_to(resolved_root):
        raise DeploymentExecutionError(
            "deployment_model_outside_root",
            "The deployment model is outside the local Agent allowlist.",
        )
    current = resolved_root
    for part in resolved_model.relative_to(resolved_root).parts:
        current /= part
        if current.is_symlink():
            raise DeploymentExecutionError(
                "deployment_model_symlink",
                "Deployment model paths cannot contain symbolic links.",
            )
    directory, installations = scan_model_directory(
        resolved_root,
        is_default=resolved_root == settings.default_model_directory,
        max_depth=settings.model_scan_max_depth,
        max_installations=settings.model_scan_max_installations,
        max_metadata_bytes=settings.model_metadata_max_bytes,
    )
    matched = next(
        (
            item
            for item in installations
            if Path(item.path).resolve(strict=False) == resolved_model
            and item.source == command.source
            and item.source_id == command.source_id
        ),
        None,
    )
    if not directory.available or matched is None:
        raise DeploymentExecutionError(
            "deployment_model_identity_mismatch",
            "The local model identity no longer matches the deployment request.",
        )
    return resolved_model


def build_vllm_arguments(command: DeploymentCreateCommand) -> list[str]:
    config = command.config
    arguments = [
        "--model",
        "/model",
        "--host",
        "0.0.0.0",  # noqa: S104 - the published container API must accept host traffic.
        "--port",
        str(command.port),
        "--tensor-parallel-size",
        str(config.tensor_parallel_size),
        "--gpu-memory-utilization",
        str(config.gpu_memory_utilization),
        "--max-model-len",
        str(config.max_model_length),
        "--dtype",
        config.data_type,
    ]
    if config.trust_remote_code:
        arguments.append("--trust-remote-code")
    arguments.extend(_validate_extra_arguments(config.extra_arguments))
    return arguments


def _port_available(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0
    finally:
        sock.close()


class DockerDeploymentRuntime:
    def __init__(
        self,
        settings: AgentSettings,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._client: Any = client or docker.from_env(timeout=5)
        self._client.ping()
        self._log_lock = threading.Lock()
        self._log_sequences: dict[uuid.UUID, int] = {}
        self._log_fingerprints: dict[uuid.UUID, set[str]] = {}

    def close(self) -> None:
        self._client.close()

    def _owned_container(
        self,
        name: str,
        deployment_id: uuid.UUID,
        generation: int,
    ) -> Any | None:
        try:
            container = self._client.containers.get(name)
        except NotFound:
            return None
        labels = container.labels or {}
        if (
            labels.get(MANAGED_LABEL) != "true"
            or labels.get(DEPLOYMENT_LABEL) != str(deployment_id)
            or labels.get(GENERATION_LABEL) != str(generation)
        ):
            raise DeploymentExecutionError(
                "foreign_container_conflict",
                "The deterministic container name belongs to another workload.",
            )
        return container

    def execute(self, command: DeploymentCommand) -> DeploymentExecutionResult:
        if not self._settings.enable_deployments:
            raise DeploymentExecutionError(
                "deployments_disabled",
                "Deployment mutations are disabled on this Agent.",
            )
        try:
            if command.kind == "create":
                return self._create(command)
            return self._lifecycle(command)
        except DeploymentExecutionError:
            raise
        except ImageNotFound as exc:
            raise DeploymentExecutionError(
                "vllm_image_unavailable",
                "The configured vLLM image is unavailable.",
            ) from exc
        except (APIError, DockerException, OSError) as exc:
            raise DeploymentExecutionError(
                "docker_operation_failed",
                f"The Docker deployment operation failed ({type(exc).__name__}).",
            ) from exc

    def _create(self, command: DeploymentCreateCommand) -> DeploymentExecutionResult:
        if command.image != self._settings.vllm_image:
            raise DeploymentExecutionError(
                "vllm_image_not_allowed",
                "The requested vLLM image is not allowed by this Agent.",
            )
        if len(command.gpu_indexes) != command.config.tensor_parallel_size or len(
            command.gpu_uuids
        ) != command.config.tensor_parallel_size:
            raise DeploymentExecutionError(
                "deployment_gpu_count_mismatch",
                "GPU selection does not match tensor parallel size.",
            )
        model_path = _validated_model_path(self._settings, command)
        existing = self._owned_container(
            command.container_name,
            command.deployment_id,
            command.generation,
        )
        if existing is not None:
            existing.reload()
            if existing.status != "running":
                if not _port_available(command.port):
                    raise DeploymentExecutionError(
                        "deployment_port_conflict",
                        "The deployment port is already in use on the Agent host.",
                    )
                existing.start()
            return DeploymentExecutionResult(state="running", container_id=str(existing.id))
        if not _port_available(command.port):
            raise DeploymentExecutionError(
                "deployment_port_conflict",
                "The deployment port is already in use on the Agent host.",
            )
        labels = {
            MANAGED_LABEL: "true",
            DEPLOYMENT_LABEL: str(command.deployment_id),
            GENERATION_LABEL: str(command.generation),
            PORT_LABEL: str(command.port),
        }
        container = self._client.containers.create(
            command.image,
            command=build_vllm_arguments(command),
            name=command.container_name,
            detach=True,
            labels=labels,
            environment={
                "CUDA_VISIBLE_DEVICES": ",".join(str(index) for index in command.gpu_indexes)
            },
            volumes={str(model_path): {"bind": "/model", "mode": "ro"}},
            ports={f"{command.port}/tcp": command.port},
            device_requests=[
                DeviceRequest(device_ids=command.gpu_uuids, capabilities=[["gpu"]])
            ],
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            tmpfs={"/tmp": "rw,noexec,nosuid,size=1g"},  # noqa: S108 - container tmpfs.
            shm_size="2g",
            restart_policy={"Name": "no"},
        )
        container.start()
        return DeploymentExecutionResult(state="running", container_id=str(container.id))

    def _lifecycle(self, command: DeploymentCommand) -> DeploymentExecutionResult:
        container = self._owned_container(
            command.container_name,
            command.deployment_id,
            command.generation,
        )
        if container is None:
            if command.kind in {"stop", "delete"}:
                return DeploymentExecutionResult(state="missing", container_id=None)
            raise DeploymentExecutionError(
                "managed_container_missing",
                "The managed deployment container does not exist.",
            )
        port_text = (container.labels or {}).get(PORT_LABEL)
        port = int(port_text) if isinstance(port_text, str) and port_text.isdigit() else None
        if command.kind == "start":
            if port is not None and not _port_available(port):
                raise DeploymentExecutionError(
                    "deployment_port_conflict",
                    "The deployment port is already in use on the Agent host.",
                )
            container.start()
            return DeploymentExecutionResult(state="running", container_id=str(container.id))
        if command.kind == "stop":
            container.stop(timeout=self._settings.deployment_stop_timeout_seconds)
            return DeploymentExecutionResult(state="stopped", container_id=str(container.id))
        if command.kind == "restart":
            container.restart(timeout=self._settings.deployment_stop_timeout_seconds)
            return DeploymentExecutionResult(state="running", container_id=str(container.id))
        container.stop(timeout=self._settings.deployment_stop_timeout_seconds)
        container.remove(v=False, force=False)
        return DeploymentExecutionResult(state="missing", container_id=None)

    def _log_entries(self, deployment_id: uuid.UUID, container: Any) -> list[DeploymentLogReport]:
        payload = container.logs(
            tail=self._settings.deployment_log_max_lines,
            stdout=True,
            stderr=True,
        )
        if not isinstance(payload, bytes):
            return []
        payload = payload[-self._settings.deployment_log_max_bytes :]
        lines = payload.decode("utf-8", errors="replace").splitlines()
        entries: list[DeploymentLogReport] = []
        with self._log_lock:
            fingerprints = self._log_fingerprints.setdefault(deployment_id, set())
            sequence = self._log_sequences.get(deployment_id, 0)
            for line in lines:
                clean = line[:4096]
                fingerprint = hashlib.sha256(clean.encode("utf-8")).hexdigest()
                if not clean or fingerprint in fingerprints:
                    continue
                fingerprints.add(fingerprint)
                sequence += 1
                entries.append(
                    DeploymentLogReport(
                        sequence=sequence,
                        timestamp=datetime.now(UTC),
                        stream="stdout",
                        message=clean,
                    )
                )
            if len(fingerprints) > self._settings.deployment_log_max_lines * 4:
                fingerprints.clear()
            self._log_sequences[deployment_id] = sequence
        return entries

    def _health(self, port: int, running: bool) -> tuple[str, float | None]:
        if not running:
            return "unknown", None
        started = time.monotonic()
        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}/health",
                timeout=self._settings.deployment_health_timeout_seconds,
            )
        except httpx.HTTPError:
            return "unhealthy", None
        latency = round((time.monotonic() - started) * 1_000, 2)
        return ("healthy" if response.is_success else "degraded"), latency

    def observe(
        self,
        expectations: list[DeploymentRuntimeExpectation],
    ) -> list[DeploymentRuntimeObservation]:
        observed: dict[uuid.UUID, DeploymentRuntimeObservation] = {}
        containers = self._client.containers.list(
            all=True,
            filters={"label": f"{MANAGED_LABEL}=true"},
        )
        expected = {item.deployment_id: item for item in expectations}
        for container in containers:
            labels = container.labels or {}
            deployment_text = labels.get(DEPLOYMENT_LABEL)
            generation_text = labels.get(GENERATION_LABEL)
            port_text = labels.get(PORT_LABEL)
            try:
                deployment_id = uuid.UUID(str(deployment_text))
                generation = int(str(generation_text))
                port = int(str(port_text))
            except (ValueError, TypeError):
                continue
            expectation = expected.get(deployment_id)
            if expectation is None or expectation.generation != generation:
                continue
            container.reload()
            state = {
                "running": "running",
                "created": "stopped",
                "exited": (
                    "stopped"
                    if (container.attrs.get("State") or {}).get("ExitCode") == 0
                    else "failed"
                ),
                "dead": "failed",
            }.get(container.status, "failed")
            running = state == "running"
            health, latency = self._health(port, running)
            exit_code = (container.attrs.get("State") or {}).get("ExitCode")
            observed[deployment_id] = DeploymentRuntimeObservation(
                deployment_id=deployment_id,
                generation=generation,
                container_id=str(container.id),
                state=state,
                exit_code=int(exit_code) if isinstance(exit_code, int) else None,
                health_status=health,
                health_latency_ms=latency,
                checked_at=datetime.now(UTC),
                logs=self._log_entries(deployment_id, container),
            )
        for deployment_id, expectation in expected.items():
            if deployment_id not in observed:
                observed[deployment_id] = DeploymentRuntimeObservation(
                    deployment_id=deployment_id,
                    generation=expectation.generation,
                    state="missing",
                    health_status="unknown",
                    checked_at=datetime.now(UTC),
                )
        return list(observed.values())


@dataclass(slots=True)
class _FixtureContainer:
    deployment_id: uuid.UUID
    generation: int
    container_id: str
    port: int
    state: str
    logs: list[DeploymentLogReport]


class FixtureDeploymentRuntime:
    def __init__(self, settings: AgentSettings) -> None:
        self._settings = settings
        self._containers: dict[uuid.UUID, _FixtureContainer] = {}

    def close(self) -> None:
        return None

    def execute(self, command: DeploymentCommand) -> DeploymentExecutionResult:
        if not self._settings.enable_deployments:
            raise DeploymentExecutionError(
                "deployments_disabled",
                "Deployment mutations are disabled on this Agent.",
            )
        current = self._containers.get(command.deployment_id)
        if command.kind == "create":
            if command.image != self._settings.vllm_image:
                raise DeploymentExecutionError(
                    "vllm_image_not_allowed",
                    "The requested vLLM image is not allowed by this Agent.",
                )
            _validated_model_path(self._settings, command)
            build_vllm_arguments(command)
            container_id = hashlib.sha256(str(command.deployment_id).encode()).hexdigest()
            current = _FixtureContainer(
                deployment_id=command.deployment_id,
                generation=command.generation,
                container_id=container_id,
                port=command.port,
                state="running",
                logs=[
                    DeploymentLogReport(
                        sequence=1,
                        timestamp=datetime.now(UTC),
                        message="INFO fixture vLLM runtime is ready",
                    )
                ],
            )
            self._containers[command.deployment_id] = current
            return DeploymentExecutionResult(state="running", container_id=container_id)
        if current is None or current.generation != command.generation:
            if command.kind in {"stop", "delete"}:
                return DeploymentExecutionResult(state="missing", container_id=None)
            raise DeploymentExecutionError(
                "managed_container_missing",
                "The managed deployment container does not exist.",
            )
        if command.kind == "stop":
            current.state = "stopped"
            return DeploymentExecutionResult(state="stopped", container_id=current.container_id)
        if command.kind in {"start", "restart"}:
            current.state = "running"
            return DeploymentExecutionResult(state="running", container_id=current.container_id)
        del self._containers[command.deployment_id]
        return DeploymentExecutionResult(state="missing", container_id=None)

    def observe(
        self,
        expectations: list[DeploymentRuntimeExpectation],
    ) -> list[DeploymentRuntimeObservation]:
        result: list[DeploymentRuntimeObservation] = []
        for expectation in expectations:
            container = self._containers.get(expectation.deployment_id)
            if container is None or container.generation != expectation.generation:
                result.append(
                    DeploymentRuntimeObservation(
                        deployment_id=expectation.deployment_id,
                        generation=expectation.generation,
                        state="missing",
                        checked_at=datetime.now(UTC),
                    )
                )
                continue
            result.append(
                DeploymentRuntimeObservation(
                    deployment_id=container.deployment_id,
                    generation=container.generation,
                    container_id=container.container_id,
                    state=container.state,
                    exit_code=0,
                    health_status="healthy" if container.state == "running" else "unknown",
                    health_latency_ms=1.0 if container.state == "running" else None,
                    checked_at=datetime.now(UTC),
                    logs=container.logs,
                )
            )
        return result


def create_deployment_runtime(settings: AgentSettings) -> DeploymentRuntime:
    if settings.deployment_runtime_fixture:
        return FixtureDeploymentRuntime(settings)
    try:
        return DockerDeploymentRuntime(settings)
    except DockerException as exc:
        raise DeploymentExecutionError(
            "docker_unavailable",
            "Docker is unavailable on this Agent.",
        ) from exc
