"""
OCR Dashboard V2 - Process Management Service
Handles subprocess management for OCR workers.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

# Add src to path for ActivityLogger import
src_path = Path(__file__).parents[2] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from ocr_engine.utils.activity_logger import ActivityLogger

    HAS_ACTIVITY_LOGGER = True
except ImportError:
    HAS_ACTIVITY_LOGGER = False

# Global state for tracking running processes
current_processes: list[subprocess.Popen] = []
current_profile_processes: dict[str, subprocess.Popen] = {}
current_remote_profiles: dict[str, dict] = {}
profile_start_attempts: dict[str, float] = {}
postprocess_process: subprocess.Popen | None = None

PROFILE_START_TRACK_SEC = 240


def pid_is_running(pid: int | None) -> bool:
    """Check if a process with given PID is running."""
    if pid is None:
        return False
    try:
        # Treat zombies as not running to avoid stale "active" status.
        stat_path = Path("/proc") / str(pid) / "stat"
        if stat_path.exists():
            try:
                state = stat_path.read_text(encoding="utf-8", errors="ignore").split()[2]
                if state == "Z":
                    return False
            except Exception:
                pass
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def terminate_pid(pid: int) -> None:
    """Terminate a process by PID."""
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def terminate_proc(proc: subprocess.Popen) -> None:
    """Terminate a subprocess."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        pass


def find_pids_by_patterns(patterns: list[str]) -> set[int]:
    """Find PIDs matching command line patterns."""
    pids = set()
    proc_root = Path("/proc")

    if not proc_root.exists():
        return pids

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", "ignore")
            for pattern in patterns:
                if pattern in cmdline:
                    pids.add(pid)
                    break
        except Exception:
            continue

    return pids


def iter_runpy_processes() -> list[tuple[int, str | None]]:
    """Return list of (pid, profile_suffix or None) for run.py processes."""
    results = []
    proc_root = Path("/proc")

    if not proc_root.exists():
        return results

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            # Skip zombies (defunct processes).
            stat_path = entry / "stat"
            if stat_path.exists():
                try:
                    state = stat_path.read_text(encoding="utf-8", errors="ignore").split()[2]
                    if state == "Z":
                        continue
                except Exception:
                    pass

            cmdline = (entry / "cmdline").read_bytes()
            if b"run.py" not in cmdline:
                continue

            profile = None
            try:
                env_bytes = (entry / "environ").read_bytes()
                for item in env_bytes.split(b"\0"):
                    if item.startswith(b"OCR_PROFILE_SUFFIX="):
                        profile = item.split(b"=", 1)[1].decode("utf-8", "ignore")
                        break
            except Exception:
                profile = None

            results.append((pid, profile))
        except Exception:
            continue

    return results


def get_profile_pids(safe_profile: str) -> set[int]:
    """Collect all PIDs belonging to a profile (run.py processes)."""
    pids = set()
    for pid, profile in iter_runpy_processes():
        if profile == safe_profile:
            pids.add(pid)
    return pids


def stop_profile_processes(safe_profile: str) -> None:
    """Stop all processes for a profile."""
    pids = get_profile_pids(safe_profile)
    for pid in pids:
        terminate_pid(pid)

    # Log stop event to database
    if HAS_ACTIVITY_LOGGER and pids:
        try:
            logger = ActivityLogger()
            logger.log_stop(
                component="profile_worker",
                profile_name=safe_profile,
                triggered_by="api",
                reason="Zatrzymano profil przez dashboard",
            )
        except Exception as log_error:
            print(f"Warning: Could not log stop event: {log_error}")


def record_profile_start(profile_name: str) -> None:
    """Record that a profile start was attempted."""
    import time

    if profile_name:
        profile_start_attempts[profile_name] = time.time()


