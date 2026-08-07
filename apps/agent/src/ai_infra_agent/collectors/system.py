import platform
import sys
from datetime import UTC, datetime

import psutil

from ai_infra_agent.schemas import (
    CPUSnapshot,
    DiskSnapshot,
    HostSnapshot,
    MemorySnapshot,
    NetworkSnapshot,
    RuntimeSnapshot,
)


def cpu_model() -> str | None:
    value = platform.processor().strip()
    return value or None


def disk_snapshots() -> list[DiskSnapshot]:
    snapshots: list[DiskSnapshot] = []
    seen: set[str] = set()
    for partition in psutil.disk_partitions(all=False):
        if partition.mountpoint in seen:
            continue
        seen.add(partition.mountpoint)
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (OSError, PermissionError):
            continue
        snapshots.append(
            DiskSnapshot(
                mountpoint=partition.mountpoint,
                filesystem=partition.fstype or None,
                total=usage.total,
                used=usage.used,
                percent=usage.percent,
            )
        )
    return snapshots


def load_average() -> tuple[float, float, float] | None:
    try:
        first, fifth, fifteenth = psutil.getloadavg()
    except (AttributeError, OSError):
        return None
    return float(first), float(fifth), float(fifteenth)


def collect_host_snapshot(runtime_snapshot: RuntimeSnapshot) -> HostSnapshot:
    memory = psutil.virtual_memory()
    network = psutil.net_io_counters()
    boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=UTC)
    return HostSnapshot(
        hostname=platform.node() or "unknown-host",
        os=platform.system() or "Unknown",
        kernel=platform.release() or "Unknown",
        architecture=platform.machine() or "unknown",
        boot_time=boot_time,
        cpu=CPUSnapshot(
            model=cpu_model(),
            physical_cores=psutil.cpu_count(logical=False),
            logical_cores=psutil.cpu_count(logical=True),
            utilization=psutil.cpu_percent(interval=None),
            load_average=load_average(),
        ),
        memory=MemorySnapshot(total=memory.total, used=memory.used, percent=memory.percent),
        disks=disk_snapshots(),
        network=NetworkSnapshot(
            bytes_sent=network.bytes_sent,
            bytes_received=network.bytes_recv,
        ),
        runtimes=runtime_snapshot,
    )


def python_version() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])
