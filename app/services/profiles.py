"""
OCR Dashboard V2 - Profile Service
Profile management business logic.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Optional

from ..config import CACHE_DIR


def list_profiles(include_default: bool = False) -> list[str]:
    """List available profiles from cache directory."""
    default_dir = CACHE_DIR / "gemini-profile"
    default_hidden_marker = CACHE_DIR / ".hide_default_profile"
    profiles: list[str] = []
    
    try:
        if include_default and default_dir.is_dir() and not default_hidden_marker.exists():
            profiles.append("default")
        
        if CACHE_DIR.exists():
            for d in CACHE_DIR.iterdir():
                if d.is_dir() and d.name.startswith("gemini-profile-"):
                    suffix = d.name.replace("gemini-profile-", "")
                    if suffix == "default" and default_hidden_marker.exists():
                        continue
                    profiles.append(suffix)
    except Exception:
        return []
    
    return sorted(set(p for p in profiles if p))


def get_profile_dir(profile_name: str) -> Path:
    """Get the directory path for a profile."""
    if profile_name == "default":
        return CACHE_DIR / "gemini-profile"
    return CACHE_DIR / f"gemini-profile-{profile_name}"


def profile_exists(profile_name: str) -> bool:
    """Check if profile directory exists."""
    return get_profile_dir(profile_name).is_dir()


def create_profile(name: str) -> tuple[bool, str]:
    """Create a new profile directory."""
    profile_dir = get_profile_dir(name)
    
    if profile_dir.exists():
        return False, f"Profil '{name}' już istnieje"
    
    try:
        profile_dir.mkdir(parents=True, exist_ok=True)
        return True, f"Utworzono profil '{name}'"
    except Exception as e:
        return False, f"Błąd tworzenia profilu: {e}"


def delete_profile(name: str) -> tuple[bool, str]:
    """Delete a profile directory."""
    if name == "default":
        return False, "Nie można usunąć domyślnego profilu"
    
    profile_dir = get_profile_dir(name)
    
    if not profile_dir.exists():
        return False, f"Profil '{name}' nie istnieje"
    
    try:
        shutil.rmtree(profile_dir)
        return True, f"Usunięto profil '{name}'"
    except Exception as e:
        return False, f"Błąd usuwania profilu: {e}"


def get_active_chrome_profile(profile_name: str) -> Optional[str]:
    """Get the active Chrome profile directory for a profile."""
    profile_dir = get_profile_dir(profile_name)
    active_file = profile_dir / ".active_chrome_profile"
    
    if active_file.exists():
        try:
            return active_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    
    # Fallback: find most recently used profile
    if profile_dir.exists():
        try:
            candidates = []
            for d in profile_dir.iterdir():
                if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile ")):
                    candidates.append(d)
            
            if candidates:
                def cookie_mtime(p: Path) -> float:
                    cookies = p / "Cookies"
                    try:
                        return cookies.stat().st_mtime
                    except Exception:
                        try:
                            return p.stat().st_mtime
                        except Exception:
                            return 0.0
                
                latest = max(candidates, key=cookie_mtime)
                return latest.name
        except Exception:
            pass
    
    return None


def clear_profile_cache(profile_dir: Path) -> None:
    """Clear browser cache from profile directory."""
    cache_patterns = [
        "Default/Cache",
        "Default/Code Cache",
        "Default/GPUCache",
        "Profile */Cache",
        "Profile */Code Cache",
        "Profile */GPUCache",
        "GrShaderCache",
        "ShaderCache",
    ]
    
    for pattern in cache_patterns:
        for match in profile_dir.glob(pattern):
            try:
                if match.is_dir():
                    shutil.rmtree(match)
                else:
                    match.unlink()
            except Exception:
                pass
