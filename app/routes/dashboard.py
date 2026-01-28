"""
OCR Dashboard V2 - Dashboard Routes
HTML page views.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import config
from ..services import process as process_service
from ..services import profiles as profile_service

try:
    import psycopg2
    import psycopg2.extras

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

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
    active_count = 0

    for p_name in profiles:
        # Check if profile has running processes
        pids = process_service.get_profile_pids(p_name)
        running_pids = [pid for pid in pids if process_service.pid_is_running(pid)]

        # Determine status based on running processes
        if running_pids:
            status = "active"
            active_count += 1
        else:
            status = "idle"

        profiles_data.append(
            {
                "name": p_name,
                "status": status,
                "processed": 0,  # Could be enhanced with real data from database
                "tokens_k": 0,
                "errors": 0,
            }
        )

    # Statistics - enhanced with real active worker count
    stats = {
        "today_scans": 0,
        "total_processed": 0,
        "active_workers": active_count,
        "errors": 0,
    }

    return {
        "stats": stats,
        "profiles": profiles_data,
    }


@router.get("/api/logs")
async def get_logs(profile: str = None, level: str = None, limit: int = 100):
    """Get activity logs from database."""
    logs = []

    if not HAS_PSYCOPG2:
        return {"logs": [], "error": "psycopg2 not available"}

    # Get database DSN from config or environment
    import os

    pg_dsn = (
        os.environ.get("OCR_PG_DSN") or "postgresql://tomaasz:123Karinka!%40%23@127.0.0.1:5432/ocr"
    )

    try:
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Build query with filters
            query = """
                SELECT 
                    id,
                    event_type,
                    component,
                    profile_name,
                    triggered_by,
                    reason,
                    is_automatic,
                    event_timestamp,
                    error_message
                FROM system_activity_log
                WHERE 1=1
            """
            params = []

            if profile and profile != "all":
                query += " AND profile_name = %s"
                params.append(profile)

            # Map level filter to event types
            if level and level != "all":
                if level == "error":
                    query += " AND (error_message IS NOT NULL OR event_type LIKE '%error%')"
                elif level == "warning":
                    query += " AND (event_type LIKE '%stop%' OR event_type LIKE '%limit%')"
                elif level == "info":
                    query += " AND event_type LIKE '%start%'"

            query += " ORDER BY event_timestamp DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                # Determine log level based on event type
                event_type = row.get("event_type", "")
                if row.get("error_message") or "error" in event_type.lower():
                    log_level = "ERROR"
                elif "stop" in event_type or "limit" in event_type:
                    log_level = "WARNING"
                else:
                    log_level = "INFO"

                # Format timestamp
                ts = row.get("event_timestamp")
                time_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "-"

                # Build message
                profile_name = row.get("profile_name") or ""
                reason = row.get("reason") or event_type
                component = row.get("component") or ""
                message = f"[{component}] {profile_name}: {reason}"
                if row.get("error_message"):
                    message += f" - {row['error_message']}"

                logs.append(
                    {
                        "id": row.get("id"),
                        "time": time_str,
                        "level": log_level,
                        "message": message,
                        "profile": profile_name,
                        "event_type": event_type,
                    }
                )

        conn.close()

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return {"logs": [], "error": str(e)}

    return {"logs": logs}
