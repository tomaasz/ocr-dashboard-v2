"""
OCR Dashboard V2 - FastAPI Application Entry Point
"""

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import (
    dashboard_router,
    profiles_router,
    profiles_single_router,
    settings_router,
)

# Track server start time for session filtering
SERVER_START_TIME = time.time()

# Create FastAPI app
app = FastAPI(
    title="OCR Dashboard V2",
    description="Dashboard for OCR Farm Management",
    version="1.0.0",
)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(dashboard_router)
app.include_router(profiles_router)
app.include_router(profiles_single_router)  # Singular /api/profile endpoints
app.include_router(settings_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "server_start_time": SERVER_START_TIME,
        "uptime_sec": int(time.time() - SERVER_START_TIME),
    }


@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    print(f"🚀 OCR Dashboard V2 started at {time.strftime('%Y-%m-%d %H:%M:%S')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    print(f"👋 OCR Dashboard V2 stopping at {time.strftime('%Y-%m-%d %H:%M:%S')}")
