import csv
import io
import shutil
import subprocess
from collections.abc import Callable
from typing import Any, TypeVar

import psutil
import pynvml

from ai_infra_agent.schemas import CollectorStatus, GPUProcessSnapshot, GPUSnapshot

T = TypeVar("T")
GPU_QUERY = (
    "index,uuid,name,memory.total,memory.used,utilization.gpu,temperature.gpu,"
    "power.draw,power.limit,fan.speed,driver_version"
)
PROCESS_QUERY = "gpu_uuid,pid,process_name,used_memory"


def decoded(value: str | bytes) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def optional(function: Callable[..., T], *arguments: Any) -> T | None:
    try:
        return function(*arguments)
    except pynvml.NVMLError:
        return None


def cuda_version(value: int | None) -> str | None:
    if value is None:
        return None
    major = value // 1000
    minor = (value % 1000) // 10
    return f"{major}.{minor}"


def process_details(pid: int, memory_used: int | None) -> GPUProcessSnapshot:
    try:
        process = psutil.Process(pid)
        username = process.username()
        command = process.name()
    except (psutil.Error, OSError):
        username = None
        command = None
    return GPUProcessSnapshot(
        pid=pid,
        username=username,
        command=command,
        memory_used=memory_used,
    )


def nvml_processes(handle: Any) -> list[GPUProcessSnapshot]:
    records: dict[int, GPUProcessSnapshot] = {}
    getters = (
        pynvml.nvmlDeviceGetComputeRunningProcesses,
        pynvml.nvmlDeviceGetGraphicsRunningProcesses,
    )
    for getter in getters:
        try:
            processes = getter(handle)
        except pynvml.NVMLError:
            processes = []
        for process in processes:
            pid = int(process.pid)
            used = getattr(process, "usedGpuMemory", None)
            value = int(used) if isinstance(used, int) and used >= 0 else None
            current = records.get(pid)
            if current is None or (value or 0) > (current.memory_used or 0):
                records[pid] = process_details(pid, value)
    return list(records.values())


def collect_with_nvml() -> tuple[list[GPUSnapshot], CollectorStatus]:
    pynvml.nvmlInit()
    try:
        driver = decoded(pynvml.nvmlSystemGetDriverVersion())
        cuda = cuda_version(optional(pynvml.nvmlSystemGetCudaDriverVersion_v2))
        gpus: list[GPUSnapshot] = []
        for index in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = optional(pynvml.nvmlDeviceGetUtilizationRates, handle)
            temperature = optional(
                pynvml.nvmlDeviceGetTemperature, handle, pynvml.NVML_TEMPERATURE_GPU
            )
            power_usage = optional(pynvml.nvmlDeviceGetPowerUsage, handle)
            power_limit = optional(pynvml.nvmlDeviceGetEnforcedPowerLimit, handle)
            fan_speed = optional(pynvml.nvmlDeviceGetFanSpeed, handle)
            gpus.append(
                GPUSnapshot(
                    index=index,
                    uuid=decoded(pynvml.nvmlDeviceGetUUID(handle)),
                    name=decoded(pynvml.nvmlDeviceGetName(handle)),
                    memory_total=int(memory.total),
                    memory_used=int(memory.used),
                    utilization=float(utilization.gpu) if utilization is not None else None,
                    temperature=float(temperature) if temperature is not None else None,
                    power_usage=float(power_usage) / 1000 if power_usage is not None else None,
                    power_limit=float(power_limit) / 1000 if power_limit is not None else None,
                    fan_speed=float(fan_speed) if fan_speed is not None else None,
                    driver_version=driver,
                    cuda_version=cuda,
                    processes=nvml_processes(handle),
                )
            )
        return gpus, CollectorStatus(available=True, version=f"NVML {driver}")
    finally:
        pynvml.nvmlShutdown()


def csv_value(value: str) -> str | None:
    normalized = value.strip()
    unavailable = {"", "n/a", "[not supported]", "not supported"}
    return None if normalized.lower() in unavailable else normalized


def csv_int(value: str, *, multiplier: int = 1) -> int | None:
    normalized = csv_value(value)
    return int(float(normalized) * multiplier) if normalized is not None else None


def csv_float(value: str) -> float | None:
    normalized = csv_value(value)
    return float(normalized) if normalized is not None else None


def nvidia_smi_path() -> str:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        raise FileNotFoundError("nvidia-smi was not found")
    return executable


def run_gpu_query() -> str:
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed here.
        [nvidia_smi_path(), f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return result.stdout


def fallback_processes() -> dict[str, list[GPUProcessSnapshot]]:
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed here.
        [
            nvidia_smi_path(),
            f"--query-compute-apps={PROCESS_QUERY}",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
    )
    processes: dict[str, list[GPUProcessSnapshot]] = {}
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) != 4:
            continue
        gpu_uuid, pid_value, command, memory = (item.strip() for item in row)
        pid = csv_int(pid_value)
        if pid is None:
            continue
        process = process_details(pid, csv_int(memory, multiplier=1024 * 1024))
        process.command = csv_value(command)
        processes.setdefault(gpu_uuid, []).append(process)
    return processes


def collect_with_nvidia_smi() -> tuple[list[GPUSnapshot], CollectorStatus]:
    try:
        process_map = fallback_processes()
    except (OSError, subprocess.SubprocessError, ValueError):
        process_map = {}
    gpus: list[GPUSnapshot] = []
    for row in csv.reader(io.StringIO(run_gpu_query())):
        if len(row) != 11:
            raise ValueError("nvidia-smi returned an unexpected GPU column count")
        index, uuid, name, total, used, utilization, temperature, power, limit, fan, driver = (
            item.strip() for item in row
        )
        gpu_index = csv_int(index)
        memory_total = csv_int(total, multiplier=1024 * 1024)
        if gpu_index is None or memory_total is None:
            raise ValueError("nvidia-smi returned invalid GPU identity data")
        gpus.append(
            GPUSnapshot(
                index=gpu_index,
                uuid=uuid,
                name=name,
                memory_total=memory_total,
                memory_used=csv_int(used, multiplier=1024 * 1024),
                utilization=csv_float(utilization),
                temperature=csv_float(temperature),
                power_usage=csv_float(power),
                power_limit=csv_float(limit),
                fan_speed=csv_float(fan),
                driver_version=csv_value(driver),
                processes=process_map.get(uuid, []),
            )
        )
    version = gpus[0].driver_version if gpus else None
    return gpus, CollectorStatus(available=True, version=f"nvidia-smi {version or 'unknown'}")


def collect_gpu_snapshot() -> tuple[list[GPUSnapshot], CollectorStatus]:
    try:
        return collect_with_nvml()
    except (pynvml.NVMLError, OSError, AttributeError, ValueError) as nvml_error:
        if shutil.which("nvidia-smi") is None:
            return [], CollectorStatus(
                available=False,
                detail=f"NVML unavailable ({type(nvml_error).__name__}); nvidia-smi not found",
            )
        try:
            return collect_with_nvidia_smi()
        except (OSError, subprocess.SubprocessError, ValueError) as smi_error:
            return [], CollectorStatus(
                available=False,
                detail=f"NVML and nvidia-smi unavailable ({type(smi_error).__name__})",
            )
