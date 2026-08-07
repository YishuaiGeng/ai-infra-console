from datetime import UTC, datetime

from fastapi import FastAPI
from sqlalchemy import select

from ai_infra_api.db.models import ModelFile, Server, ServerModelDirectory
from ai_infra_api.schemas.agent import ModelInventorySnapshot
from ai_infra_api.services.model_inventory import (
    _path_inside,
    persist_model_inventory,
)


def inventory(
    *,
    available: bool = True,
    include_models: bool = True,
) -> ModelInventorySnapshot:
    now = datetime.now(UTC)
    installations = (
        [
            {
                "source": "local",
                "source_id": "Qwen/Qwen3-8B",
                "name": "Qwen/Qwen3-8B",
                "display_name": "Qwen3 8B",
                "architecture": "Qwen3ForCausalLM",
                "model_type": "qwen3",
                "path": "/data/models/Qwen3-8B",
                "size": 100,
                "format": "safetensors",
                "quantization": "BF16",
                "revision": "main",
                "file_count": 2,
                "metadata": {"dtype": "bfloat16"},
            },
            {
                "source": "local",
                "source_id": "escape",
                "name": "escape",
                "path": "/data/models-escape/model.gguf",
                "size": 10,
                "format": "gguf",
            },
            {
                "source": "ollama",
                "source_id": "qwen3:8b",
                "name": "qwen3:8b",
                "path": "ollama://qwen3:8b",
                "size": 200,
                "format": "ollama",
            },
            {
                "source": "ollama",
                "source_id": "invalid",
                "name": "invalid",
                "path": "/not-ollama",
                "size": 1,
                "format": "ollama",
            },
        ]
        if include_models
        else []
    )
    return ModelInventorySnapshot.model_validate(
        {
            "collected_at": now,
            "directories": [
                {
                    "path": "/data/models",
                    "is_default": True,
                    "available": available,
                    "error_code": None if available else "unavailable",
                    "scanned_at": now,
                }
            ],
            "installations": installations,
            "ollama": {
                "available": available,
                "version": "api-tags" if available else None,
            },
        }
    )


async def test_persistence_enforces_roots_and_reconciles_status(app: FastAPI) -> None:
    async with app.state.database.session_factory() as session:
        server = Server(name="service-model-node", type="local", status="online", tags=[])
        session.add(server)
        await session.flush()

        first = await persist_model_inventory(session, server, inventory())
        await session.commit()
        assert first.changed is True
        assert first.installation_count == 2
        paths = set(
            await session.scalars(
                select(ModelFile.path).where(ModelFile.server_id == server.id)
            )
        )
        assert paths == {"/data/models/Qwen3-8B", "ollama://qwen3:8b"}

        same = await persist_model_inventory(session, server, inventory())
        assert same.changed is False

        failed = await persist_model_inventory(
            session,
            server,
            inventory(available=False, include_models=False),
        )
        await session.commit()
        assert failed.changed is True
        assert set(
            await session.scalars(
                select(ModelFile.status).where(ModelFile.server_id == server.id)
            )
        ) == {"stale"}

        recovered = await persist_model_inventory(
            session,
            server,
            inventory(available=True, include_models=False),
        )
        await session.commit()
        assert recovered.changed is True
        assert set(
            await session.scalars(
                select(ModelFile.status).where(ModelFile.server_id == server.id)
            )
        ) == {"missing"}


async def test_unadvertised_directory_is_retained_but_disabled(app: FastAPI) -> None:
    async with app.state.database.session_factory() as session:
        server = Server(name="directory-node", type="local", status="online", tags=[])
        session.add(server)
        await session.flush()
        await persist_model_inventory(session, server, inventory(include_models=False))
        await session.commit()

        empty = ModelInventorySnapshot.model_validate(
            {
                "collected_at": datetime.now(UTC),
                "directories": [],
                "installations": [],
                "ollama": {"available": False},
            }
        )
        result = await persist_model_inventory(session, server, empty)
        await session.commit()
        directory = await session.scalar(
            select(ServerModelDirectory).where(ServerModelDirectory.server_id == server.id)
        )
        assert result.changed is True
        assert directory is not None
        assert directory.is_allowed is False
        assert directory.error_code == "not_advertised"


def test_path_containment_supports_posix_and_windows_without_prefix_confusion() -> None:
    assert _path_inside("/data/models/qwen", "/data/models") is True
    assert _path_inside("/data/models-escape/qwen", "/data/models") is False
    assert _path_inside(r"D:\models\qwen", r"D:\models") is True
    assert _path_inside(r"D:\models-other\qwen", r"D:\models") is False
