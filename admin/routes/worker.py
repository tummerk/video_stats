"""
Worker status monitoring routes.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.dependencies import get_db
from admin.services.worker_monitor import WorkerMonitor

router = APIRouter()
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def get_worker_status(db: AsyncSession) -> dict:
    """Get worker status from heartbeat table."""
    status_data = await WorkerMonitor.get_worker_status(db, worker_name="unified_worker")

    # Format time_since_heartbeat for display
    if status_data["time_since_heartbeat"]:
        time_str = str(status_data["time_since_heartbeat"]).split('.')[0]
    else:
        time_str = None

    return {
        "status": status_data["status"],
        "last_heartbeat": status_data["last_heartbeat"],
        "time_since_heartbeat": time_str,
        "pid": status_data["pid"],
    }


@router.get("/status")
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


@router.get("/status/api")
async def worker_status_api(
    db: AsyncSession = Depends(get_db),
):
    """API endpoint for worker status."""
    status = await get_worker_status(db)
    return JSONResponse(content=status)
