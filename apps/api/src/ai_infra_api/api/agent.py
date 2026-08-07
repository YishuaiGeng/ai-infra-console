from fastapi import APIRouter, Request

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.db.models import ServerAgent
from ai_infra_api.dependencies import CurrentAgent, DatabaseSession
from ai_infra_api.schemas.agent import AgentReportResponse, AgentSnapshot
from ai_infra_api.services.agent_telemetry import persist_agent_snapshot
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.infrastructure_events import (
    publish_model_inventory_update,
    publish_server_update,
)

router = APIRouter(prefix="/agent", tags=["agent"])


async def save_report(
    snapshot: AgentSnapshot,
    request: Request,
    session: DatabaseSession,
    agent: ServerAgent,
) -> tuple[AgentReportResponse, bool]:
    try:
        persistence = await persist_agent_snapshot(session, agent, snapshot)
    except ValueError as exc:
        await record_audit(
            session,
            action="agent.identity.rejected",
            success=False,
            request_id=request_id_from(request),
            resource_type="server",
            resource_id=str(agent.server_id),
            details={"reason": "hostname_mismatch"},
        )
        raise AppError(
            status_code=409,
            code="agent_identity_conflict",
            message=str(exc),
        ) from exc
    return (
        AgentReportResponse(
            server_id=persistence.server.id,
            offline_after_seconds=request.app.state.settings.agent_offline_seconds,
        ),
        persistence.model_inventory_changed,
    )


@router.post("/register", response_model=AgentReportResponse)
async def register(
    snapshot: AgentSnapshot,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> AgentReportResponse:
    result, model_inventory_changed = await save_report(snapshot, request, session, agent)
    await record_audit(
        session,
        action="agent.registered",
        success=True,
        request_id=request_id_from(request),
        resource_type="server",
        resource_id=str(agent.server_id),
    )
    await publish_server_update(request.app.state.redis, result.server_id)
    if model_inventory_changed:
        await publish_model_inventory_update(request.app.state.redis, result.server_id)
    return result


@router.post("/heartbeat", response_model=AgentReportResponse)
async def heartbeat(
    snapshot: AgentSnapshot,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> AgentReportResponse:
    result, model_inventory_changed = await save_report(snapshot, request, session, agent)
    await publish_server_update(request.app.state.redis, result.server_id)
    if model_inventory_changed:
        await publish_model_inventory_update(request.app.state.redis, result.server_id)
    return result
