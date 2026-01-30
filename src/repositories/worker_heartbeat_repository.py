from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import WorkerHeartbeat
from src.repositories.base import BaseRepository


class WorkerHeartbeatRepository(BaseRepository[WorkerHeartbeat]):
    """Repository for WorkerHeartbeat model."""

    def __init__(self, session: AsyncSession):
        super().__init__(WorkerHeartbeat, session)

    async def get_by_worker_name(self, worker_name: str) -> Optional[WorkerHeartbeat]:
        """Get heartbeat by worker name."""
        result = await self.session.execute(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name)
        )
        return result.scalar_one_or_none()
