"""
OCR Dashboard V2 - Profile Routes
Profile management API endpoints.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

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
    return {"success": True, "message": f"Wyczyszczono cache profilu '{safe_name}'"}
