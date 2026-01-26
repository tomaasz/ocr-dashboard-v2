"""
OCR Dashboard V2 - Process Management Service
Handles subprocess management for OCR workers.
"""

import os
import signal
import subprocess
from pathlib import Path

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


def record_profile_start(profile_name: str) -> None:
    """Record that a profile start was attempted."""
    import time

    if profile_name:
        profile_start_attempts[profile_name] = time.time()


def start_profile_process(profile_name: str) -> tuple[bool, str]:
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
        env["OCR_HEADED"] = "0"  # Default to headless

        # Run process
        # Assuming run.py is in the project root (where CWD usually is for the service)
        cmd = ["python3", "run.py"]

        # Determine working directory (project root)
        cwd = Path(__file__).parents[2]  # app/services/process.py -> app/services -> app -> root
        if not (cwd / "run.py").exists():
            return False, "Nie znaleziono pliku run.py"

        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Record start
        current_processes.append(process)
        current_profile_processes[profile_name] = process
        record_profile_start(profile_name)

        return True, f"Uruchomiono profil '{profile_name}' (PID: {process.pid})"

    except Exception as e:
        return False, f"Błąd uruchamiania procesu: {e}"


def prune_profile_starts(now_ts: float | None = None) -> None:
    """Remove stale profile start attempts."""
    import time

    cutoff = PROFILE_START_TRACK_SEC
    now_val = now_ts or time.time()
    stale = [p for p, ts in profile_start_attempts.items() if (now_val - ts) > cutoff]
    for p in stale:
        profile_start_attempts.pop(p, None)
