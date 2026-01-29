from typing import List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Metrics
from src.repositories.base import BaseRepository


class MetricsRepository(BaseRepository[Metrics]):
    """Repository for Metrics model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Metrics, session)

    async def create_metrics_snapshot(
        self,
        video_id: int,
        view_count: int,
        like_count: int,
        comment_count: int,
        followers_count: int,
        save_count: int | None = None,
    ) -> Metrics:
        """Create a new metrics snapshot for a video."""
        return await self.create(
            video_id=video_id,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            save_count=save_count,
            followers_count=followers_count,
        )

    async def get_latest_metrics_by_video_id(
        self,
        video_id: int
    ) -> Metrics | None:
        """Get the latest metrics snapshot for a video."""
        result = await self.session.execute(
            select(Metrics)
            .where(Metrics.video_id == video_id)
            .order_by(desc(Metrics.measured_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_metrics_history(
        self,
        video_id: int,
        limit: int = 100
    ) -> List[Metrics]:
        """Get metrics history for a video."""
        result = await self.session.execute(
            select(Metrics)
            .where(Metrics.video_id == video_id)
            .order_by(desc(Metrics.measured_at))
            .limit(limit)
        )
        return list(result.scalars().all())
