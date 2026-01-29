"""initial

Revision ID: 57a9647a16b9
Revises:
Create Date: 2026-01-29 19:37:07.211032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57a9647a16b9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('profile_url', sa.String(length=512), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'])

    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('video_id', sa.String(length=100), nullable=False),
        sa.Column('shortcode', sa.String(length=50), nullable=False),
        sa.Column('video_url', sa.String(length=1024), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('audio_url', sa.String(length=1024), nullable=True),
        sa.Column('audio_file_path', sa.String(length=1024), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shortcode'),
        sa.UniqueConstraint('video_id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'])
    op.create_index(op.f('ix_videos_video_id'), 'videos', ['video_id'], unique=True)
    op.create_index(op.f('ix_videos_shortcode'), 'videos', ['shortcode'], unique=True)
    op.create_index('account_published_idx', 'videos', ['account_id', 'published_at'])

    # Create metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.BigInteger(), nullable=False),
        sa.Column('like_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('save_count', sa.Integer(), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=False),
        sa.Column('measured_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metrics_id'), 'metrics', ['id'])
    op.create_index('video_measured_idx', 'metrics', ['video_id', 'measured_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order due to foreign keys
    op.drop_index('video_measured_idx', table_name='metrics')
    op.drop_index(op.f('ix_metrics_id'), table_name='metrics')
    op.drop_table('metrics')

    op.drop_index('account_published_idx', table_name='videos')
    op.drop_index(op.f('ix_videos_shortcode'), table_name='videos')
    op.drop_index(op.f('ix_videos_video_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')

    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_table('accounts')
