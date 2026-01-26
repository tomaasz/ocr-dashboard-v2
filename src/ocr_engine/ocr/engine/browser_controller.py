"""
Browser controller module for Gemini Web OCR.

Handles Playwright browser operations: startup, navigation, upload, prompting,
model selection, and response collection.
"""

import base64
import logging
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Optional, Tuple

from playwright.sync_api import (
    sync_playwright,
    Page,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from .pro_limit_handler import PRO_LIMIT_TEXT_RE
from .ui_health_checker import UIHealthChecker
from .session_recovery import SessionRecovery, SessionIssueType
from .auto_login import AutoLogin

logger = logging.getLogger(__name__)

# Regex for upload menu items
_MENU_ITEM_RE = re.compile(r"(prześlij|upload|wybierz|select|obraz|image|plik|file)", re.IGNORECASE)

# Regex for model detection
_MODEL_BUTTON_RE = re.compile(r"(Szybki|Fast|Flash|Pro|1\.5\s*Pro|2\.0\s*Pro|Thinking|Myślący)", re.IGNORECASE)
_PRO_MODEL_RE = re.compile(r"(?:\bPro\b|1\.5\s*Pro|2\.0\s*Pro)", re.IGNORECASE)
_FAST_MODEL_RE = re.compile(r"(Szybki|Fast|Flash|1\.5 Flash|2\.0 Flash)", re.IGNORECASE)


class SessionExpiredError(Exception):
    """Raised when Google session expires and login is required."""
    pass


class GeminiBrowserController:
    """Controls Playwright browser for Gemini Web OCR operations."""
    
    def __init__(
        self,
        profile_dir: Path,
        headed: bool = False,
        locale: str = "pl-PL",
        enable_video: bool = True,
        video_dir: Optional[Path] = None,
        proxy_config: Optional[dict] = None,
        enable_tracing: bool = True,
        db_manager: Optional[Any] = None,
    ):
        self.profile_dir = profile_dir
        self.headed = headed
        self.locale = locale
        self.enable_video = enable_video
        self.video_dir = video_dir
        self.proxy_config = proxy_config
        self.enable_tracing = enable_tracing
        self.tracing_active = False
        self.debug_artifacts_enabled = os.environ.get("OCR_DEBUG_ARTIFACTS", "false").strip().lower() == "true"
        self.capture_video = (
            self.enable_video
            and os.environ.get("OCR_CAPTURE_VIDEO", "false").strip().lower() == "true"
        )
        self.tracing_mode = os.environ.get("OCR_TRACING_MODE", "off").strip().lower()
        if self.tracing_mode not in {"off", "continuous", "on_failure"} or not self.enable_tracing:
            self.tracing_mode = "off"
        
        # Remote execution config (defaults to False for local)
        self.remote_enabled = False
        self.remote_host = None
        self.remote_user = None
        self.remote_ssh_opts = "-o StrictHostKeyChecking=no"
        self.remote_port_base = 9222
        self.remote_local_port_base = 9222
        self.remote_port_span = 100
        self.remote_profile_root = None
        self.remote_tunnel_enabled = True
        self.remote_chrome_bin = None
        self.remote_python = "python3"
        self.remote_pid = None
        self.remote_runner = os.environ.get("OCR_REMOTE_BROWSER_RUNNER", "wsl").strip().lower()
        self.remote_desktop_host = os.environ.get("OCR_REMOTE_DESKTOP_HOST")
        self.remote_desktop_user = os.environ.get("OCR_REMOTE_DESKTOP_USER")
        
        # Security: Sanitize WSL distro name
        distro_raw = os.environ.get("OCR_REMOTE_BROWSER_WSL_DISTRO", "").strip()
        self.remote_wsl_distro = re.sub(r"[^a-zA-Z0-9_\-\.]", "", distro_raw)
        
        self.ssh_tunnel_proc: Optional[subprocess.Popen] = None
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        
        # Browser Context isolation (feature flag)
        self.use_isolated_contexts = os.environ.get("OCR_USE_ISOLATED_CONTEXTS", "false").strip().lower() == "true"
        self.worker_contexts: dict[int, BrowserContext] = {}  # worker_id -> context
        try:
            self.context_pool_size = int(os.environ.get("OCR_CONTEXT_POOL_SIZE", "0").strip())
        except Exception:
            self.context_pool_size = 0
        self.context_pool_size = max(0, self.context_pool_size)
        self.context_pool: list[BrowserContext] = []
        self.context_pool_index = 0
        self.context_refcounts: dict[BrowserContext, int] = {}
        try:
            self.viewport_width = int(os.environ.get("OCR_VIEWPORT_WIDTH", "1400").strip())
        except Exception:
            self.viewport_width = 1400
        try:
            self.viewport_height = int(os.environ.get("OCR_VIEWPORT_HEIGHT", "900").strip())
        except Exception:
            self.viewport_height = 900
        self.viewport_width = max(800, self.viewport_width)
        self.viewport_height = max(600, self.viewport_height)
        self.reduced_motion = os.environ.get("OCR_REDUCED_MOTION", "0").strip().lower() in ("1", "true", "yes")
        try:
            self.model_switch_retries = int(os.environ.get("OCR_MODEL_SWITCH_RETRIES", "3").strip())
        except Exception:
            self.model_switch_retries = 3
        try:
            self.model_switch_cooldown_ms = int(os.environ.get("OCR_MODEL_SWITCH_COOLDOWN_MS", "1200").strip())
        except Exception:
            self.model_switch_cooldown_ms = 1200
        self.model_switch_retries = max(1, self.model_switch_retries)
        self.model_switch_cooldown_ms = max(200, self.model_switch_cooldown_ms)
        
        # UI health monitoring
        self.ui_health_checker = UIHealthChecker()
        
        # Session recovery
        self.session_recovery = SessionRecovery()
        
        # Database manager for critical events
        self.db_manager = db_manager
        self.profile_name = profile_dir.name  # Extract profile name from path
        
        # Auto-login handler
        self.auto_login = AutoLogin(self.profile_name, db_manager=db_manager)
        self.auto_login_enabled = os.environ.get("OCR_AUTO_LOGIN", "true").strip().lower() in ("1", "true", "yes")
        
    def start(self) -> BrowserContext:
        """Start browser with persistent profile."""
        logger.info(f"[Browser] Starting Playwright. Profile: {self.profile_dir}")
        logger.info(f"[Browser] Isolated contexts mode: {self.use_isolated_contexts}")
        if self.use_isolated_contexts and self.context_pool_size > 0:
            logger.info(f"[Browser] Context pool size: {self.context_pool_size}")
        self.playwright = sync_playwright().start()

        if self.remote_enabled:
            return self._start_remote_context()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--enable-features=NetworkService,NetworkServiceInProcess",
        ]
        
        if self.use_isolated_contexts:
            # NEW MODE: Launch browser, create contexts manually
            logger.info("[Browser] Using isolated contexts mode (launch + manual contexts)")
            
            self.browser = self.playwright.chromium.launch(
                headless=not self.headed,
                args=args + [f"--user-data-dir={self.profile_dir}"],
            )
            
            # Create a default shared context for backward compatibility
            # (some code might still expect self.context to exist)
            record_video_dir = None
            if self.capture_video and self.video_dir:
                record_video_dir = str(self.video_dir / "shared")
                Path(record_video_dir).mkdir(parents=True, exist_ok=True)
            
            self.context = self.browser.new_context(
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                locale=self.locale,
                record_video_dir=record_video_dir,
                record_video_size={"width": self.viewport_width, "height": self.viewport_height} if record_video_dir else None,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                proxy=self.proxy_config,
                reduced_motion="reduce" if self.reduced_motion else "no-preference",
            )
            
            # Start tracing for shared context
            if self.tracing_mode == "continuous":
                try:
                    self.context.tracing.start(
                        screenshots=True,
                        snapshots=True,
                        sources=True
                    )
                    self.tracing_active = True
                    logger.info("[Tracing] Started tracing for shared context")
                except Exception as e:
                    logger.warning(f"[Tracing] Failed to start tracing: {e}")
                    self.tracing_active = False
        else:
            # LEGACY MODE: launch_persistent_context (single shared context)
            logger.info("[Browser] Using legacy mode (launch_persistent_context)")
            
            record_video_dir = None
            if self.capture_video and self.video_dir:
                record_video_dir = self.video_dir

            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=not self.headed,
                args=args,
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                locale=self.locale,
                record_video_dir=record_video_dir,
                record_video_size={"width": self.viewport_width, "height": self.viewport_height} if record_video_dir else None,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                proxy=self.proxy_config,
                reduced_motion="reduce" if self.reduced_motion else "no-preference",
            )
            
            # Start tracing for error diagnosis (retain-on-failure strategy)
            if self.tracing_mode == "continuous":
                try:
                    self.context.tracing.start(
                        screenshots=True,
                        snapshots=True,
                        sources=True
                    )
                    self.tracing_active = True
                    logger.info("[Tracing] Started continuous tracing (retain-on-failure)")
                except Exception as e:
                    logger.warning(f"[Tracing] Failed to start tracing: {e}")
                    self.tracing_active = False
        
        # Clean up old tabs from previous sessions and ensure fresh start
        self._ensure_clean_start()
        
        return self.context

    def _start_remote_context(self) -> BrowserContext:
        logger.info(f"[Browser] Remote mode enabled. Host: {self.remote_host}")
        port = self._remote_port()
        self.remote_pid = self._ensure_remote_chrome(port)
        local_port = self._remote_local_port()
        if self.remote_tunnel_enabled:
            tunnel_ok = self._ensure_ssh_tunnel(port, local_port)
            if tunnel_ok:
                self.remote_cdp_url = f"http://127.0.0.1:{local_port}"
            else:
                logger.warning("[Browser] SSH tunnel unavailable; falling back to direct remote host.")
                self.remote_cdp_url = f"http://{self.remote_host}:{port}"
        else:
            self.remote_cdp_url = f"http://{self.remote_host}:{port}"

        browser = None
        for attempt in range(6):
            try:
                browser = self.playwright.chromium.connect_over_cdp(self.remote_cdp_url)
                break
            except Exception as e:
                logger.warning(f"[Browser] Remote CDP connect retry {attempt + 1}/6 failed: {e}")
                time.sleep(1)
        if not browser:
            raise RuntimeError("Failed to connect to remote Chromium over CDP.")
        self.browser = browser

        if browser.contexts:
            self.context = browser.contexts[0]
        else:
            self.context = browser.new_context(
                viewport={"width": 1400, "height": 900},
                locale=self.locale,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

        self._ensure_clean_start()
        return self.context

    def create_worker_context(self, worker_id: int) -> BrowserContext:
        """
        Create isolated browser context for a specific worker.
        
        Each worker gets its own context with isolated cookies, storage, and cache.
        This improves stability and allows per-worker recovery without affecting others.
        
        Args:
            worker_id: Unique identifier for the worker
            
        Returns:
            BrowserContext: Isolated context for this worker
        """
        if not self.use_isolated_contexts:
            # Feature disabled - return shared context
            if not self.context:
                raise RuntimeError("Shared context not initialized. Call start() first.")
            return self.context
        
        if worker_id in self.worker_contexts:
            logger.warning(f"[Context] Worker {worker_id} context already exists, reusing")
            return self.worker_contexts[worker_id]
        
        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first when using isolated contexts.")
        
        context = None
        pooled = self.context_pool_size > 0
        if pooled:
            if len(self.context_pool) < self.context_pool_size:
                context = self._create_isolated_context(worker_id=worker_id)
                self.context_pool.append(context)
                self.context_refcounts[context] = 0
                logger.info(f"[Context] Created pooled context {len(self.context_pool)}/{self.context_pool_size}")
            else:
                context = self.context_pool[self.context_pool_index % len(self.context_pool)]
                self.context_pool_index += 1
                logger.info(f"[Context] Reusing pooled context for worker {worker_id}")
            self.context_refcounts[context] = self.context_refcounts.get(context, 0) + 1
        else:
            context = self._create_isolated_context(worker_id=worker_id)
            self.context_refcounts[context] = 1
        
        self.worker_contexts[worker_id] = context
        logger.info(f"[Context] Created isolated context for worker {worker_id}")
        return context

    def _create_isolated_context(self, worker_id: int) -> BrowserContext:
        """Create a new isolated context with optional video/tracing."""
        # Build context configuration
        context_config = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "locale": self.locale,
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "reduced_motion": "reduce" if self.reduced_motion else "no-preference",
        }

        if self.proxy_config:
            context_config["proxy"] = self.proxy_config

        # Per-worker video recording (optional)
        if self.capture_video and self.video_dir:
            worker_video_dir = self.video_dir / f"worker_{worker_id}"
            worker_video_dir.mkdir(parents=True, exist_ok=True)
            context_config["record_video_dir"] = str(worker_video_dir)
            context_config["record_video_size"] = {"width": self.viewport_width, "height": self.viewport_height}

        context = self.browser.new_context(**context_config)

        # Start tracing for this context (optional)
        if self.tracing_mode == "continuous":
            try:
                context.tracing.start(
                    screenshots=True,
                    snapshots=True,
                    sources=True
                )
                logger.info(f"[Context] Started tracing for worker {worker_id}")
            except Exception as e:
                logger.warning(f"[Context] Failed to start tracing for worker {worker_id}: {e}")

        return context
    
    def close_worker_context(self, worker_id: int, save_trace: bool = False):
        """
        Close isolated context for a specific worker.
        
        Args:
            worker_id: Worker identifier
            save_trace: If True, save tracing data before closing
        """
        if not self.use_isolated_contexts:
            # Feature disabled - don't close shared context
            return
        
        if worker_id not in self.worker_contexts:
            logger.debug(f"[Context] Worker {worker_id} context not found, nothing to close")
            return
        
        context = self.worker_contexts[worker_id]
        pooled = self.context_pool_size > 0 and context in self.context_pool
        
        try:
            # Save tracing if requested
            if save_trace and self.enable_tracing and self.tracing_mode != "off":
                try:
                    trace_path = self.video_dir / f"worker_{worker_id}_trace.zip" if self.video_dir else None
                    if trace_path:
                        trace_path.parent.mkdir(parents=True, exist_ok=True)
                        context.tracing.stop(path=str(trace_path))
                        logger.info(f"[Context] Saved trace for worker {worker_id} to {trace_path}")
                except Exception as e:
                    logger.warning(f"[Context] Failed to save trace for worker {worker_id}: {e}")

            if not pooled:
                context.close()
                logger.info(f"[Context] Closed context for worker {worker_id}")
        except Exception as e:
            logger.warning(f"[Context] Error closing context for worker {worker_id}: {e}")
        finally:
            if pooled:
                try:
                    self.context_refcounts[context] = max(0, self.context_refcounts.get(context, 1) - 1)
                except Exception:
                    pass
            del self.worker_contexts[worker_id]

    def _remote_port(self) -> int:
        key = self.profile_dir.name
        h = sum(ord(c) for c in key) % self.remote_port_span
        return self.remote_port_base + h

    def _remote_local_port(self) -> int:
        key = self.profile_dir.name
        h = sum(ord(c) for c in key) % self.remote_port_span
        return self.remote_local_port_base + h

    def _ensure_ssh_tunnel(self, remote_port: int, local_port: int) -> bool:
        """Establish SSH tunnel for CDP connection."""
        # 1. Kill any existing process on this local port
        try:
            logger.info(f"[Browser] Cleaning up port {local_port}...")
            subprocess.run(
                ["fuser", "-k", "-n", "tcp", str(local_port)],
                capture_output=True,
                check=False
            )
            time.sleep(0.5)
        except Exception:
            pass
            
        dest = f"{self.remote_user}@{self.remote_host}" if self.remote_user else self.remote_host
        # -N: Do not execute a remote command.
        # -L: Forward port
        # We REMOVE -f to keep the process controllable via Popen
        ssh_cmd = [
            "ssh",
            *shlex.split(self.remote_ssh_opts),
            "-N",
            "-o", "ExitOnForwardFailure=yes",
            "-L", f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
            dest,
        ]
        
        try:
            logger.info(f"[Browser] Starting SSH tunnel: {' '.join(ssh_cmd)}")
            self.ssh_tunnel_proc = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to see if it dies immediately
            time.sleep(1.0)
            if self.ssh_tunnel_proc.poll() is not None:
                _, stderr = self.ssh_tunnel_proc.communicate()
                logger.warning(f"[Browser] SSH tunnel failed to start: {stderr}")
                self.ssh_tunnel_proc = None
                return False
                
            logger.info(f"[Browser] SSH tunnel established (pid={self.ssh_tunnel_proc.pid})")
            return True
            
        except Exception as e:
            logger.warning(f"[Browser] SSH tunnel error: {e}")
            self.ssh_tunnel_proc = None
            return False

    def _ssh_run(self, command: str, timeout: int = 12) -> subprocess.CompletedProcess:
        """
        Run command over SSH using Base64 wrapping to robustly handle special characters 
        and quoting issues across different remote shells (CMD/PowerShell/Bash-on-Linux).
        """
        dest = f"{self.remote_user}@{self.remote_host}" if self.remote_user else self.remote_host
        
        # Base64 encode the command to avoid quoting hell
        b64_cmd = base64.b64encode(command.encode("utf-8")).decode("ascii")
        
        if self.remote_runner == "desktop":
            # WINDOWS/CMD HOST -> WSL
            # CMD only supports double quotes. Single quotes are literals.
            # We want to run: wsl.exe -- bash -lc "echo <B64> | base64 -d | bash"
            # Since B64 is alphanumeric, we can safely embed it.
            # We wrap the inner bash command in double quotes for CMD compatibility.
            
            wsl_prefix = f"wsl.exe -d {self.remote_wsl_distro}" if self.remote_wsl_distro else "wsl.exe"
            
            # The command bash will execute:
            inner_bash_cmd = f"echo {b64_cmd} | base64 -d | bash"
            
            # The CMD command to invoke WSL:
            # We use double quotes around the bash command.
            # CAUTION: If there are internal double quotes they need escaping, but simple echo|base64|bash 
            # uses no quotes.
            remote_cmd = f'{wsl_prefix} -- bash -lc "{inner_bash_cmd}"'
            
            ssh_cmd = ["ssh"] + shlex.split(self.remote_ssh_opts) + [dest, remote_cmd]
            
        else:
            # LINUX HOST (or proper Bash environment)
            # Combine bash -lc with command as single argument for SSH
            # SSH passes all args after destination to remote shell, so we need them as one string
            wrapped_cmd = f"echo {b64_cmd} | base64 -d | bash"
            full_bash_cmd = f"bash -lc '{wrapped_cmd}'"
            ssh_cmd = ["ssh"] + shlex.split(self.remote_ssh_opts) + [dest, full_bash_cmd]
            
        # Run with text=False to capture bytes, preventing UnicodeDecodeError
        result = subprocess.run(ssh_cmd, capture_output=True, text=False, timeout=timeout)
        
        # Manually decode with replacement for safety
        stdout_str = result.stdout.decode("utf-8", errors="replace")
        stderr_str = result.stderr.decode("utf-8", errors="replace")
        
        result.stdout = stdout_str
        result.stderr = stderr_str
        return result

    def _resolve_remote_chrome_bin(self) -> str:
        if self.remote_chrome_bin:
            return self.remote_chrome_bin
            
        # script provided as plain text now, _ssh_run will base64 encode it
        script = """
import sys
print("DEBUG_start_chrome_resolve");
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print(p.chromium.executable_path)
except Exception as e:
    print("ERROR: " + str(e))
print("DEBUG_end_chrome_resolve");
"""
        
        # Use simpler invocation since _ssh_run handles the heavy lifting
        cmd = f"{shlex.quote(self.remote_python)} -u -c {shlex.quote(script)}"
        
        logger.info(f"[Browser] Resolving remote chrome via {self.remote_python}...")
        result = self._ssh_run(cmd, timeout=15)
        
        output = result.stdout.strip()
        lines = output.splitlines()
        
        # Filter out debug lines and empty lines
        valid_lines = [line.strip() for line in lines if line.strip() and not line.startswith("DEBUG_")]
        path = valid_lines[-1] if valid_lines else ""
        
        if result.returncode != 0 or not path:
            # Enhanced error logging
            logger.error(f"[Browser] Remote Resolve Code: {result.returncode}")
            logger.error(f"[Browser] Remote Resolve Stdout: {repr(result.stdout)}")
            logger.error(f"[Browser] Remote Resolve Stderr: {repr(result.stderr)}")
            
            if result.returncode != 0:
                 raise RuntimeError(f"Remote chromium path resolve failed: {result.stderr.strip() or output}")
        
        if not path or "Traceback" in path or "Error" in path:
             # Fallback for Windows/WSL if output is messy
             match = re.search(r"(/.*chrome.*|c:\\.*chrome\.exe)", output, re.IGNORECASE)
             if match:
                 path = match.group(1)
             else:
                 raise RuntimeError(f"Remote chromium path resolve failed. Output: {output}")
        
        return path

    def _ensure_remote_chrome(self, port: int) -> Optional[int]:
        chrome_bin = self._resolve_remote_chrome_bin()
        profile_name = self.profile_dir.name
        remote_root = self.remote_profile_root or (f"/home/{self.remote_user}/.cache/ocr-dashboard-v2" if self.remote_user else "")
        if isinstance(remote_root, str):
            remote_root = remote_root.strip()
        if not remote_root:
            remote_root = "$HOME/.cache/ocr-dashboard-v2"
        profile_dir = f"{remote_root}/{profile_name}"
        pid_dir = f"{remote_root}/remote_pids"
        pid_file = f"{pid_dir}/chrome_{profile_name}.pid"
        logger.info(f"[Browser] Remote dirs: root={remote_root} profile={profile_dir} pid_dir={pid_dir}")
        headless_flag = "" if self.headed else "--headless=new"
        chrome_cmd = (
            f"{shlex.quote(chrome_bin)} "
            f"--remote-debugging-address=0.0.0.0 "
            f"--remote-debugging-port={port} "
            f"--user-data-dir={shlex.quote(profile_dir)} "
            f"--no-first-run --no-default-browser-check --disable-features=Translate "
            f"--disable-translate --disable-session-crashed-bubble --restore-last-session "
            f"--disable-dev-shm-usage --no-sandbox {headless_flag}"
        )
        pid_dir_q = shlex.quote(pid_dir)
        profile_dir_q = shlex.quote(profile_dir)
        pid_file_q = shlex.quote(pid_file)
        remote_cmd = (
            f"mkdir -p {pid_dir_q} {profile_dir_q}; "
            f"rm -f {profile_dir_q}/SingletonLock {profile_dir_q}/SingletonCookie {profile_dir_q}/SingletonSocket; "
            f"if [ -f {pid_file_q} ]; then "
            f"  pid=$(cat {pid_file_q} 2>/dev/null); "
            f"  if [ -n \"$pid\" ] && kill -0 \"$pid\" 2>/dev/null; then "
            f"    echo \"$pid\"; exit 0; "
            f"  fi; "
            f"fi; "
            f"nohup {chrome_cmd} > /tmp/ocr_remote_chrome_{profile_name}.log 2>&1 & "
            f"echo $! > {pid_file_q}; "
            f"cat {pid_file_q}"
        )
        logger.info(f"[Browser] Remote cmd: {remote_cmd}")
        result = self._ssh_run(remote_cmd, timeout=12)
        if result.returncode != 0:
            # Check if failure might be due to connection issues requiring wakeup
            is_connection_error = (
                "Connection refused" in result.stderr or 
                "Network is unreachable" in result.stderr or
                "timed out" in result.stderr or
                result.returncode == 255
            )
            
            if is_connection_error and self.remote_desktop_host and self.remote_runner == "wsl":
                logger.warning(f"[Browser] Remote connection failed. Attempting wakeup via {self.remote_desktop_host}...")
                self._wake_remote_desktop()
                
                # Retry the remote command
                logger.info("[Browser] Retrying remote Chrome start after wakeup...")
                result = self._ssh_run(remote_cmd, timeout=12)
                
            if result.returncode != 0:
                raise RuntimeError(f"Remote Chrome start failed: {result.stderr.strip()}")
        try:
            return int(result.stdout.strip().splitlines()[-1])
        except Exception:
            return None

    def _wake_remote_desktop(self) -> None:
        """
        Attempt to wake up the remote WSL instance via the Windows host.
        Executes 'wsl -- sudo service ssh start' on the Windows host via SSH.
        """
        if not self.remote_desktop_host:
            return

        logger.info(f"[Browser] ⏰ Waking up remote WSL via Desktop host: {self.remote_desktop_host}...")
        
        # We need to run this command on the Windows host to start SSH in WSL
        # Command: wsl -d Ubuntu -- sudo service ssh start
        # Note: This assumes passwordless sudo or configured sudoers for 'service ssh start'
        wsl_distro = self.remote_wsl_distro or "Ubuntu"
        remote_cmd = f"wsl -d {wsl_distro} -- sudo service ssh start"
        
        dest = f"{self.remote_desktop_user}@{self.remote_desktop_host}" if self.remote_desktop_user else self.remote_desktop_host
        
        # Simple SSH run strictly for wakeup - using existing SSH opts
        ssh_cmd = ["ssh"] + shlex.split(self.remote_ssh_opts) + [dest, remote_cmd]
        
        try:
            result = subprocess.run(
                ssh_cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("[Browser] ✅ Wakeup command executed successfully.")
                time.sleep(2) # Give it a moment to start
            else:
                logger.warning(f"[Browser] ⚠️ Wakeup command failed (code {result.returncode}): {result.stderr.strip()}")
                
        except Exception as e:
            logger.warning(f"[Browser] ⚠️ Wakeup attempt failed with exception: {e}")
    
    def _ensure_clean_start(self):
        """
        Close extra tabs, ensuring exactly TWO tabs are open.
        First tab is navigated to Gemini. Second tab is reset to about:blank for a clean start.
        Critical: Prevents accumulation of limit popups and stale UI states.
        """
        try:
            # Ensure at least 2 pages exist
            while len(self.context.pages) < 2:
                self.context.new_page()
            
            all_pages = self.context.pages
            logger.info(f"[Browser] Found {len(all_pages)} tabs. Ensuring exactly 2...")
            
            # Close all except the first TWO
            for page in all_pages[2:]:
                try:
                    page.close()
                except Exception:
                    pass
            
            # Refresh list after closing
            all_pages = self.context.pages
            
            # Navigate first tab to fresh Gemini home
            if len(all_pages) > 0:
                first_page = all_pages[0]
                logger.info("[Browser] Navigating first tab to fresh Gemini home...")
                first_page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=15000)
                
                # Wait for page to fully render
                time.sleep(1)
                
                # Close popups multiple times (some appear delayed)
                for attempt in range(3):
                    self.close_popups(first_page)
                    time.sleep(1)
                
                if self.debug_artifacts_enabled:
                    # Take debug screenshot to see what state we're in
                    try:
                        debug_path = Path("artifacts/screenshots/clean_start_debug.png")
                        debug_path.parent.mkdir(parents=True, exist_ok=True)
                        first_page.screenshot(path=str(debug_path), full_page=True)
                        logger.info(f"[Browser] Debug screenshot saved: {debug_path}")
                    except Exception:
                        pass
                
                # Check if we're logged out
                if self._is_logged_out(first_page):
                    logger.warning("⚠️ [Browser] SESSION EXPIRED during clean start!")
                    
                    # Try auto-login if enabled and credentials available
                    if self.auto_login_enabled and self.auto_login.can_auto_login():
                        logger.info("[Browser] Attempting auto-login...")
                        if self.auto_login.perform_login(first_page):
                            logger.info("✅ [Browser] Auto-login successful!")
                            # Close popups after login
                            for _ in range(3):
                                self.close_popups(first_page)
                                time.sleep(1)
                        else:
                            logger.critical("❌ [Browser] Auto-login FAILED!")
                            raise SessionExpiredError("Auto-login failed. Check credentials in config/credentials.json")
                    else:
                        logger.critical("❌ [Browser] No auto-login credentials. Run headed mode to relogin.")
                        raise SessionExpiredError("Google session expired. Run headed mode to relogin or configure auto-login.")

            # Ensure second tab is clean
            if len(all_pages) > 1:
                 try:
                     logger.info("[Browser] Resetting second tab to about:blank...")
                     all_pages[1].goto("about:blank")
                 except Exception:
                     pass
            
            logger.info("✅ [Browser] Clean start completed - ready for workers.")
        except SessionExpiredError:
            raise
        except Exception as e:
            logger.warning(f"[Browser] Clean start failed (non-critical): {e}")
    
    def try_auto_login(self, page: Page) -> bool:
        """
        Try to perform auto-login on the given page.
        
        Returns True if login successful, False otherwise.
        """
        if not self.auto_login_enabled:
            logger.debug("[Browser] Auto-login disabled")
            return False
        
        if not self.auto_login.can_auto_login():
            logger.debug("[Browser] Auto-login not available (missing credentials)")
            return False
        
        return self.auto_login.perform_login(page)
    
    def close(self):
        """Close browser and stop Playwright."""
        # Close all worker contexts first (if using isolated contexts)
        if self.use_isolated_contexts and self.worker_contexts:
            logger.info(f"[Browser] Closing {len(self.worker_contexts)} worker contexts...")
            for worker_id in list(self.worker_contexts.keys()):
                self.close_worker_context(worker_id, save_trace=False)
        
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        
        # Kill remote chrome process
        if self.remote_enabled and self.remote_pid:
            try:
                profile_name = self.profile_dir.name
                pid_dir = f"{self.remote_profile_root}/remote_pids"
                pid_file = f"{pid_dir}/chrome_{profile_name}.pid"
                # Use standard kill first
                self._ssh_run(f"kill -TERM {self.remote_pid} >/dev/null 2>&1; rm -f {pid_file}", timeout=8)
            except Exception:
                pass
                
        # Kill local SSH tunnel
        if self.ssh_tunnel_proc:
            try:
                logger.info(f"[Browser] Terminating SSH tunnel (pid={self.ssh_tunnel_proc.pid})...")
                self.ssh_tunnel_proc.terminate()
                try:
                    self.ssh_tunnel_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.ssh_tunnel_proc.kill()
            except Exception:
                pass
            self.ssh_tunnel_proc = None

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
    
    def wait_for_ui_ready(self, page: Page):
        """Wait for Gemini UI to be ready with auto-healing."""
        try:
            expect(page.locator("div[contenteditable='true']").first).to_be_visible(timeout=40_000)
        except Exception as e:
            logger.warning(f"[Browser] UI not ready (timeout). Trying RELOAD... {e}")
            
            if self.debug_artifacts_enabled:
                # Debug screenshot before reload
                try:
                    path = Path(f"artifacts/screenshots/retry_ui_{int(time.time())}.png")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(path), full_page=True)
                except Exception:
                    pass

            try:
                # Check if page is still valid before reload
                if page.is_closed():
                    logger.error("[Browser] Page already closed, cannot reload")
                    raise RuntimeError("Page closed before reload attempt")
                
                page.reload(wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)
                # Try finding it again
                expect(page.locator("div[contenteditable='true']").first).to_be_visible(timeout=60_000)
                logger.info("[Browser] UI recovered after reload!")
            except Exception as e2:
                # If still failing, check if we are LOGGED OUT
                if self._is_logged_out(page):
                    logger.critical("❌ [Browser] SESSION EXPIRED! Login required. Please run headed mode to relogin.")
                    if self.debug_artifacts_enabled:
                        # Save specific screenshot
                        try:
                            path = Path(f"artifacts/screenshots/LOGIN_REQUIRED_{int(time.time())}.png")
                            path.parent.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(path), full_page=True)
                        except Exception:
                            pass
                    raise SessionExpiredError("Google session expired. Run headed mode to relogin.")

                # Run UI health check for detailed diagnostics
                logger.error(f"[Browser] UI wait failed PERMANENTLY: {e2}")
                logger.info("[Browser] Running UI health check for diagnostics...")
                
                ui_healthy = self.ui_health_checker.check_and_report(
                    page,
                    context="after_reload_failure",
                    save_screenshot=True
                )
                
                if not ui_healthy:
                    logger.error("[Browser] UI health check indicates layout changes or missing elements.")
                    logger.error("[Browser] This may require updating selectors in browser_controller.py")
                    
                    # Log critical event for UI changes
                    if self.db_manager and hasattr(self.db_manager, 'log_critical_event'):
                        try:
                            self.db_manager.log_critical_event(
                                profile_name=self.profile_name,
                                event_type="ui_change_detected",
                                message="Google UI layout may have changed. Check logs and update selectors.",
                                requires_action=True,
                                meta={"context": "after_reload_failure"},
                            )
                        except Exception:
                            pass
                
                raise e2

    def ensure_session(self, page: Page, context: str = "") -> bool:
        """Validate session/UI and attempt a light recovery when needed."""
        try:
            self.close_popups(page)

            if self._is_logged_out(page):
                raise SessionExpiredError("Session expired during ensure.")

            healthy = self.ui_health_checker.check_and_report(
                page,
                context=f"auth_ensure_{context}" if context else "auth_ensure",
                save_screenshot=self.debug_artifacts_enabled,
            )
            if healthy:
                return True

            try:
                page.reload(wait_until="domcontentloaded")
                time.sleep(1)
                self.close_popups(page)
            except Exception:
                pass

            if self._is_logged_out(page):
                raise SessionExpiredError("Session expired after reload.")

            healthy = self.ui_health_checker.check_and_report(
                page,
                context=f"auth_ensure_reload_{context}" if context else "auth_ensure_reload",
                save_screenshot=self.debug_artifacts_enabled,
            )
            return healthy
        except SessionExpiredError:
            raise
        except Exception as e:
            logger.warning(f"[AuthEnsure] Failed to validate session: {e}")
            return False
    
    def _is_logged_out(self, page: Page) -> bool:
        """Check if page shows login screen or other session issues."""
        # Use session recovery for comprehensive detection
        issue_type = self.session_recovery.detect_issue(page)
        
        if issue_type:
            logger.warning(f"[Browser] Session issue detected: {issue_type}")
            
            # Log diagnostic info
            diagnostics = self.session_recovery.get_diagnostic_info(page, issue_type)
            for key, value in diagnostics.items():
                logger.info(f"  {key}: {value}")
            
            # Log to database if available
            if self.db_manager and hasattr(self.db_manager, 'log_critical_event'):
                try:
                    self.db_manager.log_critical_event(
                        profile_name=self.profile_name,
                        event_type=issue_type,
                        message=self.session_recovery.get_recovery_suggestion(issue_type),
                        requires_action=self.session_recovery.is_critical(issue_type),
                        meta=diagnostics,
                    )
                except Exception as e:
                    logger.warning(f"[Browser] Failed to log critical event: {e}")
            
            # Return True for any critical session issue
            return self.session_recovery.is_critical(issue_type)
        
        return False
    
    def wait_for_composer_ready(self, page: Page) -> None:
        """Wait for composer to be ready and click it."""
        box = page.locator("div[contenteditable='true']").first
        expect(box).to_be_visible(timeout=40_000)
        try:
            box.click(force=True, timeout=2000)
        except Exception:
            pass
    
    def clear_composer(self, page: Page) -> None:
        """Clear any existing text in composer."""
        try:
            box = page.locator("div[contenteditable='true']").first
            if box.is_visible():
                box.click(force=True)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
        except Exception:
            pass
    
    def clear_attachments(self, page: Page):
        """Remove all attached images."""
        try:
            while True:
                btn = page.locator("button[aria-label*='Usuń' i], button[aria-label*='Remove' i]").first
                if btn.count() == 0 or not btn.is_visible():
                    break
                btn.click(force=True)
                page.wait_for_timeout(150)
        except Exception:
            pass
    
    def close_popups(self, page: Page):
        """Close any visible popups/dialogs with extended coverage."""
        try:
            # Handle Google consent page - scroll to reveal buttons if needed
            if "consent.google.com" in page.url:
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(300)
                except Exception:
                    pass
            
            targets = [
                # Original selectors
                "button[aria-label*='Close']",
                "button[aria-label*='Zamknij']",
                "button:has-text('No thanks')",
                "button:has-text('Got it')",
                "button:has-text('Rozumiem')",
                "button:has-text('Zgadzam się')",
                "button:has-text('Zamknij')",
                "button:has-text('Use Gemini')",
                "button:has-text('Accept all')",
                "button:has-text('Zaakceptuj wszystko')",
                
                # Consent & Continue popups
                "button:has-text('Kontynuuj')",
                "button:has-text('Continue')",
                "button:has-text('Nie teraz')",
                "button:has-text('Not now')",
                "button:has-text('Maybe later')",
                "button:has-text('Later')",
                
                # Skip & Dismiss
                "button:has-text('Skip')",
                "button:has-text('Pomiń')",
                "[aria-label*='dismiss']",
                "[aria-label*='Dismiss']",
                
                # Gemini welcome screen ("Witamy w Gemini" / "Welcome to Gemini")
                "button:has-text('Otwórz Gemini')",
                "button:has-text('Get started')",
                "button:has-text('Start')",
                "button:has-text('Open Gemini')",
                "button:has-text('Try Gemini')",
                "button:has-text('Wypróbuj Gemini')",
                
                # Permission popups
                "button:has-text('Block')",
                "button:has-text('Zablokuj')",
                
                # Google-specific dismiss buttons (jsname attributes)
                "button[jsname='V67aGc']",  # Common Google dismiss
                "button[jsname='b3VHJd']",  # Feedback dismiss
            ]
            
            for sel in targets:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=100):
                        logger.info(f"[Popup] Clicking: {sel}")
                        btn.click(timeout=1000)
                        page.wait_for_timeout(300)
                except Exception:
                    # Individual selector failure shouldn't stop others
                    continue
        except Exception as e:
            logger.debug(f"[Popup] Close attempt failed: {e}")
    
    def new_chat(self, page: Page):
        """Start a new chat session."""
        logger.info("[Chat] New CHAT (Ctrl+Shift+O)")
        try:
            page.keyboard.press("Control+Shift+O")
        except Exception:
            page.goto("https://gemini.google.com/app")
        page.wait_for_timeout(500)
        self.close_popups(page)
        self.wait_for_ui_ready(page)
        self.clear_attachments(page)
        self.clear_composer(page)
    
    def get_card_id(self, page: Page) -> Optional[str]:
        """Extract card ID from current URL."""
        try:
            return re.search(r"/app/([^/?#]+)", page.url or "").group(1)
        except Exception:
            return None
    
    def upload_image(self, page: Page, image_path: Path):
        """Upload image via clipboard paste or fallback to file input."""
        self.clear_attachments(page)
        self.wait_for_composer_ready(page)
        
        # Method 1: Clipboard Paste (Fast but flaky on remote)
        try:
            raw = image_path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")

            mime = "image/jpeg"
            suf = image_path.suffix.lower()
            if suf == ".png":
                mime = "image/png"
            elif suf == ".webp":
                mime = "image/webp"

            page.evaluate(
                """({b64, name, mime}) => {
                    const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
                    const dt = new DataTransfer();
                    dt.items.add(new File([new Blob([bin], {type: mime})], name, {type: mime}));
                    const el = document.querySelector("div[contenteditable='true']");
                    el.dispatchEvent(new ClipboardEvent('paste', {bubbles: true, cancelable: true, clipboardData: dt}));
                }""",
                {"b64": b64, "name": image_path.name, "mime": mime},
            )
            # Verify it actually appeared
            self._wait_for_attachment_preview(page, timeout_s=4.0)
            logger.info("[Upload] Clipboard paste verified.")
            
        except Exception as e:
            # Fallback to Method 2: File Input
            logger.info(f"[Upload] Clipboard failed or verification timed out: {e}. Switching to button fallback.")
            if self.remote_enabled:
                logger.info("[Upload] Using remote file upload fallback.")
                
            self._click_upload_trigger(page)
            page.locator("input[type='file']").first.set_input_files(str(image_path))
            self._wait_for_attachment_preview(page, timeout_s=15.0)

    def _wait_for_attachment_preview(self, page: Page, timeout_s: float = 15.0):
        """Wait for image preview to appear using Playwright's native waiting."""
        try:
            # More specific selector: Look for image in an attachment container or near 'Remove' buttons
            # We look for ANY img with blob src that is reasonably large or in the composer area
            # A 'blob:' image is the strongest indicator of a pending upload preview
            page.wait_for_selector("img[src^='blob:']", state="visible", timeout=timeout_s * 1000)
            
            # Optional: Check if it's not just a tiny icon? 
            # For now, visibility check is usually enough given how Gemini UI works
        except Exception as e:
            raise PlaywrightTimeoutError("Preview didn't appear") from e
    
    def fill_prompt(self, page: Page, text: str):
        """Fill prompt text into composer."""
        self.wait_for_composer_ready(page)
        self.clear_composer(page)
        page.locator("div[contenteditable='true']").first.fill(text)
    
    def click_send(self, page: Page):
        """Click send button."""
        selectors = [
            "button[aria-label*='Wyślij wiadomość' i]",
            "button[aria-label*='Wyślij' i]",
            "button[aria-label*='Send message' i]",
            "button[aria-label*='Send' i]",
            "button[type='submit']",
            "button[data-testid*='send' i]",
            "button:has(svg[aria-label*='Send' i])",
            "button:has(svg[aria-label*='Wyślij' i])",
        ]
        last_err = None
        for sel in selectors:
            try:
                btn = page.locator(sel).last
                if btn.count() == 0:
                    continue
                btn.click(force=True, timeout=2000)
                return
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err
        page.locator("button[aria-label*='Wyślij' i], button[aria-label*='Send' i]").last.click(force=True)

    def get_screenshot_bytes(self, page: Page) -> bytes:
        """Return screenshot as bytes (JPEG) without saving to disk."""
        try:
            return page.screenshot(full_page=True, type="jpeg", quality=70)
        except Exception as e:
            logger.warning(f"[Screenshot] Failed to capture bytes: {e}")
            return b""

    def get_trace_bytes(self) -> bytes:
        """Stop tracing and return trace zip content as bytes."""
        if not self.tracing_active:
            return b""
            
        import tempfile
        try:
            # Playwright requires path for stop_tracing, so utilize temp file
            # then read back into memory immediately
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name
            
            self.context.tracing.stop(path=tmp_path)
            self.tracing_active = False
            
            try:
                with open(tmp_path, "rb") as f:
                    data = f.read()
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            
            # Restart tracing for next run if needed (retain-on-failure)
            if self.tracing_mode == "continuous":
                try:
                    self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    self.tracing_active = True
                except Exception:
                    pass
                    
            return data
        except Exception as e:
            logger.warning(f"[Tracing] Failed to capture trace bytes: {e}")
            return b""

    def save_screenshot(self, page: Page, path: Path):
        """Legacy helper: Save screenshot to disk (wraps get_screenshot_bytes)."""
        try:
            data = self.get_screenshot_bytes(page)
            if data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                logger.info(f"[Screenshot] Saved to: {path}")
        except Exception as e:
            logger.warning(f"[Screenshot] Failed to save screenshot: {e}")

    def wait_for_response_or_limit(
        self, page: Page, timeout_ms: int = 350_000, has_limit_banner_fn=None
    ) -> Tuple[str, str]:
        """
        Wait for model response or Pro limit banner using Playwright's native waiting.
        
        Uses wait_for_function for efficient DOM monitoring - responds immediately when
        response appears, eliminating 0.5s average polling delay.
        
        Returns:
            Tuple of (text, status) where status is "response", "limit_pro", or "timeout"
        """
        # Small initial wait for UI to settle after sending
        page.wait_for_timeout(350)
        
        # JavaScript function that continuously monitors for response or limit banner
        # Returns object with {found: bool, isLimit: bool, text: string} when condition is met
        js_check = """() => {
            // Check for Pro limit text in body
            const bodyText = document.body.innerText || '';
            const limitPattern = /Zwiększ limit|Increase your limit|Osiągnięto limit|limit reached|You('|')ve reached|Przekroczono limit/i;
            if (limitPattern.test(bodyText)) {
                return {found: true, isLimit: true, text: ''};
            }
            
            // Find last model-response element
            const responses = document.querySelectorAll('model-response');
            if (responses.length === 0) {
                return null; // Keep waiting
            }
            
            const lastResponse = responses[responses.length - 1];
            
            // Check if visible and has text content
            if (!lastResponse.offsetParent) {
                return null; // Not visible, keep waiting
            }
            
            const rawText = (lastResponse.innerText || '').trim();
            if (!rawText) {
                return null; // No text yet, keep waiting
            }
            
            // Filter out "thinking" headers
            let cleaned = rawText;
            
            // 1. If it's ONLY a thinking header, treat as empty
            if (/^(Analiza|Pokaż przebieg rozumowania|Show reasoning|Thinking process)\\s*$/i.test(cleaned)) {
                return null; // Still thinking, keep waiting
            }
            
            // 2. Strip thinking header if present at start
            cleaned = cleaned.replace(/^(Analiza|Pokaż przebieg rozumowania|Show reasoning|Thinking process)\\s*\\n+/i, '').trim();
            
            if (cleaned) {
                return {found: true, isLimit: false, text: cleaned};
            }
            
            return null; // Empty after cleaning, keep waiting
        }"""
        
        try:
            # Wait for JavaScript function to return non-null value (response ready or limit detected)
            result = page.wait_for_function(js_check, timeout=timeout_ms)
            result_value = result.json_value()
            
            if result_value and result_value.get('found'):
                if result_value.get('isLimit'):
                    return ("", "limit_pro")
                else:
                    return (result_value.get('text', ''), "response")
            
            # Shouldn't reach here, but handle edge case
            return ("", "timeout")
            
        except Exception as e:
            # Timeout or other error
            logger.debug(f"[Browser] wait_for_function timeout or error: {e}")
            
            # Fallback: check one more time if limit banner callback provided
            if has_limit_banner_fn:
                try:
                    if has_limit_banner_fn(page):
                        return ("", "limit_pro")
                except Exception:
                    pass
            
            return ("", "timeout")
    
    # Model selection methods
    def _get_model_button_locator(self, page: Page):
        """Get locator for model selection button."""
        candidates = [
            page.locator("[data-test-id='bard-mode-menu-button'] button"),
            page.locator("[data-test-id='bard-mode-menu-button']"),
            page.locator("button.input-area-switch"),
            page.locator("div[role='group'][aria-label*='selektor trybu' i] button"),
            page.locator("div[role='group'][aria-label*='mode selector' i] button"),
            # Standard aria-label selectors
            page.locator("button[aria-label*='model' i]"),
            page.locator("[role='button'][aria-label*='model' i]"),
            page.locator("button[aria-label*='modelu' i]"),
            page.locator("[role='button'][aria-label*='modelu' i]"),
            page.locator("[data-testid*='model' i]"),
            # Text-based matching for model names (limit to buttons to avoid menu items)
            page.locator("button").filter(has_text=_MODEL_BUTTON_RE),
            page.locator("[role='button']").filter(has_text=_MODEL_BUTTON_RE),
        ]
        for loc in candidates:
            try:
                if loc.count() > 0:
                    logger.debug(f"🐛 [Model Debug] Found button with selector index {candidates.index(loc)}")
                    return loc
            except Exception:
                continue
        logger.warning("🧠 [Model] No model button locator matched, using fallback")
        return page.locator("button").filter(has_text=_MODEL_BUTTON_RE)

    def _first_visible(self, loc):
        try:
            count = min(loc.count(), 6)
        except Exception:
            return None
        for idx in range(count):
            try:
                el = loc.nth(idx)
                if el.is_visible():
                    return el
            except Exception:
                continue
        return None
    
    def detect_model_label(self, page: Page) -> Optional[str]:
        """Detect currently selected model from UI."""
        try:
            primary = page.locator("[data-test-id='bard-mode-menu-button']").first
            if primary.count() > 0 and primary.is_visible():
                t = primary.inner_text().strip()
                if t:
                    return self._normalize_model_label(t)

            loc = self._get_model_button_locator(page)
            btn = self._first_visible(loc) or loc.last
            if btn and btn.is_visible():
                t = btn.inner_text().strip()
                if t:
                    return self._normalize_model_label(t)
                aria = btn.get_attribute("aria-label")
                if aria:
                    return self._normalize_model_label(aria)
        except Exception:
            pass
        return None

    def _normalize_model_label(self, label: str) -> str:
        if not label:
            return label
        normalized = label.strip()
        if re.search(_PRO_MODEL_RE, normalized):
            return "Pro"
        return normalized
    
    def ensure_pro_model(self, page: Page, has_limit_banner_fn=None) -> str:
        """Try to select Pro model if not already selected."""
        before = self.detect_model_label(page) or "unknown"
        logger.info(f"🧠 [Model] Currently: {before}")

        if re.search(_PRO_MODEL_RE, before):
            logger.info("🧠 [Model] ✅ Already Pro.")
            return before
        
        # ⚠️ CRITICAL: Log warning when model is NOT Pro
        logger.warning(f"⚠️ [Model] NOT Pro! Current: {before}, switching to Pro...")
        
        # Log to database for history
        if self.db_manager and hasattr(self.db_manager, 'log_critical_event'):
            try:
                self.db_manager.log_critical_event(
                    profile_name=self.profile_name,
                    event_type="model_drift",
                    message=f"Model drifted to '{before}', enforcing Pro.",
                    requires_action=False,  # Auto-fix in progress
                    meta={"detected_model": before}
                )
            except Exception:
                pass

        if self.debug_artifacts_enabled:
            # Debug: Save screenshot before attempting model switch
            try:
                debug_path = Path(f"artifacts/screenshots/model_switch_before_{int(time.time())}.png")
                debug_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(debug_path), full_page=True)
                logger.info(f"🐛 [Model Debug] Pre-switch screenshot: {debug_path}")
            except Exception as e:
                logger.debug(f"Failed to save debug screenshot: {e}")

        # STRATEGY 0: Try clicking Pro button directly (as seen in headed mode)
        # This button may be visible in top-right corner without opening dropdown
        try:
            logger.info("🧠 [Model] Trying direct Pro button click...")
            # Look for clickable Pro button/link in header area
            direct_pro = page.locator(
                "button, a, [role='button'], [role='link']"
            ).filter(has_text=re.compile(r"^Pro$", re.IGNORECASE)).first
            
            if direct_pro.count() > 0 and direct_pro.is_visible():
                logger.info("🧠 [Model] Found direct Pro button, clicking...")
                # Fix: Use short timeout to fail fast if element is not actually clickable
                # Default playwright timeout is 30s which delays the fallback significantly
                direct_pro.click(timeout=3000)
                page.wait_for_timeout(self.model_switch_cooldown_ms)
                after = self.detect_model_label(page) or before
                if re.search(_PRO_MODEL_RE, after):
                    logger.info(f"🧠 [Model] ✅ Switched via direct button to: {after}")
                    return after
                else:
                    logger.info(f"🧠 [Model] Direct click didn't switch: {after}")
        except Exception as e:
            # Downgrade to info/debug since this is just an optimization strategy
            logger.info(f"🧠 [Model] Direct Pro button click failed (will try menu): {e}")

        for attempt in range(1, self.model_switch_retries + 1):
            try:
                # Close general popups
                self.close_popups(page)
                
                # CRITICAL: Close the "Get access to models" info popup if visible
                # This popup appears when clicking the model button and blocks menu access
                try:
                    info_popup = page.locator("[role='dialog'], [role='alertdialog']").filter(
                        has_text=re.compile(r"(Uzyskaj dostęp|dostępu do|wszystkich modeli|Get access)", re.IGNORECASE)
                    ).first
                    if info_popup.count() > 0 and info_popup.is_visible():
                        logger.info("🐛 [Model Debug] Detected 'Get access' popup, closing it...")
                        # Try to press Escape to close it
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(self.model_switch_cooldown_ms // 2)
                        # If still visible, try clicking outside
                        if info_popup.count() > 0 and info_popup.is_visible():
                            # Click outside to dismiss (safely)
                            # page.mouse.click(100, 100) # DISABLED: Risk of clicking model button
                            page.locator("body").click(position={"x": 10, "y": 10})
                            page.wait_for_timeout(self.model_switch_cooldown_ms // 4)
                except Exception as e:
                    logger.debug(f"Failed to close info popup: {e}")
                
                loc = self._get_model_button_locator(page)
                btn = self._first_visible(loc) or loc.last
                
                if not btn or btn.count() == 0 or not btn.is_visible():
                    logger.warning(f"🧠 [Model] No model selector found (attempt {attempt}).")
                    
                    if self.debug_artifacts_enabled:
                        # Debug: Log all buttons on page to diagnose selector issue
                        try:
                            all_buttons = page.locator("button").all()
                            logger.info(f"🐛 [Model Debug] Found {len(all_buttons)} buttons on page")
                            for i, b in enumerate(all_buttons[:10]):  # Log first 10
                                try:
                                    aria = b.get_attribute("aria-label") or ""
                                    text = b.inner_text(timeout=500) or ""
                                    logger.info(f"🐛 [Model Debug] Button {i}: aria='{aria}' text='{text}'")
                                except Exception:
                                    pass
                        except Exception as e:
                            logger.debug(f"Failed to log button info: {e}")
                    
                    page.wait_for_timeout(self.model_switch_cooldown_ms // 2)
                    continue

                logger.info(f"🧠 [Model] Clicking model button (attempt {attempt})")
                btn.click()
                page.wait_for_timeout(self.model_switch_cooldown_ms)  # Increased wait for menu animation

                if self.debug_artifacts_enabled:
                    # Debug: Save screenshot of opened menu
                    try:
                        menu_path = Path(f"artifacts/screenshots/model_menu_{int(time.time())}.png")
                        menu_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(menu_path), full_page=True)
                        logger.info(f"🐛 [Model Debug] Menu screenshot: {menu_path}")
                    except Exception as e:
                        logger.debug(f"Failed to save menu screenshot: {e}")

                # Try multiple strategies to find Pro menu item
                pro_item = None
                
                # Strategy 0: Direct menu option by test-id (new UI)
                menu = page.locator("[role='menu'], [role='listbox']").first
                menu_items = None
                if menu.count() > 0 and menu.is_visible():
                    menu_items = menu.locator(
                        "div[role='menuitem'], button[role='menuitem'], [role='menuitemradio'], [role='option']"
                    )
                else:
                    menu_items = page.locator(
                        "div[role='menuitem'], button[role='menuitem'], [role='menuitemradio'], [role='option']"
                    )
                direct_pro = page.locator("[data-test-id='bard-mode-option-pro']").first
                if direct_pro.count() > 0 and direct_pro.is_visible():
                    pro_item = direct_pro
                    logger.info("🧠 [Model] Found Pro item by test-id (strategy 0)")

                # Strategy 0b: Prefer menu items starting with "Pro" or "Gemini Pro"
                try:
                    if not pro_item:
                        for idx in range(min(menu_items.count(), 12)):
                            item = menu_items.nth(idx)
                            if not item.is_visible():
                                continue
                            text = item.inner_text().strip()
                            # STRICTER MATCH: Must start with Pro or Gemini...Pro
                            if re.match(r"^(Gemini\s+)?(1\.5\s+|2\.0\s+)?Pro\b", text, re.IGNORECASE):
                                pro_item = item
                                logger.info(f"🧠 [Model] Found Pro item in menu (strategy 0b): '{text}'")
                                break
                except Exception:
                    pass

                # Strategy 1: Look in visible menu
                if not pro_item and menu.count() > 0 and menu.is_visible():
                    # STRICTER FILTER
                    pro_item = menu.locator(
                        "div[role='menuitem'], button[role='menuitem'], [role='menuitemradio'], [role='option']"
                    ).filter(has_text=re.compile(r"^(Gemini\s+)?(1\.5\s+|2\.0\s+)?Pro\b", re.IGNORECASE)).first
                    if pro_item.count() > 0:
                        logger.info("🧠 [Model] Found Pro item in menu (strategy 1)")
                
                # Strategy 2: Look globally for Pro menu items (Fallback)
                if not pro_item or pro_item.count() == 0:
                    pro_item = page.locator(
                        "div[role='menuitem'], button[role='menuitem'], [role='menuitemradio'], [role='option']"
                    ).filter(has_text=re.compile(r"^(Gemini\s+)?(1\.5\s+|2\.0\s+)?Pro\b", re.IGNORECASE)).first
                    if pro_item.count() > 0:
                        logger.info("🧠 [Model] Found Pro item globally (strategy 2)")
                
                # Strategy 3: DISABLED (Too broad, causing false positives)
                # if not pro_item or pro_item.count() == 0:
                #     pro_item = page.get_by_text(re.compile(r"\bPro\b", re.IGNORECASE)).first
                #     if pro_item.count() > 0:
                #         logger.info("🧠 [Model] Found Pro item by text (strategy 3)")

                if pro_item and pro_item.count() > 0 and pro_item.is_visible():
                    logger.info("🧠 [Model] Clicking Pro menu item...")
                    pro_item.click(force=True)
                    # Close menu and wait for the selector label to update after click.
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass
                    try:
                        page.wait_for_function(
                            """() => {
                                const btn = document.querySelector("[data-test-id='bard-mode-menu-button']");
                                const text = btn ? btn.innerText : "";
                                return /\\bPro\\b/i.test(text || "");
                            }""",
                            timeout=4000,
                        )
                    except Exception:
                        pass
                    page.wait_for_timeout(500)
                    after = self.detect_model_label(page) or before

                    if has_limit_banner_fn and not re.search(_PRO_MODEL_RE, after) and has_limit_banner_fn(page):
                        logger.warning("🧠 [Model] Clicked Pro, but UI shows limit/fallback.")
                        return after

                    if re.search(_PRO_MODEL_RE, after):
                        logger.info(f"🧠 [Model] ✅ Switched to: {after}")
                        return after
                    else:
                        logger.warning(f"🧠 [Model] Clicked but still showing: {after}")
                        # Fallback: re-open menu and check whether Pro is selected.
                        try:
                            btn.click()
                            page.wait_for_timeout(800)
                            pro_selected = page.locator(
                                "[data-test-id='bard-mode-option-pro'][aria-checked='true']"
                            ).first
                            if pro_selected.count() > 0 and pro_selected.is_visible():
                                logger.info("🧠 [Model] Pro appears selected in menu; accepting selection.")
                                page.keyboard.press("Escape")
                                return "Pro"
                        except Exception:
                            pass
                        # Fallback: trigger click via JS and keyboard navigation.
                        try:
                            page.evaluate(
                                """() => {
                                    const el = document.querySelector("[data-test-id='bard-mode-option-pro']");
                                    if (el) el.click();
                                }"""
                            )
                            page.wait_for_timeout(1200)
                            after = self.detect_model_label(page) or after
                            if re.search(_PRO_MODEL_RE, after):
                                logger.info(f"🧠 [Model] ✅ Switched via JS to: {after}")
                                return after
                        except Exception:
                            pass
                        try:
                            btn.click()
                            page.wait_for_timeout(400)
                            page.keyboard.press("End")
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(1200)
                            after = self.detect_model_label(page) or after
                            if re.search(_PRO_MODEL_RE, after):
                                logger.info(f"🧠 [Model] ✅ Switched via keyboard to: {after}")
                                return after
                        except Exception:
                            pass
                else:
                    logger.warning("🧠 [Model] Pro menu item not found or not visible")
            
            except Exception as e:
                logger.warning(f"🧠 [Model] Could not switch to Pro (attempt {attempt}): {e}")
            
            page.wait_for_timeout(400)

        after = self.detect_model_label(page) or before
        if re.search(_FAST_MODEL_RE, after):
            logger.warning(f"🧠 [Model] ⚠️ Stuck on Fast/Flash: {after}")
        else:
            logger.info(f"🧠 [Model] After attempt: {after}")
        return after
    
    def check_pro_disabled_in_menu(self, page: Page) -> Optional[str]:
        """
        Check if Pro model is disabled/grayed in dropdown menu.
        Returns reset time text if found, None otherwise.
        
        Example text: "Pro\nLimit resetuje się 22 sty, 01:19"
        """
        try:
            # Close any open popups first
            self.close_popups(page)
            
            # Click model button to open dropdown
            loc = self._get_model_button_locator(page)
            btn = self._first_visible(loc) or loc.last
            
            if not btn or btn.count() == 0:
                logger.debug("[ProLimit] No model button found for disabled check")
                return None
            
            logger.debug("[ProLimit] Opening model menu to check for disabled Pro...")
            btn.click()
            page.wait_for_timeout(800)
            
            # Find ALL items with "Pro" text (disabled or enabled)
            pro_items = page.locator(
                "[role='menuitem'], [role='menuitemradio'], [role='option'], div[class*='menu'], div[class*='item']"
            ).filter(has_text=re.compile(r"\bPro\b", re.IGNORECASE))
            
            found_disabled = False
            reset_text = None
            
            for i in range(pro_items.count()):
                try:
                    item = pro_items.nth(i)
                    
                    # Check if disabled via multiple methods
                    is_disabled = (
                        item.get_attribute("aria-disabled") == "true" or
                        item.get_attribute("disabled") is not None or
                        "disabled" in (item.get_attribute("class") or "").lower() or
                        "inactive" in (item.get_attribute("class") or "").lower()
                    )
                    
                    if is_disabled:
                        # Get full text including reset time
                        full_text = item.inner_text(timeout=1000)
                        logger.info(f"🛑 [ProLimit] Found disabled Pro item with text: {full_text[:100]}")
                        
                        # Check if contains reset time text
                        if re.search(r"(Limit|resetuje|resets)", full_text, re.IGNORECASE):
                            reset_text = full_text
                            found_disabled = True
                            break
                except Exception as e:
                    logger.debug(f"[ProLimit] Error checking item {i}: {e}")
                    continue
            
            # Close menu
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            except Exception:
                pass
            
            if found_disabled and reset_text:
                logger.info(f"✅ [ProLimit] Detected disabled Pro with reset info")
                return reset_text
            
            logger.debug("[ProLimit] No disabled Pro item found in menu")
            return None
            
        except Exception as e:
            logger.debug(f"[ProLimit] Failed to check Pro disabled state: {e}")
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return None
    
    def ensure_fast_model(self, page: Page) -> str:
        """Try to select Fast model (fallback when Pro limited)."""
        before = self.detect_model_label(page) or "unknown"
        logger.info(f"🧠 [Model] (fast) Currently: {before}")

        if re.search(_FAST_MODEL_RE, before):
            logger.info("🧠 [Model] (fast) ✅ Already Fast/Flash.")
            return before

        try:
            btn = self._get_model_button_locator(page).last
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                page.wait_for_timeout(600)

                fast_item = page.locator("div[role='menuitem'], button[role='menuitem']").filter(has_text=_FAST_MODEL_RE).first
                if fast_item.count() > 0 and fast_item.is_visible():
                    fast_item.click(force=True)
                    page.wait_for_timeout(900)
                    after = self.detect_model_label(page) or before
                    logger.info(f"🧠 [Model] (fast) ✅ Switched to: {after}")
                    return after

                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"🧠 [Model] (fast) Could not switch to Fast: {e}")

        after = self.detect_model_label(page) or before
        if re.search(_PRO_MODEL_RE, after):
            logger.info(f"🧠 [Model] (fast) Still Pro after attempt: {after}")
        else:
            logger.info(f"🧠 [Model] (fast) After attempt: {after}")
        return after

    def save_error_trace(self, path: Path) -> bool:
        """Save error trace and restart tracing.
        
        This implements the retain-on-failure strategy: save trace only on errors,
        then immediately restart tracing for the next operation.
        
        Args:
            path: Path where to save the trace .zip file
            
        Returns:
            True if trace was saved successfully, False otherwise
        """
        if not self.context:
            return False
        if not self.tracing_active and self.tracing_mode != "on_failure":
            return False
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if not self.tracing_active and self.tracing_mode == "on_failure":
                try:
                    self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    self.tracing_active = True
                except Exception as start_err:
                    logger.warning(f"[Tracing] Failed to start on-failure trace: {start_err}")
                    self.tracing_active = False
                    return False

            # Stop tracing and save to file
            self.context.tracing.stop(path=str(path))
            self.tracing_active = False
            logger.info(f"[Tracing] Saved error trace to: {path}")
            
            # Immediately restart tracing for next operation if continuous
            if self.tracing_mode == "continuous":
                try:
                    self.context.tracing.start(
                        screenshots=True,
                        snapshots=True,
                        sources=True
                    )
                    self.tracing_active = True
                    logger.info("[Tracing] Restarted tracing after error capture")
                except Exception as restart_err:
                    logger.warning(f"[Tracing] Failed to restart tracing: {restart_err}")
                    self.tracing_active = False
            
            return True
            
        except Exception as e:
            logger.warning(f"[Tracing] Failed to save error trace: {e}")
            self.tracing_active = False
            return False
