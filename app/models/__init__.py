"""OCR Dashboard V2 - Models Package"""

from .requests import (
    JobStartRequest,
    CleanupRequest,
    ProfileCreateRequest,
    ProfileLoginRequest,
    PostProcessRequest,
)

__all__ = [
    "JobStartRequest",
    "CleanupRequest",
    "ProfileCreateRequest",
    "ProfileLoginRequest",
    "PostProcessRequest",
]
