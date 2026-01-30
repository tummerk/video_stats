from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import MetricSchedule
from src.repositories.base import BaseRepository


class MetricScheduleRepository(BaseRepository[MetricSchedule]):
    """Repository for MetricSchedule model."""

    def __init__(self, session: AsyncSession):
        super().__init__(MetricSchedule, session)

    async def create_schedule(
        self,
        video_id: int,
        schedule_type: str,
        scheduled_at: datetime,
        status: str = "pending"
    ) -> MetricSchedule:
        """Create a new metric collection schedule."""
        return await self.create(
            video_id=video_id,
            schedule_type=schedule_type,
            scheduled_at=scheduled_at,
            status=status
        )

    async def get_pending_schedules(
        self,
        before: datetime | None = None
    ) -> List[MetricSchedule]:
        """Get pending schedules that are due for execution.

        Args:
            before: Only return schedules scheduled before this time.
                   If None, uses current time.
        """
        if before is None:
            before = datetime.utcnow()

        result = await self.session.execute(
            select(MetricSchedule)
            .options(selectinload(MetricSchedule.video))
            .where(
                and_(
                    MetricSchedule.status == "pending",
                    MetricSchedule.scheduled_at <= before
                )
            )
            .order_by(MetricSchedule.scheduled_at)
        )
        return list(result.scalars().all())

    async def mark_completed(
        self,
        schedule_id: int
    ) -> Optional[MetricSchedule]:
        """Mark a schedule as completed."""
        await self.update(
            schedule_id,
            status="completed",
            completed_at=datetime.utcnow()
        )
        return await self.get_by_id(schedule_id)

    async def mark_failed(
        self,
        schedule_id: int
    ) -> Optional[MetricSchedule]:
        """Mark a schedule as failed."""
        await self.update(
            schedule_id,
            status="failed",
            completed_at=datetime.utcnow()
        )
        return await self.get_by_id(schedule_id)

    async def mark_pending(
        self,
        schedule_id: int
    ) -> Optional[MetricSchedule]:
        """Mark a schedule as pending (for retry)."""
        await self.update(
            schedule_id,
            status="pending",
            completed_at=None
        )
        return await self.get_by_id(schedule_id)

    async def get_schedules_by_video(
        self,
        video_id: int,
        status: str | None = None
    ) -> List[MetricSchedule]:
        """Get all schedules for a video.

        Args:
            video_id: Video ID
            status: Filter by status if provided
        """
        query = select(MetricSchedule).where(
            MetricSchedule.video_id == video_id
        )

        if status:
            query = query.where(MetricSchedule.status == status)

        query = query.order_by(MetricSchedule.scheduled_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_completed_schedule(
        self,
        video_id: int,
        schedule_type: str | None = None
    ) -> Optional[MetricSchedule]:
        """Get the latest completed schedule for a video.

        Args:
            video_id: Video ID
            schedule_type: Filter by schedule type if provided
        """
        query = (
            select(MetricSchedule)
            .where(
                and_(
                    MetricSchedule.video_id == video_id,
                    MetricSchedule.status == "completed"
                )
            )
            .order_by(MetricSchedule.scheduled_at.desc())
            .limit(1)
        )

        if schedule_type:
            query = query.where(MetricSchedule.schedule_type == schedule_type)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_schedules_by_video(
        self,
        video_id: int
    ) -> List[MetricSchedule]:
        """Get all pending schedules for a video."""
        result = await self.session.execute(
            select(MetricSchedule)
            .where(
                and_(
                    MetricSchedule.video_id == video_id,
                    MetricSchedule.status == "pending"
                )
            )
            .order_by(MetricSchedule.scheduled_at)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count all schedules."""
        result = await self.session.execute(
            select(func.count(MetricSchedule.id))
        )
        return result.scalar()

    async def count_by_status(self, status: str) -> int:
        """Count schedules by status."""
        result = await self.session.execute(
            select(func.count(MetricSchedule.id))
            .where(MetricSchedule.status == status)
        )
        return result.scalar()

    async def get_all_with_video(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[MetricSchedule]:
        """Get all schedules with video relationship loaded."""
        result = await self.session.execute(
            select(MetricSchedule)
            .options(selectinload(MetricSchedule.video))
            .order_by(MetricSchedule.scheduled_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[MetricSchedule]:
        """Get schedules by status with video relationship loaded."""
        result = await self.session.execute(
            select(MetricSchedule)
            .options(selectinload(MetricSchedule.video))
            .where(MetricSchedule.status == status)
            .order_by(MetricSchedule.scheduled_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
