"""deployment lifecycle.

Revision ID: e4b6d7a8c901
Revises: a78d1f0b6c21
Create Date: 2026-08-08 06:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4b6d7a8c901"
down_revision: str | None = "a78d1f0b6c21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("deployments") as batch:
        batch.add_column(sa.Column("requested_by_user_id", sa.Uuid()))
        batch.add_column(
            sa.Column(
                "selection_mode",
                sa.String(length=16),
                server_default="automatic",
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "desired_state",
                sa.String(length=32),
                server_default="running",
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column("generation", sa.Integer(), server_default="1", nullable=False)
        )
        batch.add_column(
            sa.Column(
                "health_status",
                sa.String(length=32),
                server_default="unknown",
                nullable=False,
            )
        )
        batch.add_column(sa.Column("health_latency_ms", sa.Float()))
        batch.add_column(sa.Column("last_health_checked_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_reconciled_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("error_code", sa.String(length=64)))
        batch.add_column(sa.Column("error_message", sa.Text()))
        batch.create_foreign_key(
            "fk_deployments_requested_by_user_id_users",
            "users",
            ["requested_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_deployments_requested_by_user_id", ["requested_by_user_id"])
        batch.create_index("ix_deployments_desired_state", ["desired_state"])
        batch.create_index("ix_deployments_health_status", ["health_status"])
        batch.create_index("ix_deployments_last_reconciled_at", ["last_reconciled_at"])
        batch.create_check_constraint("port_valid", "port >= 1024 AND port <= 65535")
        batch.create_check_constraint("generation_positive", "generation >= 1")

    op.execute(
        "UPDATE deployments SET desired_state = "
        "CASE WHEN status IN ('running', 'starting') THEN 'running' ELSE 'stopped' END"
    )

    op.create_table(
        "deployment_operations",
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid()),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token_hash", sa.String(length=64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("request_id", sa.String(length=64)),
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
            "attempt_count >= 0",
            name="ck_deployment_operations_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "generation >= 1",
            name="ck_deployment_operations_generation_positive",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_id"],
            ["deployments.id"],
            name="fk_deployment_operations_deployment_id_deployments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name="fk_deployment_operations_server_id_servers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_deployment_operations_requested_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deployment_operations"),
        sa.UniqueConstraint(
            "lease_token_hash",
            name="uq_deployment_operations_lease_token_hash",
        ),
    )
    op.create_index(
        "ix_deployment_operations_deployment_id",
        "deployment_operations",
        ["deployment_id"],
    )
    op.create_index(
        "ix_deployment_operations_server_id",
        "deployment_operations",
        ["server_id"],
    )
    op.create_index(
        "ix_deployment_operations_requested_by_user_id",
        "deployment_operations",
        ["requested_by_user_id"],
    )
    op.create_index("ix_deployment_operations_action", "deployment_operations", ["action"])
    op.create_index("ix_deployment_operations_status", "deployment_operations", ["status"])
    op.create_index(
        "ix_deployment_operations_lease_expires_at",
        "deployment_operations",
        ["lease_expires_at"],
    )
    op.create_index(
        "ix_deployment_operations_request_id",
        "deployment_operations",
        ["request_id"],
    )
    op.create_index(
        "ix_deployment_operations_server_status_created",
        "deployment_operations",
        ["server_id", "status", "created_at"],
    )

    op.create_table(
        "deployment_logs",
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stream", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["deployment_id"],
            ["deployments.id"],
            name="fk_deployment_logs_deployment_id_deployments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deployment_logs"),
        sa.UniqueConstraint(
            "deployment_id",
            "sequence",
            name="uq_deployment_logs_deployment_id_sequence",
        ),
    )
    op.create_index("ix_deployment_logs_deployment_id", "deployment_logs", ["deployment_id"])
    op.create_index("ix_deployment_logs_timestamp", "deployment_logs", ["timestamp"])
    op.create_index("ix_deployment_logs_created_at", "deployment_logs", ["created_at"])
    op.create_index(
        "ix_deployment_logs_deployment_sequence",
        "deployment_logs",
        ["deployment_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_table("deployment_logs")
    op.drop_table("deployment_operations")

    with op.batch_alter_table("deployments") as batch:
        batch.drop_constraint("generation_positive", type_="check")
        batch.drop_constraint("port_valid", type_="check")
        batch.drop_index("ix_deployments_last_reconciled_at")
        batch.drop_index("ix_deployments_health_status")
        batch.drop_index("ix_deployments_desired_state")
        batch.drop_index("ix_deployments_requested_by_user_id")
        batch.drop_constraint(
            "fk_deployments_requested_by_user_id_users",
            type_="foreignkey",
        )
        batch.drop_column("error_message")
        batch.drop_column("error_code")
        batch.drop_column("last_reconciled_at")
        batch.drop_column("last_health_checked_at")
        batch.drop_column("health_latency_ms")
        batch.drop_column("health_status")
        batch.drop_column("generation")
        batch.drop_column("desired_state")
        batch.drop_column("selection_mode")
        batch.drop_column("requested_by_user_id")
