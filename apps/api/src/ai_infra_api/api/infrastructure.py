from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ai_infra_api.dependencies import CurrentUser, DatabaseSession
from ai_infra_api.schemas.infrastructure import (
    GPUResponse,
    InfrastructureSummaryResponse,
)
from ai_infra_api.services.infrastructure import infrastructure_summary, list_gpus
from ai_infra_api.services.infrastructure_events import stream_infrastructure_events

router = APIRouter(tags=["infrastructure"])


@router.get("/gpus", response_model=list[GPUResponse])
async def gpu_inventory(
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> list[GPUResponse]:
    return await list_gpus(
        session,
        offline_seconds=request.app.state.settings.agent_offline_seconds,
    )


@router.get("/infrastructure/summary", response_model=InfrastructureSummaryResponse)
async def summary(
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> InfrastructureSummaryResponse:
    return await infrastructure_summary(
        session,
        offline_seconds=request.app.state.settings.agent_offline_seconds,
    )


@router.get("/infrastructure/events")
async def events(request: Request, _user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(
        stream_infrastructure_events(request, request.app.state.redis),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
