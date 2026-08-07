"""model inventory state.

Revision ID: 9df60ca49392
Revises: c35f1476e62f
Create Date: 2026-08-08 02:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9df60ca49392"
down_revision: str | None = "c35f1476e62f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("server_model_directories") as batch:
        batch.add_column(
            sa.Column(
                "is_available",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch.add_column(sa.Column("last_scanned_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("error_code", sa.String(length=64)))

    with op.batch_alter_table("model_files") as batch:
        batch.add_column(sa.Column("directory_id", sa.Uuid()))
        batch.add_column(
            sa.Column("file_count", sa.Integer(), server_default="1", nullable=False)
        )
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key(
            "fk_model_files_directory_id_server_model_directories",
            "server_model_directories",
            ["directory_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_model_files_directory_id", ["directory_id"])
        batch.create_index("ix_model_files_last_seen_at", ["last_seen_at"])


def downgrade() -> None:
    with op.batch_alter_table("model_files") as batch:
        batch.drop_index("ix_model_files_last_seen_at")
        batch.drop_index("ix_model_files_directory_id")
        batch.drop_constraint(
            "fk_model_files_directory_id_server_model_directories",
            type_="foreignkey",
        )
        batch.drop_column("last_seen_at")
        batch.drop_column("file_count")
        batch.drop_column("directory_id")

    with op.batch_alter_table("server_model_directories") as batch:
        batch.drop_column("error_code")
        batch.drop_column("last_scanned_at")
        batch.drop_column("is_available")
