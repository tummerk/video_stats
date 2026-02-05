"""
Metric schedules management routes.
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from admin.dependencies import get_db
from src.repositories import MetricScheduleRepository, VideoRepository
from src.models import MetricSchedule

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/schedules")
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 50,
    status: str = None,
):
    """List metric schedules with optional status filter."""
    schedule_repo = MetricScheduleRepository(db)

    if status:
        schedules = await schedule_repo.get_by_status(status, limit=limit, offset=offset)
        # Count by status
        from sqlalchemy import func
        from src.models import MetricSchedule as ScheduleModel
        result = await db.execute(
            select(func.count(ScheduleModel.id)).where(ScheduleModel.status == status)
        )
        total = result.scalar()
    else:
        schedules = await schedule_repo.get_all_with_video(limit=limit, offset=offset)
        total = await schedule_repo.count_all()

    return templates.TemplateResponse(
        "schedules/list.html",
        {
            "request": request,
            "schedules": schedules,
            "total": total,
            "offset": offset,
            "limit": limit,
            "status_filter": status,
        },
    )


@router.post("/schedules/{schedule_id}/retry")
async def retry_schedule(
    request: Request,
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed schedule."""
    schedule_repo = MetricScheduleRepository(db)

    schedule = await schedule_repo.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Mark as pending
    await schedule_repo.mark_pending(schedule_id)
    await db.commit()

    return RedirectResponse(url="/schedules?status=failed", status_code=303)


@router.post("/videos/{video_id}/collect-metrics")
async def trigger_metrics_collection(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger immediate metrics collection for a video."""
    from datetime import datetime, timezone

    schedule_repo = MetricScheduleRepository(db)

    # Create an immediate schedule
    await schedule_repo.create_schedule(
        video_id=video_id,
        schedule_type="manual",
        scheduled_at=datetime.now(timezone.utc),
        status="pending"
    )
    await db.commit()

    return RedirectResponse(url=f"/videos/{video_id}", status_code=303)
