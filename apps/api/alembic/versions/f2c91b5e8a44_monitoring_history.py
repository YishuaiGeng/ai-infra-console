"""monitoring history.

Revision ID: f2c91b5e8a44
Revises: e4b6d7a8c901
Create Date: 2026-08-10 00:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2c91b5e8a44"
down_revision: str | None = "e4b6d7a8c901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "server_metric_samples",
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("cpu_utilization", sa.Float()),
        sa.Column("memory_used", sa.BigInteger()),
        sa.Column("memory_total", sa.BigInteger()),
        sa.Column("disk_used", sa.BigInteger()),
        sa.Column("disk_total", sa.BigInteger()),
        sa.Column("network_bytes_sent", sa.BigInteger()),
        sa.Column("network_bytes_received", sa.BigInteger()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name="fk_server_metric_samples_server_id_servers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_server_metric_samples"),
    )
    op.create_index(
        "ix_server_metric_samples_server_id",
        "server_metric_samples",
        ["server_id"],
    )
    op.create_index(
        "ix_server_metric_samples_collected_at",
        "server_metric_samples",
        ["collected_at"],
    )
    op.create_index(
        "ix_server_metric_samples_server_collected",
        "server_metric_samples",
        ["server_id", "collected_at"],
    )


def downgrade() -> None:
    op.drop_table("server_metric_samples")
