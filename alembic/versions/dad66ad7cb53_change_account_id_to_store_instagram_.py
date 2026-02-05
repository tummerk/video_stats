"""Change Account.id to store Instagram user_pk

Revision ID: dad66ad7cb53
Revises: 20250205_add_user_pk
Create Date: 2026-02-05 07:27:09.596525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dad66ad7cb53'
down_revision: Union[str, Sequence[str], None] = '20250205_add_user_pk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Since there's no data, we can safely recreate the accounts table
    # Drop dependent tables first (cascade)
    op.drop_table('metrics')
    op.drop_table('metric_schedules')
    op.drop_table('videos')
    op.drop_table('accounts')

    # Create accounts table with id as manual PK (Instagram user_pk)
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('profile_url', sa.String(length=512), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # Recreate videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
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
    op.create_index('account_published_idx', 'videos', ['account_id', 'published_at'])

    # Recreate metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), nullable=False),
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
    op.create_index('video_measured_idx', 'metrics', ['video_id', 'measured_at'])

    # Recreate metric_schedules table
    op.create_table(
        'metric_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('schedule_type', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('status_scheduled_idx', 'metric_schedules', ['status', 'scheduled_at'])
    op.create_index('video_schedule_idx', 'metric_schedules', ['video_id', 'scheduled_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables with new structure
    op.drop_table('metrics')
    op.drop_table('metric_schedules')
    op.drop_table('videos')
    op.drop_table('accounts')

    # Recreate accounts table with autoincrement id and separate user_pk column
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_pk', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('profile_url', sa.String(length=512), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_pk'),
        sa.UniqueConstraint('username')
    )

    # Recreate videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
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
    op.create_index('account_published_idx', 'videos', ['account_id', 'published_at'])

    # Recreate metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), nullable=False),
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
    op.create_index('video_measured_idx', 'metrics', ['video_id', 'measured_at'])

    # Recreate metric_schedules table
    op.create_table(
        'metric_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('schedule_type', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('status_scheduled_idx', 'metric_schedules', ['status', 'scheduled_at'])
    op.create_index('video_schedule_idx', 'metric_schedules', ['video_id', 'scheduled_at'])
