from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from admin.routes import dashboard, accounts, videos, schedules, worker

app = FastAPI(title="Video Stats Admin")

# Mount static files
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

# Include routers
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(accounts.router, tags=["accounts"])
app.include_router(videos.router, tags=["videos"])
app.include_router(schedules.router, tags=["schedules"])
app.include_router(worker.router, tags=["worker"])


@app.get("/")
async def root():
    """Redirect root to dashboard."""
    return RedirectResponse(url="/dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