def start_profile_process(profile_name: str, headed: bool = False) -> tuple[bool, str]:
    """Start the OCR worker process for a profile."""

    # Check if already running
    pids = get_profile_pids(profile_name)
    if pids:
        # Check if actually running
        running_pids = [pid for pid in pids if pid_is_running(pid)]
        if running_pids:
            return False, f"Profil '{profile_name}' już pracuje (PID: {running_pids})"

    try:
        # Prepare environment
        env = os.environ.copy()
        env["OCR_PROFILE_SUFFIX"] = profile_name
        env["OCR_HEADED"] = "1" if headed else "0"

        # Run process
        # Assuming run.py is in the project root (where CWD usually is for the service)
        cmd = ["python3", "run.py"]

        # Determine working directory (project root)
        cwd = Path(__file__).parents[2]  # app/services/process.py -> app/services -> app -> root
        if not (cwd / "run.py").exists():
            return False, "Nie znaleziono pliku run.py"

        # Prepare log file
        log_dir = cwd / "logs" / "profiles"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{profile_name}.log"
        log_fp = open(log_file, "a", encoding="utf-8")

        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        # Record start
        current_processes.append(process)
        current_profile_processes[profile_name] = process
        record_profile_start(profile_name)

        # Log to database
        if HAS_ACTIVITY_LOGGER:
            try:
                logger = ActivityLogger()
                logger.log_start(
                    component="profile_worker",
                    profile_name=profile_name,
                    configuration={"headed": headed, "pid": process.pid},
                    triggered_by="api",
                    reason="Uruchomiono profil przez dashboard",
                )
            except Exception as log_error:
                print(f"Warning: Could not log start event: {log_error}")

        return True, f"Uruchomiono profil '{profile_name}' (PID: {process.pid})"

    except Exception as e:
        return False, f"Błąd uruchamiania procesu: {e}"


def start_login_process(profile_name: str) -> tuple[bool, str]:
    """Start the login helper process for a profile."""

    # Check if already running (run.py)
    pids = get_profile_pids(profile_name)
    running_pids = [pid for pid in pids if pid_is_running(pid)]
    if running_pids:
        return (
            False,
            f"Profil '{profile_name}' jest zajęty przez proces OCR (PID: {running_pids}). Zatrzymaj go najpierw.",
        )

    try:
        # Prepare environment
        env = os.environ.copy()
        env["OCR_PROFILE_SUFFIX"] = profile_name
        env["OCR_HEADED"] = "1"  # Always headed for login

        # Run process
        cmd = ["python3", "scripts/login_profile.py"]

        # Determine working directory (project root)
        cwd = Path(__file__).parents[2]
        if not (cwd / "scripts" / "login_profile.py").exists():
            return False, "Nie znaleziono pliku scripts/login_profile.py"

        # Prepare log file - separate from main log to avoid clutter/confusion?
        # Or same log file so frontend 'fetchLoginLog' works if it uses same log?
        # Frontend polls `/api/profiles/login/log`. We need to see where that endpoint reads from.
        # Assuming it reads from `logs/profiles/{name}.login.log` or similar?
        # Let's check where `fetchLoginLog` reads.
        # IF we don't know, let's use a specific log file and ensure the route reads it.

        log_dir = cwd / "logs" / "profiles"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{profile_name}.login.log"
        # Truncate login log for fresh start
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("=== Inicjalizacja logowania ===\n")

        log_fp = open(log_file, "a", encoding="utf-8")

        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        # We don't track login processes in `current_profile_processes` to avoid 'stop' command killing them strictly?
        # Or maybe we should?
        # For now, let's just let them run. They should close themselves.
        # But we might want to kill them.

        return True, f"Uruchomiono logowanie dla '{profile_name}' (PID: {process.pid})"

    except Exception as e:
        return False, f"Błąd uruchamiania logowania: {e}"


def prune_profile_starts(now_ts: float | None = None) -> None:
    """Remove stale profile start attempts."""
    import time

    cutoff = PROFILE_START_TRACK_SEC
    now_val = now_ts or time.time()
    stale = [p for p, ts in profile_start_attempts.items() if (now_val - ts) > cutoff]
    for p in stale:
        profile_start_attempts.pop(p, None)
