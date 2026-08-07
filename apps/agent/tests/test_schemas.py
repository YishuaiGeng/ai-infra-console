from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_infra_agent.schemas import (
    AgentSnapshot,
    CollectorStatus,
    CPUSnapshot,
    HostSnapshot,
    MemorySnapshot,
    NetworkSnapshot,
    RuntimeSnapshot,
)


def snapshot() -> AgentSnapshot:
    unavailable = CollectorStatus(available=False, detail="not installed")
    return AgentSnapshot(
        collected_at=datetime.now(UTC),
        agent_version="0.1.0",
        host=HostSnapshot(
            hostname="cpu-node",
            os="Linux",
            kernel="6.8.0",
            architecture="x86_64",
            cpu=CPUSnapshot(logical_cores=8, utilization=12.5),
            memory=MemorySnapshot(total=1024, used=512, percent=50),
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


def test_cpu_only_snapshot_is_valid() -> None:
    assert snapshot().gpus == []


def test_percentages_are_bounded() -> None:
    payload = snapshot().model_dump()
    payload["host"]["memory"]["percent"] = 101

    with pytest.raises(ValidationError):
        AgentSnapshot.model_validate(payload)
