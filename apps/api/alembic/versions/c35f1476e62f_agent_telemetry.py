"""agent telemetry.

Revision ID: c35f1476e62f
Revises: 71ec4261e708
Create Date: 2026-08-08 01:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c35f1476e62f"
down_revision: str | None = "71ec4261e708"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "server_metrics",
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("uptime_seconds", sa.BigInteger(), nullable=True),
        sa.Column("cpu_utilization", sa.Float(), nullable=True),
        sa.Column("memory_used", sa.BigInteger(), nullable=True),
        sa.Column("memory_total", sa.BigInteger(), nullable=True),
        sa.Column("disk_used", sa.BigInteger(), nullable=True),
        sa.Column("disk_total", sa.BigInteger(), nullable=True),
        sa.Column("network_bytes_sent", sa.BigInteger(), nullable=True),
        sa.Column("network_bytes_received", sa.BigInteger(), nullable=True),
        sa.Column("runtime_info", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_server_metrics_collected_at", "server_metrics", ["collected_at"])
    op.create_index("ix_server_metrics_server_id", "server_metrics", ["server_id"], unique=True)
    op.create_table(
        "gpu_processes",
        sa.Column("gpu_id", sa.Uuid(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("command", sa.String(length=512), nullable=True),
        sa.Column("memory_used", sa.BigInteger(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["gpu_id"], ["gpus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gpu_id", "pid"),
    )
    op.create_index("ix_gpu_processes_collected_at", "gpu_processes", ["collected_at"])
    op.create_index("ix_gpu_processes_gpu_id", "gpu_processes", ["gpu_id"])


def downgrade() -> None:
    op.drop_index("ix_gpu_processes_gpu_id", table_name="gpu_processes")
    op.drop_index("ix_gpu_processes_collected_at", table_name="gpu_processes")
    op.drop_table("gpu_processes")
    op.drop_index("ix_server_metrics_server_id", table_name="server_metrics")
    op.drop_index("ix_server_metrics_collected_at", table_name="server_metrics")
    op.drop_table("server_metrics")
