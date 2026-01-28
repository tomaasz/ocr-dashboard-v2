"""
OCR Dashboard V2 - Profile Routes
Profile management API endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..services import process as process_service
from ..services import profiles as profile_service
from ..utils import validate_profile_name

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
async def get_profiles():
    """List all available profiles."""
    profiles_list = profile_service.list_profiles(include_default=True)
    return {"profiles": profiles_list}


@router.get("/active-dir")
async def get_active_profile_dir(profile: str):
    """Get active Chrome profile directory for a profile."""
    try:
        safe_name = validate_profile_name(profile)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nieprawidłowa nazwa profilu")

    active_dir = profile_service.get_active_chrome_profile(safe_name)
    return {"profile": safe_name, "active_dir": active_dir}


@router.post("/create")
async def create_profile(name: str):
    """Create a new profile."""
    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    success, message = profile_service.create_profile(safe_name)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.delete("/{name}")
async def delete_profile(name: str):
    """Delete a profile."""
    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    success, message = profile_service.delete_profile(safe_name)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.post("/{name}/reset")
async def reset_profile(name: str):
    """Reset profile (clear cache)."""
    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile_dir = profile_service.get_profile_dir(safe_name)
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{safe_name}' nie istnieje")

    profile_service.clear_profile_cache(profile_dir)
    profile_service.clear_profile_cache(profile_dir)
    return {"success": True, "message": f"Wyczyszczono cache profilu '{safe_name}'"}


@router.post("/login")
async def login_profile_endpoint(payload: dict):
    """Start login helper process."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Brak nazwy profilu")

    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    success, message = process_service.start_login_process(safe_name)
    if not success:
        # If it's already running, it might be OK or not. Frontend expects success to start polling.
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.get("/login/log")
async def get_login_log(name: str, tail: int = 100):
    """Get tail of login log."""
    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Determine log file path - must match process.py
    # process.py uses: cwd / "logs" / "profiles" / f"{profile_name}.login.log"
    # We need to find cwd. In routes, we can assume relative to app root?
    # Best to ask process service for log path or construct safely.
    # process.py: cwd = Path(__file__).parents[2]

    from pathlib import Path

    cwd = Path(__file__).parents[2]  # app/routes/profiles.py -> app/routes -> app -> root
    log_file = cwd / "logs" / "profiles" / f"{safe_name}.login.log"

    if not log_file.exists():
        return {"log": ""}

    try:
        # Simple tail implementation
        lines = []
        # Check file size?
        # Use simple read for now, optimization later if needed
        # Read last N bytes?
        # Or read all lines and take last N
        with open(log_file, encoding="utf-8", errors="replace") as f:
            # Efficient tailing for large files is better but for login log (short lived) readlines is fine
            all_lines = f.readlines()
            lines = all_lines[-tail:]

        return {"log": "".join(lines)}
    except Exception as e:
        return {"log": f"[Error reading log: {e}]"}


# Alias router for singular /api/profile access if needed
# OR: we simple add the route here but internally it is mounted at /api/profiles
# The frontend requests /api/profile/{name}/start (Singular)
# But this router key prefix is /api/profiles (Plural)
# We can add a specialized router for singular access or just bind it here and assume main.py handles mounting.

single_router = APIRouter(prefix="/api/profile", tags=["profile"])


@single_router.post("/{name}/start")
async def start_profile_endpoint(name: str, headed: bool = False):
    """Start profile worker."""

    try:
        safe_name = validate_profile_name(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    success, message = process_service.start_profile_process(safe_name, headed=headed)
    if not success:
        # Return a 200 OK with success=False or 400? Frontend checks response.ok
        # If already running, frontend expects success/info.
        # But generic error should be 400.
        if "już pracuje" in message:
            return {"success": False, "message": message}
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}
