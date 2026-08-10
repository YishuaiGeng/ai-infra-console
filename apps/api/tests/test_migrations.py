import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from ai_infra_api.core.config import get_settings
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
    "server_metric_samples",
    "models",
    "model_files",
    "model_download_tasks",
    "model_delete_tasks",
    "deployments",
    "deployment_gpus",
    "deployment_operations",
    "deployment_logs",
    "api_endpoints",
    "api_providers",
    "api_accounts",
    "api_credentials",
    "api_account_models",
    "api_usage_snapshots",
    "api_balance_snapshots",
    "api_health_checks",
    "api_sync_runs",
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


def column_names(database_path: Path, table: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def test_initial_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    config = Config(api_root / "alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    assert REQUIRED_TABLES <= table_names(database_path)
    assert {"is_available", "last_scanned_at", "error_code"} <= column_names(
        database_path, "server_model_directories"
    )
    assert {"directory_id", "file_count", "last_seen_at"} <= column_names(
        database_path, "model_files"
    )
    assert {
        "directory_id",
        "revision",
        "attempt_count",
        "lease_token_hash",
        "error_code",
    } <= column_names(database_path, "model_download_tasks")
    assert {
        "requested_by_user_id",
        "selection_mode",
        "desired_state",
        "generation",
        "health_status",
        "last_reconciled_at",
        "error_code",
    } <= column_names(database_path, "deployments")
    assert {
        "deployment_id",
        "action",
        "status",
        "generation",
        "lease_token_hash",
        "request_id",
    } <= column_names(database_path, "deployment_operations")
    assert {"adapter_kind", "credential_header", "static_headers"} <= column_names(
        database_path, "api_providers"
    )

    command.downgrade(config, "base")
    assert not (REQUIRED_TABLES & table_names(database_path))

    command.upgrade(config, "head")
    assert REQUIRED_TABLES <= table_names(database_path)


def test_environment_database_url_accepts_percent_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration%21.db"
    monkeypatch.setenv(
        "AI_INFRA_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("AI_INFRA_ENVIRONMENT", "test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config(api_root / "alembic.ini"), "head")
    finally:
        get_settings.cache_clear()

    assert REQUIRED_TABLES <= table_names(database_path)
