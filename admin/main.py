"""FastAPI application entry point for admin panel."""
from pathlib import Path

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


@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


@app.get("/health")
async def health_check():
    """Health check endpoint for docker healthcheck."""
    return {"status": "healthy"}


# Include routers
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(accounts.router, tags=["accounts"], prefix="/accounts")
app.include_router(videos.router, tags=["videos"], prefix="/videos")
app.include_router(schedules.router, tags=["schedules"], prefix="/schedules")
app.include_router(worker.router, tags=["worker"], prefix="/worker")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates are configured per-router in individual route files


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "admin.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
