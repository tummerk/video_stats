"""
Worker status monitoring routes.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from admin.dependencies import get_db
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
            "pid": None,
        }

    # Check if last heartbeat is within 2 minutes
    time_since_heartbeat = datetime.now(timezone.utc) - heartbeat.last_heartbeat
    is_running = time_since_heartbeat < timedelta(minutes=2)

    return {
        "status": "running" if is_running else "stopped",
        "last_heartbeat": heartbeat.last_heartbeat,
        "time_since_heartbeat": str(time_since_heartbeat).split('.')[0],
        "pid": heartbeat.pid,
    }


@router.get("/worker/status")
async def worker_status_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Worker status page."""
    status = await get_worker_status(db)

    return templates.TemplateResponse(
        "worker/status.html",
        {
            "request": request,
            "worker_status": status,
        },
    )


@router.get("/worker/status/api")
async def worker_status_api(
    db: AsyncSession = Depends(get_db),
):
    """API endpoint for worker status."""
    status = await get_worker_status(db)
    return JSONResponse(content=status)
