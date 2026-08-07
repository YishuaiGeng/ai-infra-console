import uuid

from fastapi import APIRouter, Request, status
from sqlalchemy import select

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.db.models import Server, ServerAgent
from ai_infra_api.dependencies import AdminUser, CurrentUser, DatabaseSession
from ai_infra_api.schemas.agent import (
    AgentTokenResponse,
    ServerRegistrationRequest,
    ServerRegistrationResponse,
)
from ai_infra_api.schemas.infrastructure import ServerDetailResponse, ServerSummaryResponse
from ai_infra_api.schemas.model_inventory import (
    DefaultModelDirectoryRequest,
    ModelDirectoryResponse,
)
from ai_infra_api.services.agent_tokens import revoke_agent_token, rotate_agent_token
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.infrastructure import get_server_detail, list_server_summaries
from ai_infra_api.services.infrastructure_events import publish_model_inventory_update
from ai_infra_api.services.model_reads import (
    list_model_directories,
    set_default_model_directory,
)

router = APIRouter(prefix="/servers", tags=["servers"])


async def server_agent_or_404(session: DatabaseSession, server_id: uuid.UUID) -> ServerAgent:
    agent = await session.scalar(select(ServerAgent).where(ServerAgent.server_id == server_id))
    if agent is None:
        raise AppError(
            status_code=404,
            code="server_not_found",
            message="The server does not exist.",
        )
    return agent


@router.post(
    "/registrations",
    response_model=ServerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_registration(
    payload: ServerRegistrationRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ServerRegistrationResponse:
    if await session.scalar(select(Server.id).where(Server.name == payload.name)) is not None:
        raise AppError(
            status_code=409,
            code="server_name_conflict",
            message="A server with this name already exists.",
        )

    server = Server(
        name=payload.name,
        type=payload.type,
        provider=payload.provider,
        description=payload.description,
        tags=payload.tags,
        status="pending",
    )
    session.add(server)
    await session.flush()
    agent = ServerAgent(server_id=server.id)
    token = rotate_agent_token(agent)
    session.add(agent)
    await record_audit(
        session,
        action="agent.registration.created",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="server",
        resource_id=str(server.id),
    )
    return ServerRegistrationResponse(server_id=server.id, registration_token=token)


@router.post("/{server_id}/agent-token", response_model=AgentTokenResponse)
async def rotate_token(
    server_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> AgentTokenResponse:
    agent = await server_agent_or_404(session, server_id)
    token = rotate_agent_token(agent)
    await record_audit(
        session,
        action="agent.token.rotated",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="server",
        resource_id=str(server_id),
    )
    return AgentTokenResponse(server_id=server_id, registration_token=token)


@router.post("/{server_id}/agent-token/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    server_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> None:
    agent = await server_agent_or_404(session, server_id)
    revoke_agent_token(agent)
    await record_audit(
        session,
        action="agent.token.revoked",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="server",
        resource_id=str(server_id),
    )


@router.get("", response_model=list[ServerSummaryResponse])
async def list_servers(
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> list[ServerSummaryResponse]:
    return await list_server_summaries(
        session,
        offline_seconds=request.app.state.settings.agent_offline_seconds,
    )


@router.get(
    "/{server_id}/model-directories",
    response_model=list[ModelDirectoryResponse],
)
async def server_model_directories(
    server_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
) -> list[ModelDirectoryResponse]:
    if await session.get(Server, server_id) is None:
        raise AppError(
            status_code=404,
            code="server_not_found",
            message="The server does not exist.",
        )
    return await list_model_directories(session, server_id)


@router.put(
    "/{server_id}/model-directories/default",
    response_model=ModelDirectoryResponse,
)
async def change_default_model_directory(
    server_id: uuid.UUID,
    payload: DefaultModelDirectoryRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ModelDirectoryResponse:
    if await session.get(Server, server_id) is None:
        raise AppError(
            status_code=404,
            code="server_not_found",
            message="The server does not exist.",
        )
    result = await set_default_model_directory(session, server_id, payload.directory_id)
    if result is None:
        raise AppError(
            status_code=422,
            code="model_directory_not_allowed",
            message="The default must be an Agent-advertised allowed directory.",
        )
    await record_audit(
        session,
        action="model.directory.default.changed",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="server_model_directory",
        resource_id=str(payload.directory_id),
        details={"server_id": str(server_id)},
    )
    await publish_model_inventory_update(request.app.state.redis, server_id)
    return result


@router.get("/{server_id}", response_model=ServerDetailResponse)
async def server_detail(
    server_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> ServerDetailResponse:
    result = await get_server_detail(
        session,
        server_id,
        offline_seconds=request.app.state.settings.agent_offline_seconds,
    )
    if result is None:
        raise AppError(
            status_code=404,
            code="server_not_found",
            message="The server does not exist.",
        )
    return result
