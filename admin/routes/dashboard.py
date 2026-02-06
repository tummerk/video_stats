"""
Dashboard route - Overview of system status and statistics.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from admin.dependencies import get_db
from admin.services.worker_monitor import WorkerMonitor
from src.repositories import (
    AccountRepository,
    VideoRepository,
    MetricsRepository,
    MetricScheduleRepository,
)

router = APIRouter()
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def get_worker_status(db: AsyncSession) -> dict:
    """Get worker status from heartbeat table."""
    status_data = await WorkerMonitor.get_worker_status(db, worker_name="unified_worker")

    # Calculate uptime (time since last heartbeat for running workers)
    uptime = None
    if status_data["status"] == "running" and status_data["time_since_heartbeat"]:
        uptime = status_data["time_since_heartbeat"]

    return {
        "status": status_data["status"],
        "last_heartbeat": status_data["last_heartbeat"],
        "uptime": uptime,
        "pid": status_data["pid"],
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
