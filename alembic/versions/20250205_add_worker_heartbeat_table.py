"""Add worker_heartbeats table

Revision ID: 20250205_add_worker_heartbeat
Revises: dad66ad7cb53
Create Date: 2026-02-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250205_add_worker_heartbeat'
down_revision: Union[str, Sequence[str], None] = 'dad66ad7cb53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=255), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='running'),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worker_name')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('worker_heartbeats')
