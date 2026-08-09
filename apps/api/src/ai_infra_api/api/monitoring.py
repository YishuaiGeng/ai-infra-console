import uuid

from fastapi import APIRouter, Query

from ai_infra_api.dependencies import CurrentUser, DatabaseSession
from ai_infra_api.schemas.monitoring import MetricsHistoryResponse, NotificationListResponse
from ai_infra_api.services.monitoring import list_notifications, metrics_history

router = APIRouter(tags=["monitoring"])


@router.get("/metrics/history", response_model=MetricsHistoryResponse)
async def metric_history(
    session: DatabaseSession,
    _user: CurrentUser,
    window_hours: int = Query(default=24, ge=1, le=720),
    server_id: uuid.UUID | None = None,
) -> MetricsHistoryResponse:
    return await metrics_history(session, window_hours=window_hours, server_id=server_id)


@router.get("/notifications", response_model=NotificationListResponse)
async def notifications(
    session: DatabaseSession,
    _user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> NotificationListResponse:
    return await list_notifications(session, limit=limit)
