"""
OCR Dashboard V2 - Pydantic Request Models
Extracted from legacy app.py.
"""

from typing import List, Optional
from pydantic import BaseModel


class JobStartRequest(BaseModel):
    """Request model for starting OCR job."""
    source_path: str
    profiles: List[str]
    remote_browser_profiles: Optional[List[str]] = None
    remote_wsl_browser_profiles: Optional[List[str]] = None
    remote_desktop_browser_profiles: Optional[List[str]] = None
    remote_ssh_profiles: Optional[List[str]] = None
    remote_desktop_profiles: Optional[List[str]] = None
    remote_desktop_source_path: Optional[str] = None
    workers: int = 2
    scans_per_worker: int = 2
    batch_id: Optional[str] = None
    headed: bool = True
    continue_mode: bool = True
    pro_only: bool = True
    collect_timeout_sec: int = 400
    close_idle_tabs: bool = True
    max_tabs_per_context: int = 0
    use_isolated_contexts: bool = False
    context_pool_size: int = 0
    viewport_width: int = 1200
    viewport_height: int = 800
    reduced_motion: bool = True
    pg_enabled: bool = False
    pg_dsn: Optional[str] = None
    pg_table: str = "public.ocr_raw_texts"
    clean_temp_images: bool = True
    debug_artifacts: bool = False
    capture_video: bool = False
    tracing_mode: str = "off"
    auth_ensure_enabled: bool = True
    auth_ensure_interval_sec: int = 900
    model_switch_retries: int = 3
    model_switch_cooldown_ms: int = 1200
    limit_check_interval_sec: int = 1800
    pro_pause_buffer_sec: int = 180
    pro_fallback_pause_min: int = 60
    browser_id: Optional[str] = None
    # Preprocessing options
    preproc_max_dimension: int = 2500
    preproc_median_kernel: int = 3
    preproc_denoise_strength: int = 8
    preproc_clahe_clip_limit: float = 2.0
    preproc_clahe_grid_size: str = "8,8"
    preproc_morph_kernel_size: int = 2
    preproc_unsharp_amount: float = 1.2
    preproc_unsharp_radius: int = 1
    preproc_margin_percent: float = 0.05
    preproc_dark_threshold: int = 60
    preproc_margin_ink_ratio_max: float = 0.01
    preproc_margin_shadow_mean_max: int = 200
    preproc_background_kernel_ratio: float = 0.025
    preproc_background_kernel_min: int = 31
    preproc_local_contrast_sigma: float = 12.0
    preproc_local_contrast_amount: float = 0.35
    preproc_blackhat_kernel_size: int = 5
    preproc_blackhat_strength: float = 0.45
    preproc_enable_adaptive_binarization: bool = False
    preproc_sauvola_window: int = 31
    preproc_sauvola_k: float = 0.2
    preproc_sauvola_r: float = 128.0
    preproc_text_mask_block_size: int = 31
    preproc_text_mask_c: int = 12
    preproc_text_mask_open_kernel: int = 3
    preproc_text_mask_close_kernel: int = 9
    preproc_text_mask_close_iters: int = 2
    preproc_text_mask_dilate_iters: int = 1
    preproc_text_mask_min_area_ratio: float = 0.0005
    preproc_trim_band_ratio: float = 0.02
    preproc_trim_ink_ratio_max: float = 0.02
    preproc_trim_max_ratio: float = 0.15
    preproc_trim_min_dimension: int = 200
    engine: Optional[str] = None
    auto_restart: bool = False
    manual_start: bool = False


class CleanupRequest(BaseModel):
    """Request model for cleanup operation."""
    targets: List[str]
    force: bool = False


class ProfileCreateRequest(BaseModel):
    """Request model for creating a profile."""
    name: str


class ProfileLoginRequest(BaseModel):
    """Request model for profile login."""
    name: str


class PostProcessRequest(BaseModel):
    """Request model for post-processing worker."""
    dsn: str
    profile_suffix: str = ""
    api_key: Optional[str] = None
