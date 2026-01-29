from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import Video
from src.repositories.base import BaseRepository


class VideoRepository(BaseRepository[Video]):
    """Repository for Video model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Video, session)

    async def get_by_shortcode(self, shortcode: str) -> Optional[Video]:
        """Get video by shortcode with relationships."""
        result = await self.session.execute(
            select(Video)
            .options(selectinload(Video.account), selectinload(Video.metrics))
            .where(Video.shortcode == shortcode)
        )
        return result.scalar_one_or_none()

    async def get_by_video_id(self, video_id: str) -> Optional[Video]:
        """Get video by Instagram video ID."""
        result = await self.session.execute(
            select(Video)
            .where(Video.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def get_by_account_id(
        self,
        account_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Video]:
        """Get videos by account ID with pagination."""
        result = await self.session.execute(
            select(Video)
            .where(Video.account_id == account_id)
            .order_by(Video.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_shortcode_with_metrics(self, shortcode: str) -> Optional[Video]:
        """Get video by shortcode with all relationships."""
        result = await self.session.execute(
            select(Video)
            .options(
                selectinload(Video.account),
                selectinload(Video.metrics)
            )
            .where(Video.shortcode == shortcode)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_account_id(self, account_id: int) -> Optional[Video]:
        """Get the most recent video for an account by published_at."""
        result = await self.session.execute(
            select(Video)
            .where(Video.account_id == account_id)
            .order_by(Video.published_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_or_update_by_shortcode(
        self,
        shortcode: str,
        **kwargs
    ) -> Video:
        """Create video if not exists, otherwise update."""
        video = await self.get_by_shortcode(shortcode)

        if video:
            # Update existing video (only allow certain fields to update)
            updatable_fields = [
                'caption', 'duration_seconds', 'audio_url',
                'audio_file_path', 'transcription', 'video_url'
            ]
            for key, value in kwargs.items():
                if key in updatable_fields:
                    setattr(video, key, value)
            await self.session.flush()
            await self.session.refresh(video)
            return video
        else:
            # Create new video
            return await self.create(shortcode=shortcode, **kwargs)

    async def get_videos_without_metrics(self, limit: int = 100) -> List[Video]:
        """Get videos that don't have any metrics yet."""
        from sqlalchemy import exists
        from src.models import Metrics

        result = await self.session.execute(
            select(Video)
            .options(selectinload(Video.account))
            .where(
                ~exists()
                .where(Metrics.video_id == Video.id)
            )
            .order_by(Video.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_videos_with_account(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Video]:
        """Get all videos with account relationship loaded."""
        result = await self.session.execute(
            select(Video)
            .options(selectinload(Video.account))
            .order_by(Video.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_videos_by_ids(
        self,
        video_ids: List[int]
    ) -> List[Video]:
        """Get videos by list of IDs."""
        result = await self.session.execute(
            select(Video)
            .options(selectinload(Video.account))
            .where(Video.id.in_(video_ids))
        )
        return list(result.scalars().all())

    async def get_videos_for_schedule_update(self, limit: int = 100) -> List[Video]:
        """Get videos that need schedule creation or update.

        Returns videos ordered by published_at (newest first).
        """
        from sqlalchemy import exists
        from src.models import MetricSchedule

        # Get videos without any schedules
        result = await self.session.execute(
            select(Video)
            .options(selectinload(Video.account))
            .where(
                ~exists()
                .where(MetricSchedule.video_id == Video.id)
            )
            .order_by(Video.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
