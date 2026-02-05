"""
Dashboard route - Overview of system status and statistics.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from admin.dependencies import get_db
from src.repositories import (
    AccountRepository,
    VideoRepository,
    MetricsRepository,
    MetricScheduleRepository,
)
from src.models import WorkerHeartbeat

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


async def get_worker_status(db: AsyncSession) -> dict:
    """Get worker status from heartbeat table."""
    result = await db.execute(
        select(WorkerHeartbeat).where(
            WorkerHeartbeat.worker_name == "unified_worker"
        )
    )
    heartbeat = result.scalar_one_or_none()

    if not heartbeat:
        return {
            "status": "unknown",
            "last_heartbeat": None,
            "uptime": None,
        }

    # Check if last heartbeat is within 2 minutes
    time_since_heartbeat = datetime.now(timezone.utc) - heartbeat.last_heartbeat
    is_running = time_since_heartbeat < timedelta(minutes=2)

    # Calculate uptime
    uptime = None
    if is_running:
        uptime = time_since_heartbeat

    return {
        "status": "running" if is_running else "stopped",
        "last_heartbeat": heartbeat.last_heartbeat,
        "uptime": uptime,
        "pid": heartbeat.pid,
    }


@router.get("/dashboard")
async def dashboard(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """Main dashboard with statistics and worker status."""
    # Get statistics
    account_repo = AccountRepository(db)
    video_repo = VideoRepository(db)
    metrics_repo = MetricsRepository(db)
    schedule_repo = MetricScheduleRepository(db)

    total_accounts = await account_repo.count_all()
    total_videos = await video_repo.count_all()
    total_metrics = await metrics_repo.count_all()
    total_schedules = await schedule_repo.count_all()

    pending_schedules = await schedule_repo.count_by_status("pending")
    failed_schedules = await schedule_repo.count_by_status("failed")
    completed_schedules = await schedule_repo.count_by_status("completed")

    # Get worker status
    worker_status = await get_worker_status(db)

    # Get recent videos
    recent_videos = await video_repo.get_recent(limit=5)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": {
                "total_accounts": total_accounts,
                "total_videos": total_videos,
                "total_metrics": total_metrics,
                "total_schedules": total_schedules,
                "pending_schedules": pending_schedules,
                "failed_schedules": failed_schedules,
                "completed_schedules": completed_schedules,
            },
            "worker_status": worker_status,
            "recent_videos": recent_videos,
        },
    )
