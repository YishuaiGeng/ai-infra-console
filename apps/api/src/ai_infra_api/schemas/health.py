from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class DependencyStatus(BaseModel):
    status: Literal["ready", "unavailable"]
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: dict[str, DependencyStatus]
