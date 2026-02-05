"""
Videos management and metrics visualization routes.
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from admin.dependencies import get_db
from src.repositories import VideoRepository, MetricsRepository
from src.models import Video

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/videos")
async def list_videos(
    request: Request,
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 20,
    account_id: int = None,
):
    """List videos with pagination and optional account filter."""
    video_repo = VideoRepository(db)

    if account_id:
        videos = await video_repo.get_by_account_id(account_id, limit=limit, offset=offset)
        total = await video_repo.count_by_account(account_id)
    else:
        videos = await video_repo.get_with_latest_metrics(limit=limit, offset=offset)
        total = await video_repo.count_all()

    return templates.TemplateResponse(
        "videos/list.html",
        {
            "request": request,
            "videos": videos,
            "total": total,
            "offset": offset,
            "limit": limit,
            "account_id": account_id,
        },
    )


@router.get("/videos/{video_id}")
async def video_detail(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
):
    """View video detail with metrics chart."""
    video_repo = VideoRepository(db)
    metrics_repo = MetricsRepository(db)

    video = await video_repo.get_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Load video with relationships
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.account), selectinload(Video.metrics))
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get latest metrics
    latest_metrics = await metrics_repo.get_latest_metrics_by_video_id(video_id)

    return templates.TemplateResponse(
        "videos/detail.html",
        {
            "request": request,
            "video": video,
            "latest_metrics": latest_metrics,
        },
    )


@router.get("/videos/{video_id}/metrics")
async def video_metrics_api(
    video_id: int,
    db: AsyncSession = Depends(get_db),
):
    """API endpoint returning JSON metrics data for Chart.js."""
    metrics_repo = MetricsRepository(db)

    metrics_history = await metrics_repo.get_metrics_history(video_id, limit=100)

    # Reverse to get chronological order
    metrics_history = list(reversed(metrics_history))

    data = {
        "labels": [m.measured_at.strftime('%Y-%m-%d %H:%M') for m in metrics_history],
        "views": [m.view_count for m in metrics_history],
        "likes": [m.like_count for m in metrics_history],
        "comments": [m.comment_count for m in metrics_history],
    }

    return JSONResponse(content=data)
