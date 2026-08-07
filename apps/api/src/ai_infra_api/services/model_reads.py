import uuid
from collections import Counter

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import Model, ModelFile, Server, ServerModelDirectory
from ai_infra_api.schemas.model_inventory import (
    ModelDetailResponse,
    ModelDirectoryResponse,
    ModelInstallationResponse,
    ModelInventorySummaryResponse,
    ModelServerResponse,
)


def _public_metadata(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key)[:64]: item[:255]
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def _installation_response(
    model_file: ModelFile,
    model: Model,
    server: Server,
) -> ModelInstallationResponse:
    return ModelInstallationResponse(
        id=model_file.id,
        model_id=model.id,
        source=model.source,
        source_id=model.source_id,
        name=model.name,
        display_name=model.display_name,
        description=model.description,
        architecture=model.architecture,
        model_type=model.model_type,
        metadata=_public_metadata(model.metadata_json),
        server=ModelServerResponse(
            id=server.id,
            name=server.name,
            status=server.status,
            type=server.type,
            host=server.host,
            hostname=server.hostname,
        ),
        directory_id=model_file.directory_id,
        path=model_file.path,
        size=model_file.size,
        file_count=model_file.file_count,
        format=model_file.format,
        quantization=model_file.quantization,
        revision=model_file.revision,
        status=model_file.status,
        last_seen_at=model_file.last_seen_at,
        created_at=model_file.created_at,
        updated_at=model_file.updated_at,
    )


async def list_model_installations(
    session: AsyncSession,
    *,
    server_id: uuid.UUID | None = None,
    source: str | None = None,
    format_name: str | None = None,
    status: str | None = None,
    model_type: str | None = None,
    search: str | None = None,
) -> list[ModelInstallationResponse]:
    query = (
        select(ModelFile, Model, Server)
        .join(Model, Model.id == ModelFile.model_id)
        .join(Server, Server.id == ModelFile.server_id)
        .order_by(Model.name, Server.name, ModelFile.path)
    )
    if server_id is not None:
        query = query.where(ModelFile.server_id == server_id)
    if source is not None:
        query = query.where(Model.source == source)
    if format_name is not None:
        query = query.where(ModelFile.format == format_name)
    if status is not None:
        query = query.where(ModelFile.status == status)
    if model_type is not None:
        query = query.where(Model.model_type == model_type)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Model.name.ilike(pattern),
                Model.display_name.ilike(pattern),
                Model.source_id.ilike(pattern),
                ModelFile.path.ilike(pattern),
                Server.name.ilike(pattern),
            )
        )
    rows = (await session.execute(query)).all()
    return [_installation_response(model_file, model, server) for model_file, model, server in rows]


async def get_model_detail(
    session: AsyncSession,
    model_id: uuid.UUID,
) -> ModelDetailResponse | None:
    model = await session.get(Model, model_id)
    if model is None:
        return None
    rows = (
        await session.execute(
            select(ModelFile, Server)
            .join(Server, Server.id == ModelFile.server_id)
            .where(ModelFile.model_id == model.id)
            .order_by(Server.name, ModelFile.path)
        )
    ).all()
    return ModelDetailResponse(
        id=model.id,
        source=model.source,
        source_id=model.source_id,
        name=model.name,
        display_name=model.display_name,
        description=model.description,
        architecture=model.architecture,
        model_type=model.model_type,
        metadata=_public_metadata(model.metadata_json),
        locations=[
            _installation_response(model_file, model, server) for model_file, server in rows
        ],
    )


async def list_model_directories(
    session: AsyncSession,
    server_id: uuid.UUID,
) -> list[ModelDirectoryResponse]:
    directories = list(
        await session.scalars(
            select(ServerModelDirectory)
            .where(ServerModelDirectory.server_id == server_id)
            .order_by(ServerModelDirectory.path)
        )
    )
    if not directories:
        return []
    count_rows = (
        await session.execute(
            select(ModelFile.directory_id, func.count(ModelFile.id))
            .where(
                ModelFile.directory_id.in_([item.id for item in directories]),
                ModelFile.status == "discovered",
            )
            .group_by(ModelFile.directory_id)
        )
    ).all()
    counts: dict[uuid.UUID, int] = {
        directory_id: int(count) for directory_id, count in count_rows if directory_id is not None
    }
    return [
        ModelDirectoryResponse(
            id=item.id,
            server_id=item.server_id,
            path=item.path,
            is_default=item.is_default,
            is_allowed=item.is_allowed,
            is_available=item.is_available,
            error_code=item.error_code,
            last_scanned_at=item.last_scanned_at,
            model_count=int(counts.get(item.id, 0)),
        )
        for item in directories
    ]


async def set_default_model_directory(
    session: AsyncSession,
    server_id: uuid.UUID,
    directory_id: uuid.UUID,
) -> ModelDirectoryResponse | None:
    directory = await session.scalar(
        select(ServerModelDirectory).where(
            ServerModelDirectory.id == directory_id,
            ServerModelDirectory.server_id == server_id,
            ServerModelDirectory.is_allowed.is_(True),
            ServerModelDirectory.is_available.is_(True),
        )
    )
    if directory is None:
        return None
    await session.execute(
        update(ServerModelDirectory)
        .where(ServerModelDirectory.server_id == server_id)
        .values(is_default=False)
    )
    directory.is_default = True
    await session.flush()
    responses = await list_model_directories(session, server_id)
    return next(item for item in responses if item.id == directory_id)


async def model_inventory_summary(session: AsyncSession) -> ModelInventorySummaryResponse:
    installations = await list_model_installations(session)
    current = [item for item in installations if item.status == "discovered"]
    latest = [item.last_seen_at for item in installations if item.last_seen_at is not None]
    return ModelInventorySummaryResponse(
        model_count=len({item.model_id for item in current}),
        installation_count=len(installations),
        current_installation_count=len(current),
        server_count=len({item.server.id for item in current}),
        total_size=sum(item.size or 0 for item in current),
        formats=dict(Counter(item.format or "unknown" for item in current)),
        latest_scanned_at=max(latest, default=None),
    )
