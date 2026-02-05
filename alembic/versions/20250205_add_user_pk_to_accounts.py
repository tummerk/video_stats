"""add user_pk to accounts

Revision ID: 20250205_add_user_pk
Revises: 284ae8b6c888
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250205_add_user_pk'
down_revision: Union[str, Sequence[str], None] = '284ae8b6c888'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_pk column to accounts table
    # First add as nullable to populate existing data
    op.add_column('accounts', sa.Column('user_pk', sa.Integer(), nullable=True))

    # Make it unique after existing rows are updated
    op.create_unique_constraint('uq_accounts_user_pk', 'accounts', ['user_pk'])

    # Then make it non-nullable
    # Note: This requires all existing rows to have a user_pk value
    # You'll need to update existing accounts before this step
    # op.alter_column('accounts', 'user_pk', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_accounts_user_pk', 'accounts')
    op.drop_column('accounts', 'user_pk')
