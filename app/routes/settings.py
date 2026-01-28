"""
OCR Dashboard V2 - Settings Routes
Settings and utilities API endpoints.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import (
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
        FAVORITES_FILE.write_text(
            json.dumps(favorites, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
                items.append(
                    {
                        "name": entry.name,
                        "path": str(entry),
                        "is_dir": entry.is_dir(),
                    }
                )
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
        AUTO_RESTART_CONFIG_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
        X11_DISPLAY_CONFIG_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"success": True, "display": display}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default-source-path")
async def get_default_source_path():
    """Get default source path from environment."""
    # 1. Próba pobrania z bazy danych (pierwszy katalog wymagający OCR)
    try:
        from ..utils.db import execute_single

        query = """
            SELECT source_path 
            FROM v_source_path_stats 
            WHERE remaining_to_ocr > 0 
            ORDER BY source_path ASC 
            LIMIT 1
        """
        row = execute_single(query)
        if row and row[0]:
            path = str(row[0]).strip()
            # Sprawdź czy ścieżka fizycznie istnieje (opcjonalne, ale dobre dla UX)
            if os.path.exists(path):
                return {"path": path}
    except Exception:
        # Ignorujemy błędy DB (np. brak połączenia) i idziemy do fallbacków
        pass

    # 2. Lista zmiennych środowiskowych do sprawdzenia w kolejności priorytetu
    env_vars = ["OCR_DEFAULT_SOURCE_PATH", "OCR_REMOTE_SOURCE_DIR", "OCR_SOURCE_DIR"]

    for var in env_vars:
        path = os.environ.get(var, "")
        if path:
            return {"path": path}

    # Fallback: sprawdź czy istnieje katalog 'source' w katalogu domowym
    home = Path.home()
    source_dir = home / "source"
    if source_dir.exists() and source_dir.is_dir():
        return {"path": str(source_dir)}

    # Ostateczny fallback: katalog domowy
    return {"path": str(home)}


@router.post("/restart")
async def restart_application():
    """Restart the application by exiting the process (systemd will restart it)."""
    import asyncio
    import signal
    import subprocess
    import time

    from ..services import process as process_service

    # Best-effort activity logging
    try:
        from ocr_engine.utils.activity_logger import ActivityLogger

        ActivityLogger().log_restart(
            component="web_dashboard",
            reason="Manual restart triggered via dashboard API",
        )
    except Exception:
        pass

    project_root = Path(__file__).parents[2]
    start_script = project_root / "scripts" / "start_web.sh"
    restart_log = project_root / "logs" / "restart.log"

    def _stop_workers_best_effort() -> None:
        """Terminate OCR worker processes and related browser helpers."""
        patterns = [
            "python3 run.py",
            "python run.py",
            "playwright/driver/node",
            "cli.js run-driver",
            "chrome-linux64/chrome",
            "chromium",
            "google-chrome",
            "Xvfb",
            "xvfb-run",
        ]
        pids = process_service.find_pids_by_patterns(patterns)
        for pid in pids:
            process_service.terminate_pid(pid)

        # Give processes a moment to exit before restart
        time.sleep(1.0)

    def do_restart() -> None:
        """
        If not under systemd, spawn a new instance via start_web.sh,
        then terminate this process. Under systemd, just exit and let it restart.
        """
        _stop_workers_best_effort()
        try:
            # systemd sets INVOCATION_ID for services
            under_systemd = bool(os.environ.get("INVOCATION_ID"))
        except Exception:
            under_systemd = False

        if not under_systemd and start_script.exists():
            try:
                restart_log.parent.mkdir(parents=True, exist_ok=True)
                out = open(restart_log, "a", encoding="utf-8")
            except Exception:
                out = subprocess.DEVNULL

            try:
                subprocess.Popen(
                    ["/bin/bash", str(start_script)],
                    cwd=str(project_root),
                    start_new_session=True,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                )
            except Exception:
                pass

        # Graceful shutdown first
        os.kill(os.getpid(), signal.SIGTERM)

        # Fallback hard exit if graceful shutdown hangs
        try:
            time.sleep(3)
            os.kill(os.getpid(), signal.SIGKILL)
        except Exception:
            pass

    # Schedule restart after response is sent
    asyncio.create_task(asyncio.sleep(0.5)).add_done_callback(lambda _: do_restart())

    return {"success": True, "message": "Aplikacja zostanie zrestartowana za chwilę"}


@router.post("/cleanup")
async def cleanup_folders(request: dict):
    """Clean up temporary folders."""
    import shutil
    from datetime import datetime

    targets = request.get("targets", [])
    force = request.get("force", False)

    # Define folder paths relative to project root
    project_root = Path(__file__).parents[1].parent

    folder_map = {
        "jobs": project_root / "jobs",
        "logs": project_root / "logs",
        "artifacts": project_root / "artifacts",
        "test-results": project_root / "test-results",
        "pycache": project_root / "__pycache__",
    }

    cleaned = []
    errors = []

    for target in targets:
        if target not in folder_map:
            errors.append(f"Nieznany folder: {target}")
            continue

        folder = folder_map[target]

        if not folder.exists():
            continue

        try:
            # For __pycache__, recursively remove all __pycache__ folders
            if target == "pycache":
                for pycache_dir in project_root.rglob("__pycache__"):
                    try:
                        shutil.rmtree(pycache_dir)
                    except Exception:
                        pass
                cleaned.append(target)
            else:
                # Remove all contents of the folder but keep the folder itself
                for item in folder.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        errors.append(f"{target}/{item.name}: {e!s}")
                cleaned.append(target)

        except Exception as e:
            errors.append(f"{target}: {e!s}")

    return {
        "success": len(cleaned) > 0,
        "cleaned": cleaned,
        "errors": errors if errors else None,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/autorestart")
async def get_autorestart():
    """Get auto-restart configuration status."""
    try:
        if AUTO_RESTART_CONFIG_FILE.exists():
            data = json.loads(AUTO_RESTART_CONFIG_FILE.read_text(encoding="utf-8"))
            return {"enabled": data.get("enabled", False)}
    except Exception:
        pass
    return {"enabled": False}


@router.post("/autorestart")
async def set_autorestart(enabled: bool):
    """Set auto-restart configuration."""
    try:
        AUTO_RESTART_CONFIG_FILE.write_text(
            json.dumps({"enabled": enabled}, indent=2), encoding="utf-8"
        )
        return {"success": True, "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/x11-display")
async def get_x11_display():
    """Get X11 display configuration."""
    try:
        if X11_DISPLAY_CONFIG_FILE.exists():
            data = json.loads(X11_DISPLAY_CONFIG_FILE.read_text(encoding="utf-8"))
            return {"display": data.get("display", ":0")}
    except Exception:
        pass
    return {"display": ":0"}


@router.post("/settings/x11-display")
async def set_x11_display(display: str):
    """Set X11 display configuration."""
    try:
        X11_DISPLAY_CONFIG_FILE.write_text(
            json.dumps({"display": display}, indent=2), encoding="utf-8"
        )
        return {"success": True, "display": display}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
