import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command

REQUIRED_TABLES = {
    "users",
    "servers",
    "server_agents",
    "server_model_directories",
    "gpus",
    "gpu_metrics",
    "gpu_processes",
    "server_metrics",
    "models",
    "model_files",
    "model_download_tasks",
    "deployments",
    "deployment_gpus",
    "api_endpoints",
    "notifications",
    "system_settings",
    "audit_logs",
}


def table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_initial_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    config = Config(api_root / "alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    assert REQUIRED_TABLES <= table_names(database_path)

    command.downgrade(config, "base")
    assert not (REQUIRED_TABLES & table_names(database_path))

    command.upgrade(config, "head")
    assert REQUIRED_TABLES <= table_names(database_path)
