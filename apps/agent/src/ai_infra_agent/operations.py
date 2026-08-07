from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ai_infra_agent.collectors.nvidia import collect_gpu_snapshot
from ai_infra_agent.collectors.runtimes import collect_runtime_snapshot
from ai_infra_agent.collectors.system import collect_host_snapshot


class OperationName(StrEnum):
    GET_SYSTEM_INFO = "get_system_info"
    GET_GPU_INFO = "get_gpu_info"
    GET_GPU_PROCESSES = "get_gpu_processes"


class OperationRequest(BaseModel):
    name: OperationName
    payload: dict[str, Any] = Field(default_factory=dict, max_length=0)


class OperationResult(BaseModel):
    name: OperationName
    result: Any


def system_info() -> dict[str, Any]:
    runtimes = collect_runtime_snapshot()
    return collect_host_snapshot(runtimes).model_dump(mode="json")


def gpu_info() -> list[dict[str, Any]]:
    gpus, _ = collect_gpu_snapshot()
    return [gpu.model_dump(mode="json", exclude={"processes"}) for gpu in gpus]


def gpu_processes() -> list[dict[str, Any]]:
    gpus, _ = collect_gpu_snapshot()
    return [
        {"gpu_uuid": gpu.uuid, **process.model_dump(mode="json")}
        for gpu in gpus
        for process in gpu.processes
    ]


HANDLERS: dict[OperationName, Callable[[], Any]] = {
    OperationName.GET_SYSTEM_INFO: system_info,
    OperationName.GET_GPU_INFO: gpu_info,
    OperationName.GET_GPU_PROCESSES: gpu_processes,
}


def dispatch_operation(request: OperationRequest) -> OperationResult:
    handler = HANDLERS[request.name]
    return OperationResult(name=request.name, result=handler())
