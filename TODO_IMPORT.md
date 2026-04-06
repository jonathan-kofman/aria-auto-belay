# ARIA-OS Import Path

This repo previously contained a copy of ARIA-OS.
Generic pipeline code now lives in aria-os-export.

To use ARIA-OS from this repo:
  pip install -e /path/to/aria-os-export
  # or add to sys.path

Files that were here and are now in aria-os-export:
  - aria_os/ (entire CAD/agent pipeline package)
  - cem/ (core CEM modules)
  - contracts/ (JSON schemas)
  - dashboard/ (generic CAD dashboard)
  - tests/ (pipeline tests)
  - Various root shims (cem_*.py, run_aria_os.py, batch.py, etc.)
