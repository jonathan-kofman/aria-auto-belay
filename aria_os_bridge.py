"""
aria_os_bridge.py — Makes aria-os-export importable from this repo.

Usage:
    import aria_os_bridge  # sets up sys.path
    from aria_os import orchestrator  # now works

If aria-os-export is not found, this module does nothing (no error).
The dashboard tabs that need aria_os wrap their imports in try/except.
"""
import sys
from pathlib import Path

_EXPORT_DIR = Path(__file__).resolve().parent.parent / "aria-os-export"

if _EXPORT_DIR.is_dir() and str(_EXPORT_DIR) not in sys.path:
    sys.path.insert(0, str(_EXPORT_DIR))
