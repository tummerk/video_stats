"""fix worker_heartbeat timezone

Revision ID: 30f0f1a419c8
Revises: bc7c91a8f446
Create Date: 2026-01-30 12:31:43.247027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30f0f1a419c8'
down_revision: Union[str, Sequence[str], None] = 'bc7c91a8f446'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change last_heartbeat to timezone-aware timestamp
    op.execute("ALTER TABLE worker_heartbeat ALTER COLUMN last_heartbeat TYPE TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to timezone-naive timestamp
    op.execute("ALTER TABLE worker_heartbeat ALTER COLUMN last_heartbeat TYPE TIMESTAMP WITHOUT TIME ZONE")
