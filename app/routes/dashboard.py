"""
OCR Dashboard V2 - Dashboard Routes
HTML page views.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import config
from ..services import profiles as profile_service

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parents[1].parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Legacy dashboard (redirect to V2)."""
    return await dashboard_v2(request)


@router.get("/dashboard2", response_class=HTMLResponse)
async def dashboard2(request: Request):
    """Dashboard 2 view."""
    # This might also need context if it uses the same base, but for now focusing on main v2
    return templates.TemplateResponse("dashboard2.html", {"request": request})


@router.get("/v2", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    """Dashboard V2 - main view."""
    profiles = profile_service.list_profiles(include_default=True)

    # Enrich profiles with mocked status for initial render (optional, but helps avoid undefined checks in template if any)
    # The template iterates 'profiles', so a simple list of strings might need to be dicts if template expects objects
    # Looking at template: {% for profile in profiles %} ... {{ profile.name }}
    # list_profiles returns strings. We need to wrap them ONLY IF the template expects objects.
    # checking template: {{ profile.name }} -> Yes, it expects objects.

    profiles_data = []
    for p_name in profiles:
        profiles_data.append(
            {
                "name": p_name,
                "status": "idle",  # Default state
                "processed": 0,
                "tokens_k": 0,
                "errors": 0,
            }
        )

    return templates.TemplateResponse(
        "dashboard_v2.html",
        {
            "request": request,
            "profiles": profiles_data,
            "limit_worker_url": config.LIMIT_WORKER_URL or "",
        },
    )


@router.get("/api/stats/v2")
async def get_stats_v2():
    """Get dashboard statistics and profiles data."""
    profiles = profile_service.list_profiles(include_default=True)

    profiles_data = []
    for p_name in profiles:
        profiles_data.append(
            {
                "name": p_name,
                "status": "idle",  # Default state - could be enhanced with real status
                "processed": 0,
                "tokens_k": 0,
                "errors": 0,
            }
        )

    # Mock statistics - could be enhanced with real data from database
    stats = {
        "today_scans": 0,
        "total_processed": 0,
        "active_workers": 0,
        "errors": 0,
    }

    return {
        "stats": stats,
        "profiles": profiles_data,
    }
