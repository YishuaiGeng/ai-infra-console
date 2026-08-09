from fastapi import APIRouter, Query

from ai_infra_api.dependencies import CurrentUser, DatabaseSession
from ai_infra_api.schemas.activity import ActivityLogResponse
from ai_infra_api.services.audit import list_activity_logs

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityLogResponse])
async def activity_logs(
    session: DatabaseSession,
    _user: CurrentUser,
    limit: int = Query(default=200, ge=1, le=1_000),
    search: str | None = Query(default=None, max_length=128),
) -> list[ActivityLogResponse]:
    return await list_activity_logs(session, limit=limit, search=search)
