"""
watch.py — File watcher. Polls watched paths every second, re-runs a command on any change.
Pure stdlib, no extra dependencies.

Usage:
    python watch.py aria_os/cadquery_generator.py -- python preview.py "ratchet ring"
    python watch.py aria_os/ -- python -m pytest tests/ -q
    python watch.py aria_os/ src/ -- python run_aria_os.py "bracket"

- Uses MD5 hashing of file contents to detect changes
- On change: terminates previous subprocess (if still running), spawns a fresh one
- Runs command once immediately on start
- Ctrl+C stops cleanly
"""
import sys
import os
import time
import signal
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _collect_files(paths: list[Path]) -> list[Path]:
    """Recursively collect all files under the given paths."""
    files = []
    for p in paths:
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    files.append(f)
    return files


def _hash_file(path: Path) -> str:
    """Return MD5 hex digest of a file's contents, or empty string on error."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _snapshot(paths: list[Path]) -> dict[str, str]:
    """Return {filepath_str: md5} for all files under watched paths."""
    result = {}
    for f in _collect_files(paths):
        result[str(f)] = _hash_file(f)
    return result


def _terminate(proc: subprocess.Popen | None) -> None:
    """Terminate a subprocess and its children gracefully."""
    if proc is None:
        return
    if proc.poll() is not None:
        return
    print("\n[watch] Terminating previous run...", flush=True)
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except OSError:
        pass


def _launch(cmd: list[str]) -> subprocess.Popen:
    """Launch the command as a subprocess, inheriting stdio."""
    kwargs: dict = {
        "stdout": None,
        "stderr": None,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(cmd, **kwargs)


def _parse_args(argv: list[str]) -> tuple[list[Path], list[str]]:
    """
    Parse CLI arguments into (watch_paths, command).
    Everything before '--' is watch paths; everything after is the command.
    """
    if "--" not in argv:
        print("Usage: python watch.py <path> [path...] -- <command>")
        print("Example: python watch.py aria_os/ -- python -m pytest tests/ -q")
        sys.exit(1)
    sep = argv.index("--")
    raw_paths = argv[:sep]
    command = argv[sep + 1:]
    if not raw_paths:
        print("[watch] Error: no watch paths provided before '--'")
        sys.exit(1)
    if not command:
        print("[watch] Error: no command provided after '--'")
        sys.exit(1)
    paths = []
    for rp in raw_paths:
        p = Path(rp)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"[watch] Warning: path does not exist: {p}")
        paths.append(p)
    return paths, command


def main() -> None:
    args = sys.argv[1:]
    watch_paths, command = _parse_args(args)

    watch_display = ", ".join(str(p) for p in watch_paths)
    cmd_display = " ".join(command)
    print(f"[watch] Watching: {watch_display}")
    print(f"[watch] Command:  {cmd_display}")
    print(f"[watch] Press Ctrl+C to stop.\n")

    # Initial snapshot and run
    last_snapshot = _snapshot(watch_paths)
    proc = _launch(command)
    print(f"[watch] Launched PID {proc.pid}", flush=True)

    try:
        while True:
            time.sleep(1)
            current = _snapshot(watch_paths)
            if current != last_snapshot:
                # Identify changed files for display
                changed = [
                    f for f in set(current) | set(last_snapshot)
                    if current.get(f) != last_snapshot.get(f)
                ]
                for cf in changed[:3]:
                    print(f"[watch] Changed: {cf}", flush=True)
                if len(changed) > 3:
                    print(f"[watch] ... and {len(changed) - 3} more", flush=True)

                last_snapshot = current
                _terminate(proc)
                print(f"[watch] Re-running: {cmd_display}\n", flush=True)
                proc = _launch(command)
                print(f"[watch] Launched PID {proc.pid}", flush=True)
    except KeyboardInterrupt:
        print("\n[watch] Stopped.", flush=True)
        _terminate(proc)
        sys.exit(0)


if __name__ == "__main__":
    main()
