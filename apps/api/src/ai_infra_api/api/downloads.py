import uuid
from typing import Literal

from fastapi import APIRouter, Query, Request, status

from ai_infra_api.core.errors import AppError
from ai_infra_api.core.middleware import request_id_from
from ai_infra_api.dependencies import AdminUser, CurrentUser, DatabaseSession
from ai_infra_api.schemas.model_tasks import (
    CatalogModelResponse,
    CatalogSearchResponse,
    DownloadCreateRequest,
    DownloadTargetResponse,
    DownloadTaskResponse,
    ModelDeleteRequest,
    ModelDeleteTaskResponse,
    ModelProvider,
)
from ai_infra_api.services.audit import record_audit
from ai_infra_api.services.infrastructure_events import (
    publish_model_download_update,
    publish_model_inventory_update,
)
from ai_infra_api.services.model_catalog import (
    ProviderCatalogError,
    get_catalog_model,
    search_catalog,
)
from ai_infra_api.services.model_tasks import (
    ModelTaskError,
    cancel_download_task,
    create_delete_task,
    create_download_task,
    delete_response,
    download_response,
    get_delete_task,
    get_download_task,
    list_download_targets,
    list_download_tasks,
    retry_download_task,
)

router = APIRouter(tags=["model tasks"])


def task_error(error: ModelTaskError) -> AppError:
    statuses = {
        "server_not_found": 404,
        "model_installation_not_found": 404,
        "download_task_not_found": 404,
        "delete_task_not_found": 404,
        "download_already_active": 409,
        "model_already_installed": 409,
        "delete_already_active": 409,
        "model_installation_in_use": 409,
        "server_offline": 409,
        "agent_unavailable": 409,
    }
    return AppError(
        status_code=statuses.get(error.code, 422),
        code=error.code,
        message=error.message,
    )


def provider_error(error: ProviderCatalogError) -> AppError:
    statuses = {
        "not_found": 404,
        "rate_limited": 429,
        "timeout": 504,
        "authentication": 502,
        "unavailable": 502,
    }
    return AppError(
        status_code=statuses.get(error.code, 502),
        code=f"provider_{error.code}",
        message=error.public_message,
        details={"provider": error.provider},
    )


@router.get("/catalog/models", response_model=CatalogSearchResponse)
async def catalog_models(
    request: Request,
    _user: CurrentUser,
    query: str = Query(default="", max_length=128),
    provider: ModelProvider | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CatalogSearchResponse:
    try:
        return await search_catalog(
            request.app.state.settings,
            query=query,
            provider=provider,
            limit=limit,
        )
    except ModelTaskError as exc:
        raise task_error(exc) from exc


@router.get("/catalog/models/detail", response_model=CatalogModelResponse)
async def catalog_model_detail(
    request: Request,
    _user: CurrentUser,
    provider: ModelProvider,
    source_id: str = Query(min_length=3, max_length=255),
) -> CatalogModelResponse:
    try:
        return await get_catalog_model(request.app.state.settings, provider, source_id)
    except ModelTaskError as exc:
        raise task_error(exc) from exc
    except ProviderCatalogError as exc:
        raise provider_error(exc) from exc


@router.post(
    "/downloads",
    response_model=DownloadTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def queue_download(
    payload: DownloadCreateRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DownloadTaskResponse:
    try:
        task, server = await create_download_task(
            session,
            request.app.state.settings,
            payload,
            admin,
        )
    except ModelTaskError as exc:
        raise task_error(exc) from exc
    await record_audit(
        session,
        action="model.download.created",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="model_download_task",
        resource_id=str(task.id),
        details={"server_id": str(server.id), "provider": task.source},
    )
    await session.refresh(task)
    await publish_model_download_update(request.app.state.redis, server.id)
    return download_response(task, server)


@router.get("/download-targets", response_model=list[DownloadTargetResponse])
async def download_targets(
    request: Request,
    session: DatabaseSession,
    _user: CurrentUser,
) -> list[DownloadTargetResponse]:
    return await list_download_targets(session, request.app.state.settings)


@router.get("/downloads", response_model=list[DownloadTaskResponse])
async def downloads(
    session: DatabaseSession,
    _user: CurrentUser,
    server_id: uuid.UUID | None = None,
    status_filter: Literal[
        "queued",
        "downloading",
        "cancelling",
        "completed",
        "failed",
        "cancelled",
    ]
    | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=128),
) -> list[DownloadTaskResponse]:
    return await list_download_tasks(
        session,
        server_id=server_id,
        status=status_filter,
        search=search,
    )


@router.get("/downloads/{task_id}", response_model=DownloadTaskResponse)
async def download_detail(
    task_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
) -> DownloadTaskResponse:
    row = await get_download_task(session, task_id)
    if row is None:
        raise AppError(
            status_code=404,
            code="download_task_not_found",
            message="The download task does not exist.",
        )
    return download_response(*row)


async def _mutate_download(
    task_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
    action: Literal["cancel", "retry"],
) -> DownloadTaskResponse:
    row = await get_download_task(session, task_id)
    if row is None:
        raise AppError(
            status_code=404,
            code="download_task_not_found",
            message="The download task does not exist.",
        )
    task, server = row
    try:
        if action == "cancel":
            await cancel_download_task(task)
        else:
            await retry_download_task(task)
    except ModelTaskError as exc:
        raise task_error(exc) from exc
    await record_audit(
        session,
        action=f"model.download.{action}",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="model_download_task",
        resource_id=str(task.id),
    )
    await session.refresh(task)
    await publish_model_download_update(request.app.state.redis, server.id)
    return download_response(task, server)


@router.post("/downloads/{task_id}/cancel", response_model=DownloadTaskResponse)
async def cancel_download(
    task_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DownloadTaskResponse:
    return await _mutate_download(task_id, request, session, admin, "cancel")


@router.post("/downloads/{task_id}/retry", response_model=DownloadTaskResponse)
async def retry_download(
    task_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> DownloadTaskResponse:
    return await _mutate_download(task_id, request, session, admin, "retry")


@router.post(
    "/model-files/{model_file_id}/delete",
    response_model=ModelDeleteTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_model_deletion(
    model_file_id: uuid.UUID,
    payload: ModelDeleteRequest,
    request: Request,
    session: DatabaseSession,
    admin: AdminUser,
) -> ModelDeleteTaskResponse:
    try:
        task, server = await create_delete_task(
            session,
            request.app.state.settings,
            model_file_id,
            payload.confirmation,
            admin,
        )
    except ModelTaskError as exc:
        raise task_error(exc) from exc
    await record_audit(
        session,
        action="model.installation.delete.requested",
        success=True,
        request_id=request_id_from(request),
        actor_user_id=admin.id,
        resource_type="model_delete_task",
        resource_id=str(task.id),
        details={"server_id": str(server.id), "model_file_id": str(model_file_id)},
    )
    await session.refresh(task)
    await publish_model_inventory_update(request.app.state.redis, server.id)
    return delete_response(task, server)


@router.get("/model-deletions/{task_id}", response_model=ModelDeleteTaskResponse)
async def model_deletion_detail(
    task_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
) -> ModelDeleteTaskResponse:
    row = await get_delete_task(session, task_id)
    if row is None:
        raise AppError(
            status_code=404,
            code="delete_task_not_found",
            message="The delete task does not exist.",
        )
    return delete_response(*row)
