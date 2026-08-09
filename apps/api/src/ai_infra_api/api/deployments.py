import uuid
from typing import Literal

from fastapi import APIRouter, Query, Request, status

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.db.models import Deployment
from ai_infra_api.dependencies import AdminUser, CurrentUser, DatabaseSession
from ai_infra_api.schemas.deployments import (
    DeploymentApiTestRequest,
    DeploymentApiTestResponse,
    DeploymentCreateRequest,
    DeploymentDeleteRequest,
    DeploymentLogResponse,
    DeploymentResponse,
    DeploymentTargetResponse,
)
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.deployments import (
    DeploymentError,
    create_deployment,
    deployment_response,
    get_deployment,
    list_deployment_logs,
    list_deployment_targets,
    list_deployments,
    queue_deployment_action,
    retry_deployment,
    test_deployment_api_endpoint,
    validate_deployment_action_target,
)
from ai_infra_api.services.infrastructure_events import publish_deployment_update

router = APIRouter(tags=["deployments"])


def deployment_error(error: DeploymentError) -> AppError:
    not_found = {
        "deployment_not_found",
        "deployment_operation_not_found",
        "model_file_not_found",
        "server_not_found",
    }
    conflict = {
        "deployment_name_conflict",
        "deployment_port_conflict",
        "deployment_gpu_conflict",
        "deployment_operation_conflict",
        "model_deletion_active",
        "server_offline",
        "agent_unavailable",
        "docker_unavailable",
        "agent_deployment_disabled",
        "gpu_unavailable",
        "insufficient_gpus",
        "deployment_not_running",
        "deployment_not_retryable",
    }
    return AppError(
        status_code=404 if error.code in not_found else 409 if error.code in conflict else 422,
        code=error.code,
        message=error.message,
    )


async def _deployment_or_404(
    session: DatabaseSession,
    deployment_id: uuid.UUID,
) -> Deployment:
    deployment = await get_deployment(session, deployment_id)
    if deployment is None:
        raise AppError(
            status_code=404,
            code="deployment_not_found",
            message="The deployment does not exist.",
        )
    return deployment


@router.get("/deployment-targets", response_model=list[DeploymentTargetResponse])
async def deployment_targets(
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> list[DeploymentTargetResponse]:
    return await list_deployment_targets(session, request.app.state.settings)


@router.get("/deployments", response_model=list[DeploymentResponse])
async def deployment_list(
    session: DatabaseSession,
    _user: CurrentUser,
    server_id: uuid.UUID | None = None,
    status_filter: Literal[
        "queued",
        "starting",
        "running",
        "stopping",
        "stopped",
        "restarting",
        "deleting",
        "failed",
        "unknown",
    ]
    | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=128),
) -> list[DeploymentResponse]:
    return await list_deployments(
        session,
        server_id=server_id,
        status=status_filter,
        search=search,
    )


@router.post(
    "/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def deployment_create(
    payload: DeploymentCreateRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    try:
        deployment, operation = await create_deployment(
            session,
            request.app.state.settings,
            payload,
            admin,
            request_id=request_id_from(request),
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc
    await record_audit(
        session,
        action="deployment.created",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        details={
            "server_id": str(deployment.server_id),
            "model_file_id": str(deployment.model_file_id),
            "operation_id": str(operation.id),
        },
    )
    await session.refresh(deployment)
    await publish_deployment_update(request.app.state.redis, deployment.server_id)
    return await deployment_response(session, deployment)


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def deployment_detail(
    deployment_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
) -> DeploymentResponse:
    deployment = await _deployment_or_404(session, deployment_id)
    return await deployment_response(session, deployment)


async def _queue_action(
    deployment_id: uuid.UUID,
    action: Literal["start", "stop", "restart"],
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    deployment = await _deployment_or_404(session, deployment_id)
    try:
        await validate_deployment_action_target(
            session,
            request.app.state.settings,
            deployment,
            action,
        )
        operation = await queue_deployment_action(
            session,
            deployment,
            action,
            admin,
            request_id=request_id_from(request),
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc
    await record_audit(
        session,
        action=f"deployment.{action}.requested",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        details={"operation_id": str(operation.id)},
    )
    await session.refresh(deployment)
    await publish_deployment_update(request.app.state.redis, deployment.server_id)
    return await deployment_response(session, deployment)


@router.post("/deployments/{deployment_id}/start", response_model=DeploymentResponse)
async def deployment_start(
    deployment_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    return await _queue_action(deployment_id, "start", request, session, admin)


@router.post("/deployments/{deployment_id}/stop", response_model=DeploymentResponse)
async def deployment_stop(
    deployment_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    return await _queue_action(deployment_id, "stop", request, session, admin)


@router.post("/deployments/{deployment_id}/restart", response_model=DeploymentResponse)
async def deployment_restart(
    deployment_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    return await _queue_action(deployment_id, "restart", request, session, admin)


@router.post("/deployments/{deployment_id}/retry", response_model=DeploymentResponse)
async def deployment_retry(
    deployment_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    deployment = await _deployment_or_404(session, deployment_id)
    try:
        await validate_deployment_action_target(
            session,
            request.app.state.settings,
            deployment,
            "start",
        )
        operation = await retry_deployment(
            session,
            deployment,
            admin,
            request_id=request_id_from(request),
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc
    await record_audit(
        session,
        action="deployment.retry.requested",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        details={"operation_id": str(operation.id)},
    )
    await session.refresh(deployment)
    await publish_deployment_update(request.app.state.redis, deployment.server_id)
    return await deployment_response(session, deployment)


@router.delete("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def deployment_delete(
    deployment_id: uuid.UUID,
    payload: DeploymentDeleteRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DeploymentResponse:
    deployment = await _deployment_or_404(session, deployment_id)
    if payload.confirmation != deployment.name:
        raise AppError(
            status_code=422,
            code="deployment_delete_confirmation_mismatch",
            message="Type the exact deployment name to confirm deletion.",
        )
    try:
        await validate_deployment_action_target(
            session,
            request.app.state.settings,
            deployment,
            "delete",
        )
        operation = await queue_deployment_action(
            session,
            deployment,
            "delete",
            admin,
            request_id=request_id_from(request),
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc
    await record_audit(
        session,
        action="deployment.delete.requested",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        details={"operation_id": str(operation.id)},
    )
    await session.refresh(deployment)
    await publish_deployment_update(request.app.state.redis, deployment.server_id)
    return await deployment_response(session, deployment)


@router.get(
    "/deployments/{deployment_id}/logs",
    response_model=list[DeploymentLogResponse],
)
async def deployment_logs(
    deployment_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1_000),
    search: str | None = Query(default=None, max_length=128),
) -> list[DeploymentLogResponse]:
    try:
        return await list_deployment_logs(
            session,
            deployment_id,
            after=after,
            limit=limit,
            search=search,
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc


@router.post(
    "/deployments/{deployment_id}/test-api",
    response_model=DeploymentApiTestResponse,
)
async def deployment_test_api(
    deployment_id: uuid.UUID,
    payload: DeploymentApiTestRequest,
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> DeploymentApiTestResponse:
    try:
        return await test_deployment_api_endpoint(
            session,
            deployment_id,
            payload,
            timeout_seconds=request.app.state.settings.api_test_timeout_seconds,
        )
    except DeploymentError as exc:
        raise deployment_error(exc) from exc
