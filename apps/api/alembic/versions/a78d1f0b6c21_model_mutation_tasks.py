"""model mutation tasks.

Revision ID: a78d1f0b6c21
Revises: 9df60ca49392
Create Date: 2026-08-08 03:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a78d1f0b6c21"
down_revision: str | None = "9df60ca49392"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE model_download_tasks SET status = 'queued' WHERE status = 'pending'")
    with op.batch_alter_table("model_download_tasks") as batch:
        batch.add_column(sa.Column("directory_id", sa.Uuid()))
        batch.add_column(sa.Column("requested_by_user_id", sa.Uuid()))
        batch.add_column(
            sa.Column("revision", sa.String(length=128), server_default="main", nullable=False)
        )
        batch.add_column(
            sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch.add_column(sa.Column("lease_token_hash", sa.String(length=64)))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_progress_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("cancel_requested_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("error_code", sa.String(length=64)))
        batch.create_foreign_key(
            "fk_model_download_tasks_directory_id_server_model_directories",
            "server_model_directories",
            ["directory_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_model_download_tasks_requested_by_user_id_users",
            "users",
            ["requested_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_model_download_tasks_directory_id", ["directory_id"])
        batch.create_index("ix_model_download_tasks_requested_by_user_id", ["requested_by_user_id"])
        batch.create_index("ix_model_download_tasks_lease_expires_at", ["lease_expires_at"])
        batch.create_index(
            "ix_model_download_tasks_server_status_created",
            ["server_id", "status", "created_at"],
        )
        batch.create_unique_constraint(
            "uq_model_download_tasks_lease_token_hash", ["lease_token_hash"]
        )
        batch.create_check_constraint("downloaded_size_non_negative", "downloaded_size >= 0")
        batch.create_check_constraint(
            "total_size_non_negative", "total_size IS NULL OR total_size >= 0"
        )
        batch.create_check_constraint("attempt_count_non_negative", "attempt_count >= 0")

    op.create_table(
        "model_delete_tasks",
        sa.Column("model_file_id", sa.Uuid()),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("directory_id", sa.Uuid()),
        sa.Column("requested_by_user_id", sa.Uuid()),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token_hash", sa.String(length=64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_model_delete_tasks_attempt_count_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["model_file_id"],
            ["model_files.id"],
            name="fk_model_delete_tasks_model_file_id_model_files",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name="fk_model_delete_tasks_server_id_servers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["directory_id"],
            ["server_model_directories.id"],
            name="fk_model_delete_tasks_directory_id_server_model_directories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_model_delete_tasks_requested_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_delete_tasks"),
        sa.UniqueConstraint("lease_token_hash", name="uq_model_delete_tasks_lease_token_hash"),
    )
    op.create_index("ix_model_delete_tasks_model_file_id", "model_delete_tasks", ["model_file_id"])
    op.create_index("ix_model_delete_tasks_server_id", "model_delete_tasks", ["server_id"])
    op.create_index("ix_model_delete_tasks_directory_id", "model_delete_tasks", ["directory_id"])
    op.create_index(
        "ix_model_delete_tasks_requested_by_user_id",
        "model_delete_tasks",
        ["requested_by_user_id"],
    )
    op.create_index("ix_model_delete_tasks_status", "model_delete_tasks", ["status"])
    op.create_index(
        "ix_model_delete_tasks_lease_expires_at", "model_delete_tasks", ["lease_expires_at"]
    )
    op.create_index(
        "ix_model_delete_tasks_server_status_created",
        "model_delete_tasks",
        ["server_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("model_delete_tasks")

    with op.batch_alter_table("model_download_tasks") as batch:
        batch.drop_constraint("attempt_count_non_negative", type_="check")
        batch.drop_constraint("total_size_non_negative", type_="check")
        batch.drop_constraint("downloaded_size_non_negative", type_="check")
        batch.drop_constraint("uq_model_download_tasks_lease_token_hash", type_="unique")
        batch.drop_index("ix_model_download_tasks_server_status_created")
        batch.drop_index("ix_model_download_tasks_lease_expires_at")
        batch.drop_index("ix_model_download_tasks_requested_by_user_id")
        batch.drop_index("ix_model_download_tasks_directory_id")
        batch.drop_constraint(
            "fk_model_download_tasks_requested_by_user_id_users", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_model_download_tasks_directory_id_server_model_directories",
            type_="foreignkey",
        )
        batch.drop_column("error_code")
        batch.drop_column("cancel_requested_at")
        batch.drop_column("last_progress_at")
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_token_hash")
        batch.drop_column("attempt_count")
        batch.drop_column("revision")
        batch.drop_column("requested_by_user_id")
        batch.drop_column("directory_id")
    op.execute("UPDATE model_download_tasks SET status = 'pending' WHERE status = 'queued'")
