import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ActivityLogResponse(BaseModel):
    id: uuid.UUID
    time: datetime
    user: str
    action: str
    resource: str
    server_id: str | None
    status: Literal["success", "failed", "warning"]
    detail: str
