import json
import uuid
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import SecretStr, ValidationError

from ai_infra_agent.config import AgentSettings
from ai_infra_agent.deployment_runtime import (
    DEPLOYMENT_LABEL,
    GENERATION_LABEL,
    MANAGED_LABEL,
    DeploymentExecutionError,
    DockerDeploymentRuntime,
    FixtureDeploymentRuntime,
    build_vllm_arguments,
)
from ai_infra_agent.schemas import (
    DeploymentConfig,
    DeploymentCreateCommand,
    DeploymentLifecycleCommand,
    DeploymentRuntimeExpectation,
)


def model_fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "models"
    model = root / "huggingface" / "Qwen" / "Qwen3-8B"
    model.mkdir(parents=True)
    (model / "config.json").write_text(
        json.dumps({"model_type": "qwen", "architectures": ["QwenForCausalLM"]}),
        encoding="utf-8",
    )
    (model / ".ai-infra-source.json").write_text(
        json.dumps(
            {
                "source": "huggingface",
                "source_id": "Qwen/Qwen3-8B",
                "revision": "main",
            }
        ),
        encoding="utf-8",
    )
    (model / "model.safetensors").write_bytes(b"fixture")
    return root, model


def settings(root: Path, *, fixture: bool = True) -> AgentSettings:
    return AgentSettings(
        environment="test",
        central_url="http://central.test",
        token=SecretStr("agent-token"),
        allowed_model_directories=(root,),
        default_model_directory=root,
        enable_deployments=True,
        deployment_runtime_fixture=fixture,
        vllm_image="vllm/vllm-openai:test",
    )


def create_command(root: Path, model: Path) -> DeploymentCreateCommand:
    return DeploymentCreateCommand(
        kind="create",
        operation_id=uuid.uuid4(),
        deployment_id=uuid.uuid4(),
        generation=1,
        lease_token="l" * 40,
        container_name="ai-infra-test",
        image="vllm/vllm-openai:test",
        root_path=str(root),
        model_file_id=uuid.uuid4(),
        source="huggingface",
        source_id="Qwen/Qwen3-8B",
        model_path=str(model),
        port=8001,
        gpu_indexes=[0],
        gpu_uuids=["GPU-test-0"],
        config=DeploymentConfig(
            tensor_parallel_size=1,
            gpu_memory_utilization=0.8,
            max_model_length=8192,
            data_type="float16",
            trust_remote_code=False,
            extra_arguments=["--enable-prefix-caching", "--max-num-seqs", "32"],
        ),
    )


def lifecycle(
    command: DeploymentCreateCommand,
    kind: Literal["start", "stop", "restart", "delete"],
) -> DeploymentLifecycleCommand:
    return DeploymentLifecycleCommand(
        kind=kind,
        operation_id=uuid.uuid4(),
        deployment_id=command.deployment_id,
        generation=command.generation,
        lease_token="n" * 40,
        container_name=command.container_name,
    )


def expectation(command: DeploymentCreateCommand) -> DeploymentRuntimeExpectation:
    return DeploymentRuntimeExpectation(
        deployment_id=command.deployment_id,
        generation=command.generation,
        container_name=command.container_name,
        port=command.port,
        desired_state="running",
    )


def test_fixture_runtime_lifecycle_and_reconciliation(tmp_path: Path) -> None:
    root, model = model_fixture(tmp_path)
    runtime = FixtureDeploymentRuntime(settings(root))
    command = create_command(root, model)
    created = runtime.execute(command)
    assert created.state == "running"
    observations = runtime.observe([expectation(command)])
    assert observations[0].state == "running"
    assert observations[0].health_status == "healthy"
    assert observations[0].logs[0].message == "INFO fixture vLLM runtime is ready"

    assert runtime.execute(lifecycle(command, "stop")).state == "stopped"
    assert runtime.observe([expectation(command)])[0].state == "stopped"
    assert runtime.execute(lifecycle(command, "start")).state == "running"
    assert runtime.execute(lifecycle(command, "restart")).state == "running"
    assert runtime.execute(lifecycle(command, "delete")).state == "missing"
    assert runtime.observe([expectation(command)])[0].state == "missing"
    assert runtime.execute(lifecycle(command, "delete")).state == "missing"


