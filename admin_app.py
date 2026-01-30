"""
Instagram Reels Tracker - Admin Panel

FastAPI application for monitoring and managing Instagram Reels data.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.session import get_session
from src.repositories import (
    AccountRepository,
    VideoRepository,
    MetricsRepository,
    MetricScheduleRepository,
)

# Import routes
from admin.routes import dashboard, accounts, videos, schedules, worker
from admin.dependencies import get_db

# Create FastAPI app
app = FastAPI(
    title="Instagram Reels Tracker Admin",
    description="Admin panel for monitoring Instagram Reels data",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="admin/templates")


# Include routers
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(accounts.router, tags=["accounts"])
app.include_router(videos.router, tags=["videos"])
app.include_router(schedules.router, tags=["schedules"])
app.include_router(worker.router, tags=["worker"])


@app.get("/")
async def root():
    """Redirect to dashboard."""
    return RedirectResponse(url="/dashboard")


# Context processor for templates (add common data to all templates)
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Add common context to all templates."""
    response = await call_next(request)

    # Add worker status to context
    async with get_session() as session:
        from src.models import WorkerHeartbeat
        from sqlalchemy import select

        result = await session.execute(
            select(WorkerHeartbeat).where(
                WorkerHeartbeat.worker_name == "unified_worker"
            )
        )
        heartbeat = result.scalar_one_or_none()

        worker_is_running = False
        if heartbeat:
            # Check if last heartbeat is within 2 minutes
            time_since_heartbeat = datetime.now(timezone.utc) - heartbeat.last_heartbeat
            if time_since_heartbeat < timedelta(minutes=2):
                worker_is_running = True

    # This is a simple approach - for production, use proper context processors
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "admin_app:app",
        host=settings.admin_host,
        port=settings.admin_port,
        reload=settings.admin_debug,
    )
