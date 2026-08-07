from types import SimpleNamespace

import pynvml  # type: ignore[import-untyped]

from ai_infra_agent.collectors import nvidia
from ai_infra_agent.collectors.snapshot import collect_snapshot
from ai_infra_agent.collectors.system import collect_host_snapshot
from ai_infra_agent.schemas import CollectorStatus, GPUSnapshot, RuntimeSnapshot


def unavailable_runtimes() -> RuntimeSnapshot:
    unavailable = CollectorStatus(available=False, detail="not installed")
    return RuntimeSnapshot(
        python=CollectorStatus(available=True, version="3.12.0"),
        docker=unavailable,
        ollama=unavailable,
    )


def test_system_collector_returns_normalized_host_snapshot() -> None:
    host = collect_host_snapshot(unavailable_runtimes())

    assert host.hostname
    assert host.os
    assert host.kernel
    assert host.memory.total >= host.memory.used >= 0
    assert host.network.bytes_sent >= 0


def test_nvml_collection_is_preferred_and_normalizes_units(monkeypatch: object) -> None:
    patch = monkeypatch.setattr  # type: ignore[attr-defined]
    patch(nvidia.pynvml, "nvmlInit", lambda: None)
    patch(nvidia.pynvml, "nvmlShutdown", lambda: None)
    patch(nvidia.pynvml, "nvmlSystemGetDriverVersion", lambda: b"580.00")
    patch(nvidia.pynvml, "nvmlSystemGetCudaDriverVersion_v2", lambda: 13000)
    patch(nvidia.pynvml, "nvmlDeviceGetCount", lambda: 1)
    patch(nvidia.pynvml, "nvmlDeviceGetHandleByIndex", lambda _index: "handle")
    patch(
        nvidia.pynvml,
        "nvmlDeviceGetMemoryInfo",
        lambda _handle: SimpleNamespace(total=24_000, used=12_000),
    )
    patch(
        nvidia.pynvml,
        "nvmlDeviceGetUtilizationRates",
        lambda _handle: SimpleNamespace(gpu=75),
    )
    patch(nvidia.pynvml, "nvmlDeviceGetTemperature", lambda _handle, _sensor: 64)
    patch(nvidia.pynvml, "nvmlDeviceGetPowerUsage", lambda _handle: 250_000)
    patch(nvidia.pynvml, "nvmlDeviceGetEnforcedPowerLimit", lambda _handle: 450_000)
    patch(nvidia.pynvml, "nvmlDeviceGetFanSpeed", lambda _handle: 40)
    patch(nvidia.pynvml, "nvmlDeviceGetUUID", lambda _handle: b"GPU-test")
    patch(nvidia.pynvml, "nvmlDeviceGetName", lambda _handle: b"RTX Test")
    patch(
        nvidia.pynvml,
        "nvmlDeviceGetComputeRunningProcesses",
        lambda _handle: [SimpleNamespace(pid=4321, usedGpuMemory=8_000)],
    )
    patch(nvidia.pynvml, "nvmlDeviceGetGraphicsRunningProcesses", lambda _handle: [])

    gpus, status = nvidia.collect_with_nvml()

    assert status.available is True
    assert len(gpus) == 1
    assert gpus[0].uuid == "GPU-test"
    assert gpus[0].power_usage == 250
    assert gpus[0].cuda_version == "13.0"
    assert gpus[0].processes[0].pid == 4321


def test_nvidia_smi_fallback_parses_four_gpus(monkeypatch: object) -> None:
    rows = "\n".join(
        f"{index}, GPU-{index}, RTX 4090, 24564, 1024, 10, 45, 100, 450, 30, 580.00"
        for index in range(4)
    )
    monkeypatch.setattr(nvidia, "run_gpu_query", lambda: rows)  # type: ignore[attr-defined]
    monkeypatch.setattr(nvidia, "fallback_processes", lambda: {})  # type: ignore[attr-defined]

    gpus, status = nvidia.collect_with_nvidia_smi()

    assert status.available is True
    assert [gpu.uuid for gpu in gpus] == ["GPU-0", "GPU-1", "GPU-2", "GPU-3"]
    assert gpus[0].memory_total == 24_564 * 1024 * 1024


def test_malformed_nvidia_smi_output_fails_closed(monkeypatch: object) -> None:
    monkeypatch.setattr(nvidia, "run_gpu_query", lambda: "0, too,few")  # type: ignore[attr-defined]
    monkeypatch.setattr(nvidia, "fallback_processes", lambda: {})  # type: ignore[attr-defined]

    try:
        nvidia.collect_with_nvidia_smi()
    except ValueError as exc:
        assert "column count" in str(exc)
    else:
        raise AssertionError("malformed output was accepted")


def test_cpu_only_host_returns_explicit_unavailable_status(monkeypatch: object) -> None:
    def unavailable_nvml() -> tuple[list[GPUSnapshot], CollectorStatus]:
        raise pynvml.NVMLError(pynvml.NVML_ERROR_UNKNOWN)

    monkeypatch.setattr(nvidia, "collect_with_nvml", unavailable_nvml)  # type: ignore[attr-defined]
    monkeypatch.setattr(nvidia.shutil, "which", lambda _name: None)  # type: ignore[attr-defined]

    gpus, status = nvidia.collect_gpu_snapshot()

    assert gpus == []
    assert status.available is False
    assert "nvidia-smi not found" in str(status.detail)


def test_snapshot_orchestrator_combines_collectors(monkeypatch: object) -> None:
    import ai_infra_agent.collectors.snapshot as orchestrator

    runtimes = unavailable_runtimes()
    host = collect_host_snapshot(runtimes)
    monkeypatch.setattr(orchestrator, "collect_runtime_snapshot", lambda: runtimes)  # type: ignore[attr-defined]
    monkeypatch.setattr(orchestrator, "collect_host_snapshot", lambda _runtime: host)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        orchestrator,
        "collect_gpu_snapshot",
        lambda: ([], CollectorStatus(available=False, detail="CPU-only host")),
    )

    snapshot = collect_snapshot()

    assert snapshot.host.hostname == host.hostname
    assert snapshot.gpus == []
    assert snapshot.gpu_collector.available is False
