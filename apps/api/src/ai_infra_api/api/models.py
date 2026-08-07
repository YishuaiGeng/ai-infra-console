import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from ai_infra_api.core.errors import AppError
from ai_infra_api.dependencies import CurrentUser, DatabaseSession
from ai_infra_api.schemas.model_inventory import (
    ModelDetailResponse,
    ModelInstallationResponse,
    ModelInventorySummaryResponse,
)
from ai_infra_api.services.model_reads import (
    get_model_detail,
    list_model_installations,
    model_inventory_summary,
)

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelInstallationResponse])
async def list_models(
    session: DatabaseSession,
    _user: CurrentUser,
    server_id: uuid.UUID | None = None,
    source: Annotated[str | None, Query(max_length=32)] = None,
    format_name: Annotated[str | None, Query(alias="format", max_length=32)] = None,
    status: Annotated[str | None, Query(max_length=32)] = None,
    model_type: Annotated[str | None, Query(max_length=64)] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
) -> list[ModelInstallationResponse]:
    return await list_model_installations(
        session,
        server_id=server_id,
        source=source,
        format_name=format_name,
        status=status,
        model_type=model_type,
        search=search,
    )


@router.get("/models/{model_id}", response_model=ModelDetailResponse)
async def model_detail(
    model_id: uuid.UUID,
    session: DatabaseSession,
    _user: CurrentUser,
) -> ModelDetailResponse:
    result = await get_model_detail(session, model_id)
    if result is None:
        raise AppError(
            status_code=404,
            code="model_not_found",
            message="The model does not exist.",
        )
    return result


@router.get(
    "/model-inventory/summary",
    response_model=ModelInventorySummaryResponse,
)
async def inventory_summary(
    session: DatabaseSession,
    _user: CurrentUser,
) -> ModelInventorySummaryResponse:
    return await model_inventory_summary(session)
