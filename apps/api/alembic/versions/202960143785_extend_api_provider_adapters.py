"""extend api provider adapters.

Revision ID: 202960143785
Revises: 418a2649d5e9
Create Date: 2026-08-10 12:54:33.413896
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '202960143785'
down_revision: str | None = '418a2649d5e9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'api_providers',
        sa.Column('adapter_kind', sa.String(length=32), nullable=False, server_default='openai-compatible'),
    )
    op.add_column(
        'api_providers',
        sa.Column('credential_header', sa.String(length=128), nullable=False, server_default='authorization'),
    )
    op.add_column(
        'api_providers',
        sa.Column('static_headers', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    with op.batch_alter_table('api_providers') as batch_op:
        batch_op.alter_column('adapter_kind', server_default=None)
        batch_op.alter_column('credential_header', server_default=None)
        batch_op.alter_column('static_headers', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('api_providers') as batch_op:
        batch_op.drop_column('static_headers')
        batch_op.drop_column('credential_header')
        batch_op.drop_column('adapter_kind')
