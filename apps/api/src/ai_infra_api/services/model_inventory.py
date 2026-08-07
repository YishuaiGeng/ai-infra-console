from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.models import Model, ModelFile, Server, ServerModelDirectory
from ai_infra_api.schemas.agent import ModelInstallationSnapshot, ModelInventorySnapshot


@dataclass(slots=True)
class InventoryPersistenceResult:
    changed: bool
    installation_count: int


def _assign(row: object, attribute: str, value: object) -> bool:
    if getattr(row, attribute) == value:
        return False
    setattr(row, attribute, value)
    return True


def _path_inside(path: str, root: str) -> bool:
    try:
        path_type = PureWindowsPath if "\\" in root else PurePosixPath
        candidate = path_type(path)
        parent = path_type(root)
        return candidate == parent or candidate.is_relative_to(parent)
    except (TypeError, ValueError):
        return False


def _directory_for_installation(
    installation: ModelInstallationSnapshot,
    directories: list[ServerModelDirectory],
) -> ServerModelDirectory | None:
    if installation.source == "ollama":
        return None
    return next(
        (
            directory
            for directory in directories
            if directory.is_allowed
            and directory.is_available
            and _path_inside(installation.path, directory.path)
        ),
        None,
    )


async def persist_model_inventory(
    session: AsyncSession,
    server: Server,
    inventory: ModelInventorySnapshot | None,
) -> InventoryPersistenceResult:
    if inventory is None:
        return InventoryPersistenceResult(changed=False, installation_count=0)

    changed = False
    directories = list(
        await session.scalars(
            select(ServerModelDirectory).where(
                ServerModelDirectory.server_id == server.id
            )
        )
    )
    directories_by_path = {item.path: item for item in directories}
    advertised_paths = {item.path for item in inventory.directories}
    current_default = next(
        (item for item in directories if item.is_default and item.path in advertised_paths),
        None,
    )
    reported_default = next(
        (item.path for item in inventory.directories if item.is_default),
        None,
    )
    default_path = current_default.path if current_default is not None else reported_default

    for reported in inventory.directories:
        directory = directories_by_path.get(reported.path)
        if directory is None:
            directory = ServerModelDirectory(
                server_id=server.id,
                path=reported.path,
                is_default=reported.path == default_path,
                is_allowed=True,
                is_available=reported.available,
                last_scanned_at=reported.scanned_at,
                error_code=reported.error_code,
            )
            session.add(directory)
            directories.append(directory)
            directories_by_path[reported.path] = directory
            changed = True
            continue
        changed |= _assign(directory, "is_allowed", True)
        changed |= _assign(directory, "is_available", reported.available)
        changed |= _assign(directory, "error_code", reported.error_code)
        changed |= _assign(directory, "is_default", directory.path == default_path)
        directory.last_scanned_at = reported.scanned_at

    for directory in directories:
        if directory.path in advertised_paths:
            continue
        changed |= _assign(directory, "is_allowed", False)
        changed |= _assign(directory, "is_available", False)
        changed |= _assign(directory, "error_code", "not_advertised")
        changed |= _assign(directory, "is_default", False)

    await session.flush()
    models = list(await session.scalars(select(Model)))
    models_by_key = {(item.source, item.source_id): item for item in models}
    accepted: list[tuple[ModelInstallationSnapshot, Model, ServerModelDirectory | None]] = []
    for installation in inventory.installations:
        directory = _directory_for_installation(installation, directories)
        if installation.source != "ollama" and directory is None:
            continue
        if installation.source == "ollama" and not installation.path.startswith("ollama://"):
            continue
        key = (installation.source, installation.source_id)
        model = models_by_key.get(key)
        metadata = dict(sorted(installation.metadata.items()))
        if model is None:
            model = Model(
                source=installation.source,
                source_id=installation.source_id,
                name=installation.name,
                display_name=installation.display_name,
                architecture=installation.architecture,
                model_type=installation.model_type,
                metadata_json=metadata,
            )
            session.add(model)
            models_by_key[key] = model
            changed = True
        else:
            changed |= _assign(model, "name", installation.name)
            changed |= _assign(model, "display_name", installation.display_name)
            changed |= _assign(model, "architecture", installation.architecture)
            changed |= _assign(model, "model_type", installation.model_type)
            changed |= _assign(model, "metadata_json", metadata)
        accepted.append((installation, model, directory))

    await session.flush()
    existing_files = list(
        await session.scalars(select(ModelFile).where(ModelFile.server_id == server.id))
    )
    files_by_path = {item.path: item for item in existing_files}
    model_by_id = {item.id: item for item in models_by_key.values()}
    seen_paths: set[str] = set()
    for installation, model, directory in accepted:
        seen_paths.add(installation.path)
        model_file = files_by_path.get(installation.path)
        if model_file is None:
            model_file = ModelFile(
                model_id=model.id,
                server_id=server.id,
                directory_id=directory.id if directory is not None else None,
                path=installation.path,
                size=installation.size,
                file_count=installation.file_count,
                format=installation.format,
                quantization=installation.quantization,
                source=installation.source,
                revision=installation.revision,
                status="discovered",
                last_seen_at=inventory.collected_at,
            )
            session.add(model_file)
            files_by_path[installation.path] = model_file
            changed = True
            continue
        changed |= _assign(model_file, "model_id", model.id)
        changed |= _assign(
            model_file,
            "directory_id",
            directory.id if directory is not None else None,
        )
        changed |= _assign(model_file, "size", installation.size)
        changed |= _assign(model_file, "file_count", installation.file_count)
        changed |= _assign(model_file, "format", installation.format)
        changed |= _assign(model_file, "quantization", installation.quantization)
        changed |= _assign(model_file, "source", installation.source)
        changed |= _assign(model_file, "revision", installation.revision)
        changed |= _assign(model_file, "status", "discovered")
        model_file.last_seen_at = inventory.collected_at

    directories_by_id = {item.id: item for item in directories}
    for model_file in existing_files:
        if model_file.path in seen_paths:
            continue
        model = model_by_id.get(model_file.model_id)
        if model is not None and model.source == "ollama":
            target_status = "missing" if inventory.ollama.available else "stale"
        else:
            directory = (
                directories_by_id.get(model_file.directory_id)
                if model_file.directory_id is not None
                else None
            )
            target_status = (
                "missing"
                if directory is not None and directory.is_allowed and directory.is_available
                else "stale"
            )
        changed |= _assign(model_file, "status", target_status)

    return InventoryPersistenceResult(changed=changed, installation_count=len(accepted))
