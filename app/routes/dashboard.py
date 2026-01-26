"""
OCR Dashboard V2 - Dashboard Routes
HTML page views.
"""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parents[1].parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Legacy dashboard (redirect to V2)."""
    return templates.TemplateResponse("dashboard_v2.html", {"request": request})


@router.get("/dashboard2", response_class=HTMLResponse)
async def dashboard2(request: Request):
    """Dashboard 2 view."""
    return templates.TemplateResponse("dashboard2.html", {"request": request})


@router.get("/v2", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    """Dashboard V2 - main view."""
    return templates.TemplateResponse("dashboard_v2.html", {"request": request})
