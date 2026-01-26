"""
OCR Dashboard V2 - Settings Routes
Settings and utilities API endpoints.
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..config import (
    CACHE_DIR,
    AUTO_RESTART_CONFIG_FILE,
    X11_DISPLAY_CONFIG_FILE,
)

router = APIRouter(prefix="/api", tags=["settings"])

FAVORITES_FILE = Path(__file__).parents[1].parent / "favorites.json"


@router.get("/favorites")
async def get_favorites():
    """Get list of favorite directories."""
    try:
        if FAVORITES_FILE.exists():
            data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            return {"favorites": data if isinstance(data, list) else []}
    except Exception:
        pass
    return {"favorites": []}


@router.post("/favorites")
async def save_favorites(favorites: list[str]):
    """Save list of favorite directories."""
    try:
        FAVORITES_FILE.write_text(json.dumps(favorites, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browse")
async def browse_files(path: str = "/"):
    """Browse filesystem directories."""
    try:
        target = Path(path).expanduser()
        if not target.exists():
            return {"error": "Ścieżka nie istnieje", "items": []}
        
        items = []
        for entry in sorted(target.iterdir()):
            try:
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                })
            except Exception:
                continue
        
        return {
            "path": str(target),
            "parent": str(target.parent) if target.parent != target else None,
            "items": items,
        }
    except Exception as e:
        return {"error": str(e), "items": []}


@router.get("/auto-restart")
async def get_auto_restart_setting():
    """Get auto-restart setting."""
    try:
        if AUTO_RESTART_CONFIG_FILE.exists():
            data = json.loads(AUTO_RESTART_CONFIG_FILE.read_text(encoding="utf-8"))
            return {"enabled": bool(data.get("enabled", False))}
    except Exception:
        pass
    return {"enabled": False}


@router.post("/auto-restart")
async def set_auto_restart_setting(enabled: bool):
    """Set auto-restart setting."""
    from datetime import datetime
    try:
        AUTO_RESTART_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "enabled": bool(enabled),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        AUTO_RESTART_CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/x11-display")
async def get_x11_display_setting():
    """Get X11 display setting."""
    try:
        if X11_DISPLAY_CONFIG_FILE.exists():
            data = json.loads(X11_DISPLAY_CONFIG_FILE.read_text(encoding="utf-8"))
            return {"display": data.get("display", "")}
    except Exception:
        pass
    return {"display": ""}


@router.post("/x11-display")
async def set_x11_display_setting(display: str):
    """Set X11 display setting."""
    from datetime import datetime
    try:
        X11_DISPLAY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "display": display,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        X11_DISPLAY_CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "display": display}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default-source-path")
async def get_default_source_path():
    """Get default source path from environment."""
    default_path = os.environ.get("OCR_DEFAULT_SOURCE_PATH", "")
    return {"path": default_path}
