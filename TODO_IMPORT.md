# ARIA-OS Import Path — Post-Split Setup

## What happened
This repo was split on 2026-04-06. Generic CAD pipeline code moved to `aria-os-export`.
This repo now contains ONLY hardware-specific code for the ARIA auto-belay device.

## Import mechanism
`aria_os_bridge.py` adds `../aria-os-export` to `sys.path` when it exists.
The dashboard (`aria_dashboard.py`) imports it automatically.

### To use ARIA-OS features:
```bash
# Option A: Just have aria-os-export as a sibling directory (auto-detected)
ls ../aria-os-export/aria_os/  # if this exists, it works

# Option B: pip install (when pyproject.toml is added)
pip install -e ../aria-os-export
```

## What's in each repo

### aria-auto-belay (this repo) — hardware-specific
- `device/` — firmware (STM32/ESP32), React Native app, training data
- `aria_models/` — state machine, drop physics simulation
- `aria_cem/` — ARIA-specific CEM module (drop test physics)
- `aria_dashboard.py` — hardware test dashboard (70KB)
- `dashboard/` — 15 tab modules (12 hardware, 3 OS-generic with graceful degradation)
- `tools/` — simulator, HIL test, PID tuner, constants sync
- `context/` — hardware context files
- `cad-pipeline/` — ARIA-specific assembly configs and part specs

### aria-os-export (sibling repo) — generic CAD pipeline
- `aria_os/` — orchestrator, generators, validators, LLM client, API server
- `cem/` — core CEM modules (registry, core, LRE, civil)
- `contracts/` — JSON schemas
- `tests/` — pipeline test suite
- Root scripts: `run_aria_os.py`, `batch.py`, `assemble.py`, etc.

## OS-generic dashboard tabs
3 tabs (`aria_cad_tab`, `aria_api_tab`, `aria_outputs_tab`) need aria-os-export.
They wrap imports in try/except and show a helpful message when it's not available.
The other 12 tabs are fully self-contained hardware tabs.
