"""Fix worker heartbeats timezone

Revision ID: 20250205_fix_timezone
Revises: 20250205_add_worker_heartbeat
Create Date: 2026-02-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250205_fix_timezone'
down_revision: Union[str, Sequence[str], None] = '20250205_add_worker_heartbeat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - recreate with timezone support."""
    # Drop old table
    op.drop_table('worker_heartbeats')

    # Create new table with TIMESTAMP WITH TIME ZONE
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=255), nullable=False),
        sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='running'),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worker_name')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('worker_heartbeats')
