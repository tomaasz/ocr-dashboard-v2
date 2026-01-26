"""OCR Dashboard V2 - Routes Package"""

from .dashboard import router as dashboard_router
from .profiles import router as profiles_router
from .settings import router as settings_router

__all__ = [
    "dashboard_router",
    "profiles_router",
    "settings_router",
]
