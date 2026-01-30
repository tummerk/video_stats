"""
Worker monitoring service for tracking worker status via heartbeat.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WorkerHeartbeat


class WorkerMonitor:
    """Service for monitoring worker status."""

    HEARTBEAT_TIMEOUT = timedelta(minutes=2)  # Worker considered stopped after 2 minutes

    @staticmethod
    async def get_worker_status(db: AsyncSession, worker_name: str = "unified_worker") -> dict:
        """Get the current status of a worker.

        Args:
            db: Database session
            worker_name: Name of the worker to check

        Returns:
            Dict with status information:
            - status: "running", "stopped", or "unknown"
            - last_heartbeat: datetime of last heartbeat or None
            - time_since_heartbeat: timedelta or None
            - pid: Process ID or None
        """
        result = await db.execute(
            select(WorkerHeartbeat).where(
                WorkerHeartbeat.worker_name == worker_name
            )
        )
        heartbeat = result.scalar_one_or_none()

        if not heartbeat:
            return {
                "status": "unknown",
                "last_heartbeat": None,
                "time_since_heartbeat": None,
                "pid": None,
            }

        time_since_heartbeat = datetime.now(timezone.utc) - heartbeat.last_heartbeat
        is_running = time_since_heartbeat < WorkerMonitor.HEARTBEAT_TIMEOUT

        return {
            "status": "running" if is_running else "stopped",
            "last_heartbeat": heartbeat.last_heartbeat,
            "time_since_heartbeat": time_since_heartbeat,
            "pid": heartbeat.pid,
        }

    @staticmethod
    async def update_heartbeat(
        db: AsyncSession,
        worker_name: str = "unified_worker",
        pid: Optional[int] = None,
    ) -> WorkerHeartbeat:
        """Update or create heartbeat record for a worker.

        Args:
            db: Database session
            worker_name: Name of the worker
            pid: Process ID (optional)

        Returns:
            The created or updated WorkerHeartbeat record
        """
        result = await db.execute(
            select(WorkerHeartbeat).where(
                WorkerHeartbeat.worker_name == worker_name
            )
        )
        heartbeat = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if heartbeat:
            # Update existing heartbeat
            heartbeat.last_heartbeat = now
            heartbeat.status = "running"
            if pid is not None:
                heartbeat.pid = pid
        else:
            # Create new heartbeat record
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                last_heartbeat=now,
                status="running",
                pid=pid,
            )
            db.add(heartbeat)

        await db.flush()
        return heartbeat

    @staticmethod
    async def mark_worker_stopped(
        db: AsyncSession,
        worker_name: str = "unified_worker",
    ) -> Optional[WorkerHeartbeat]:
        """Mark a worker as stopped.

        Args:
            db: Database session
            worker_name: Name of the worker

        Returns:
            The updated heartbeat record or None if not found
        """
        result = await db.execute(
            select(WorkerHeartbeat).where(
                WorkerHeartbeat.worker_name == worker_name
            )
        )
        heartbeat = result.scalar_one_or_none()

        if heartbeat:
            heartbeat.status = "stopped"
            await db.flush()
            return heartbeat

        return None