def test_runtime_rejects_image_path_identity_and_arguments(tmp_path: Path) -> None:
    root, model = model_fixture(tmp_path)
    runtime = FixtureDeploymentRuntime(settings(root))
    command = create_command(root, model)
    command.image = "foreign/image:latest"
    with pytest.raises(DeploymentExecutionError, match="not allowed"):
        runtime.execute(command)

    command = create_command(root, model)
    command.source_id = "Other/Model"
    with pytest.raises(DeploymentExecutionError, match="identity"):
        runtime.execute(command)

    command = create_command(root, model)
    command.config.extra_arguments = ["--model", "/etc"]
    with pytest.raises(DeploymentExecutionError, match="unsupported"):
        build_vllm_arguments(command)

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "model.safetensors").write_bytes(b"outside")
    command = create_command(root, outside)
    with pytest.raises(DeploymentExecutionError, match="outside"):
        runtime.execute(command)


class FakeContainer:
    def __init__(self, name: str, labels: dict[str, str], kwargs: dict[str, Any]) -> None:
        self.name = name
        self.labels = labels
        self.kwargs = kwargs
        self.id = "docker-fixture-id"
        self.status = "created"
        self.attrs: dict[str, Any] = {"State": {"ExitCode": 0}}
        self.removed = False

    def start(self) -> None:
        self.status = "running"

    def stop(self, *, timeout: int) -> None:
        assert timeout > 0
        self.status = "exited"

    def restart(self, *, timeout: int) -> None:
        assert timeout > 0
        self.status = "running"

    def remove(self, *, v: bool, force: bool) -> None:
        assert v is False and force is False
        self.removed = True

    def reload(self) -> None:
        return None

    def logs(self, **_kwargs: object) -> bytes:
        return b"INFO ready\n"


class FakeContainers:
    def __init__(self) -> None:
        self.by_name: dict[str, FakeContainer] = {}
        self.last_create: dict[str, Any] | None = None

    def get(self, name: str) -> FakeContainer:
        from docker.errors import NotFound

        if name not in self.by_name:
            raise NotFound("missing")
        return self.by_name[name]

    def create(self, image: str, **kwargs: Any) -> FakeContainer:
        self.last_create = {"image": image, **kwargs}
        container = FakeContainer(kwargs["name"], kwargs["labels"], kwargs)
        self.by_name[container.name] = container
        return container

    def list(self, **_kwargs: object) -> list[FakeContainer]:
        return [item for item in self.by_name.values() if not item.removed]


class FakeDockerClient:
    def __init__(self) -> None:
        self.containers = FakeContainers()

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        return None


def test_docker_runtime_builds_owned_hardened_container(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, model = model_fixture(tmp_path)
    command = create_command(root, model)
    fake = FakeDockerClient()
    monkeypatch.setattr("ai_infra_agent.deployment_runtime._port_available", lambda _port: True)
    runtime = DockerDeploymentRuntime(settings(root, fixture=False), client=fake)
    result = runtime.execute(command)
    assert result.state == "running"
    created = fake.containers.last_create
    assert created is not None
    assert created["image"] == "vllm/vllm-openai:test"
    assert created["labels"][MANAGED_LABEL] == "true"
    assert created["labels"][DEPLOYMENT_LABEL] == str(command.deployment_id)
    assert created["labels"][GENERATION_LABEL] == "1"
    assert created["read_only"] is True
    assert created["cap_drop"] == ["ALL"]
    assert created["security_opt"] == ["no-new-privileges:true"]
    assert created["volumes"][str(model)]["mode"] == "ro"
    assert created["command"] == build_vllm_arguments(command)
    assert isinstance(created["command"], list)
    assert created["environment"] == {"CUDA_VISIBLE_DEVICES": "0"}


def test_production_deployment_requires_digest(tmp_path: Path) -> None:
    root, _model = model_fixture(tmp_path)
    with pytest.raises(ValidationError, match="immutable vLLM image digest"):
        AgentSettings(
            environment="production",
            central_url="https://central.test",
            token=SecretStr("token"),
            allowed_model_directories=(root,),
            enable_deployments=True,
            vllm_image="vllm/vllm-openai:latest",
        )
