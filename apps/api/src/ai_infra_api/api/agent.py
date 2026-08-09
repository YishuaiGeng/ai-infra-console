import uuid

from fastapi import APIRouter, Request

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.db.models import ServerAgent
from ai_infra_api.dependencies import CurrentAgent, DatabaseSession
from ai_infra_api.schemas.agent import AgentReportResponse, AgentSnapshot
from ai_infra_api.schemas.deployments import (
    DeploymentOperationProgressRequest,
    DeploymentOperationProgressResponse,
    DeploymentOperationTerminalRequest,
    DeploymentRuntimeExpectation,
    DeploymentRuntimeReport,
    DeploymentTaskClaimResponse,
)
from ai_infra_api.schemas.model_tasks import (
    DeleteTerminalRequest,
    DownloadProgressRequest,
    DownloadProgressResponse,
    DownloadTerminalRequest,
    ModelTaskClaimResponse,
)
from ai_infra_api.services.agent_telemetry import persist_agent_snapshot
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.deployments import (
    DeploymentError,
    apply_runtime_report,
    claim_deployment_operation,
    complete_deployment_operation,
    list_runtime_expectations,
    renew_deployment_operation,
)
from ai_infra_api.services.infrastructure_events import (
    publish_deployment_logs_update,
    publish_deployment_update,
    publish_model_download_update,
    publish_model_inventory_update,
    publish_server_update,
)
from ai_infra_api.services.model_tasks import (
    ModelTaskError,
    claim_model_task,
    complete_delete_task,
    complete_download_task,
    report_download_progress,
)

router = APIRouter(prefix="/agent", tags=["agent"])


def task_error(error: ModelTaskError) -> AppError:
    status_code = 404 if error.code.endswith("_not_found") else 409
    return AppError(status_code=status_code, code=error.code, message=error.message)


def deployment_task_error(error: DeploymentError) -> AppError:
    status_code = 404 if error.code.endswith("_not_found") else 409
    return AppError(status_code=status_code, code=error.code, message=error.message)


async def save_report(
    snapshot: AgentSnapshot,
    request: Request,
    session: DatabaseSession,
    agent: ServerAgent,
) -> tuple[AgentReportResponse, bool]:
    try:
        persistence = await persist_agent_snapshot(
            session,
            agent,
            snapshot,
            metrics_retention_days=request.app.state.settings.metrics_retention_days,
        )
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


@router.post("/model-tasks/claim", response_model=ModelTaskClaimResponse)
async def claim_next_model_task(
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> ModelTaskClaimResponse:
    try:
        task = await claim_model_task(
            session,
            request.app.state.settings,
            agent.server_id,
        )
    except ModelTaskError as exc:
        raise task_error(exc) from exc
    await session.commit()
    return ModelTaskClaimResponse(task=task)


@router.post(
    "/download-tasks/{task_id}/progress",
    response_model=DownloadProgressResponse,
)
async def update_download_progress(
    task_id: str,
    payload: DownloadProgressRequest,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> DownloadProgressResponse:
    try:
        result = await report_download_progress(
            session,
            request.app.state.settings,
            agent.server_id,
            uuid.UUID(task_id),
            payload,
        )
    except (ValueError, ModelTaskError) as exc:
        if isinstance(exc, ModelTaskError):
            raise task_error(exc) from exc
        raise AppError(
            status_code=404,
            code="download_task_not_found",
            message="The download task does not exist.",
        ) from exc
    await session.commit()
    await publish_model_download_update(request.app.state.redis, agent.server_id)
    return result


@router.post("/download-tasks/{task_id}/complete", status_code=204)
async def finish_download_task(
    task_id: str,
    payload: DownloadTerminalRequest,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> None:
    try:
        await complete_download_task(
            session,
            agent.server_id,
            uuid.UUID(task_id),
            payload,
        )
    except (ValueError, ModelTaskError) as exc:
        if isinstance(exc, ModelTaskError):
            raise task_error(exc) from exc
        raise AppError(
            status_code=404,
            code="download_task_not_found",
            message="The download task does not exist.",
        ) from exc
    await session.commit()
    await publish_model_download_update(request.app.state.redis, agent.server_id)


@router.post("/delete-tasks/{task_id}/complete", status_code=204)
async def finish_delete_task(
    task_id: str,
    payload: DeleteTerminalRequest,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> None:
    try:
        result = await complete_delete_task(
            session,
            agent.server_id,
            uuid.UUID(task_id),
            payload,
        )
    except (ValueError, ModelTaskError) as exc:
        if isinstance(exc, ModelTaskError):
            raise task_error(exc) from exc
        raise AppError(
            status_code=404, code="delete_task_not_found", message="The delete task does not exist."
        ) from exc
    await session.commit()
    await publish_model_inventory_update(request.app.state.redis, result.server_id)


@router.post("/deployment-tasks/claim", response_model=DeploymentTaskClaimResponse)
async def claim_next_deployment_task(
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> DeploymentTaskClaimResponse:
    try:
        task = await claim_deployment_operation(
            session,
            request.app.state.settings,
            agent.server_id,
        )
    except DeploymentError as exc:
        raise deployment_task_error(exc) from exc
    await session.commit()
    return DeploymentTaskClaimResponse(task=task)


@router.post(
    "/deployment-operations/{operation_id}/progress",
    response_model=DeploymentOperationProgressResponse,
)
async def update_deployment_operation(
    operation_id: uuid.UUID,
    payload: DeploymentOperationProgressRequest,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> DeploymentOperationProgressResponse:
    try:
        result = await renew_deployment_operation(
            session,
            request.app.state.settings,
            agent.server_id,
            operation_id,
            payload,
        )
    except DeploymentError as exc:
        raise deployment_task_error(exc) from exc
    await session.commit()
    await publish_deployment_update(request.app.state.redis, agent.server_id)
    return result


@router.post("/deployment-operations/{operation_id}/complete", status_code=204)
async def finish_deployment_operation(
    operation_id: uuid.UUID,
    payload: DeploymentOperationTerminalRequest,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> None:
    try:
        server_id, deployment_id, deleted = await complete_deployment_operation(
            session,
            agent.server_id,
            operation_id,
            payload,
        )
    except DeploymentError as exc:
        raise deployment_task_error(exc) from exc
    await record_audit(
        session,
        action="deployment.operation.completed",
        success=payload.outcome == "completed",
        request_id=request_id_from(request),
        resource_type="deployment",
        resource_id=str(deployment_id),
        details={
            "operation_id": str(operation_id),
            "observed_state": payload.observed_state,
            "deleted": deleted,
        },
    )
    await publish_deployment_update(request.app.state.redis, server_id)


@router.post("/deployment-runtimes/report", status_code=204)
async def report_deployment_runtimes(
    payload: DeploymentRuntimeReport,
    request: Request,
    session: DatabaseSession,
    agent: CurrentAgent,
) -> None:
    changed, logs_changed = await apply_runtime_report(
        session,
        request.app.state.settings,
        agent.server_id,
        payload,
    )
    await session.commit()
    if changed:
        await publish_deployment_update(request.app.state.redis, agent.server_id)
    if logs_changed:
        await publish_deployment_logs_update(request.app.state.redis, agent.server_id)


@router.post(
    "/deployment-runtimes/expected",
    response_model=list[DeploymentRuntimeExpectation],
)
async def expected_deployment_runtimes(
    session: DatabaseSession,
    agent: CurrentAgent,
) -> list[DeploymentRuntimeExpectation]:
    return await list_runtime_expectations(session, agent.server_id)
