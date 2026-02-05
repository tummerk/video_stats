"""FastAPI application entry point for admin panel."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from admin.routes import (
    dashboard,
    accounts,
    videos,
    schedules,
    worker,
)
from admin.dependencies import get_db

# Create FastAPI app
app = FastAPI(
    title="Instagram Reels Tracker Admin",
    description="Admin panel for tracking Instagram Reels metrics",
    version="1.0.0",
)

# Include routers
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(accounts.router, tags=["accounts"], prefix="/accounts")
app.include_router(videos.router, tags=["videos"], prefix="/videos")
app.include_router(schedules.router, tags=["schedules"], prefix="/schedules")
app.include_router(worker.router, tags=["worker"], prefix="/worker"])

# Mount static files
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

# Templates are configured per-router in individual route files
