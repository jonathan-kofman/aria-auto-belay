# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Is

ARIA (Autonomous Rope Intelligence Architecture) — a wall-mounted lead climbing auto-belay device. The codebase has three active concerns running in parallel:
1. **ARIA-OS** — a multi-domain AI-driven CAD pipeline (CadQuery + LLM + CEM physics)
2. **Firmware** — STM32 safety layer + ESP32 intelligence layer (hardware not yet arrived)
3. **aria-climb** — React Native / Expo companion app

---

## Commands

### ARIA-OS (CAD pipeline)
```bash
# Generate a part (natural language goal)
python run_aria_os.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"

# List all generated parts with validation status
python run_aria_os.py --list

# Re-validate all STEP files
python run_aria_os.py --validate

# Modify an existing part
python run_aria_os.py --modify outputs/cad/generated_code/aria_spool.py "add 6x M6 bolt circle at 90mm radius"

# Run CEM physics check on all parts
python run_aria_os.py --cem-full

# Material study for a part
python run_aria_os.py --material-study aria_ratchet_ring
python run_aria_os.py --material-study-all

# Parametric optimizer
python run_aria_os.py --optimize aria_spool --goal minimize_weight --constraint "SF>=2.0"

# Optimize params then immediately regenerate CAD with best result
python run_aria_os.py --optimize-and-regenerate aria_spool --goal minimize_weight --material 6061_al

# Generate a part and append it to an existing assembly config
python run_aria_os.py --generate-and-assemble "pump housing" --into assembly_configs/foo.json --as pump_housing --at "0,0,10" --rot "0,0,0"

# Lattice generation (uses Blender)
python run_aria_os.py --lattice --pattern honeycomb --form volumetric --width 100 --height 100 --depth 10
python run_aria_os.py --lattice-test

# Assembly from JSON config
python run_aria_os.py --assemble assembly_configs/aria_clutch_assembly.json

# Print-fit scaling check
python run_aria_os.py --print-scale aria_ratchet_ring --scale 0.75

# Generate from a photo (vision AI extracts goal, then runs pipeline)
python run_aria_os.py --image photo.jpg
python run_aria_os.py --image photo.jpg "it's a bracket"   # optional hint

# Preview generated model in 3D browser before export
python run_aria_os.py --preview "ARIA ratchet ring, 213mm OD"
# Opens Three.js STL viewer in browser; choose export format in terminal:
#   [1] step  [2] stl  [3] both (default)  [4] skip
```

### Dashboard
```bash
# Windows (sets up .python/ local env automatically)
START_DASHBOARD.bat

# System Python
pip install -r requirements.txt
streamlit run aria_dashboard.py
```

### ARIA-OS dependencies (separate from dashboard)
```bash
pip install -r requirements_aria_os.txt   # cadquery==2.7.0, anthropic>=0.39.0, etc.
```

### Tests
```bash
python aria_models/static_tests.py        # unit tests for state machine / physics
python tools/aria_test_harness.py         # automated scenario PASS/FAIL tests
python tools/aria_hil_test.py             # hardware-in-loop tests (requires connected hardware)

# CAD pipeline test suite (186 tests, all headless):
python -m pytest tests/ -q
#  tests/test_post_gen_validator.py  — validation loop, STEP/STL quality, repair
#  tests/test_cad_router.py          — multi-backend routing + 14-template smoke tests
#  tests/test_spec_extractor.py      — structured spec extraction (40 tests)
#  tests/test_api_server.py          — FastAPI server: 422 validation, health, runs log
#  tests/test_e2e_pipeline.py        — 5 diverse descriptions, one per backend:
#      cadquery (bracket, ratchet ring) — real STEP+STL + watertight assertions
#      grasshopper (spool CQ fallback) — watertight + diameter ≈ spec
#      blender (gyroid lattice)        — artifact produced + bpy reference
#      fusion360 (motor housing)       — script non-empty + fusion API reference
```

### Simulator & tools
```bash
python tools/aria_simulator.py          # headless state machine CLI (scenario climb, voice take, status)
python tools/aria_constants_sync.py     # verify constants match between simulator and firmware
python tools/aria_pid_tuner.py          # PID Kp/Ki/Kd sweep
```

### aria-climb app
```bash
cd aria-climb
npm install --legacy-peer-deps
npx expo run:android    # add google-services.json first
```

### LLM backend
All keys are **optional**. Priority chain: **Anthropic → Gemini → Ollama → heuristic fallback**. The pipeline never crashes due to a missing key.

- **Anthropic** — set `ANTHROPIC_API_KEY` in `.env`; enables full LLM generation + vision image analysis.
- **Google Gemini** — set `GOOGLE_API_KEY` in `.env`; enables LLM generation + vision image analysis. Set `GEMINI_MODEL` to override (default: `gemini-2.0-flash`).
- **Ollama (local)** — install [Ollama](https://ollama.com), run `ollama pull deepseek-coder`. Set `OLLAMA_HOST` / `OLLAMA_MODEL` in `.env` if non-default.
- **Heuristic templates** — 16 known parts work with zero network calls (see `cadquery_generator._CQ_TEMPLATE_MAP`).

See `aria_os/llm_client.py` — `call_llm(prompt, system, *, repo_root)` is the single entry point used by all generators. `analyze_image_for_cad(image_path, hint, *, repo_root)` uses the same priority chain for vision (Anthropic → Gemini → None).

---

## Architecture: ARIA-OS CAD Pipeline

The main pipeline lives in `aria_os/` and runs as: **goal string → plan → route → generate → validate → CEM check → export → log**.

### Entry & routing
- `run_aria_os.py` — CLI; calls `aria_os.run(goal)`
- `aria_os/orchestrator.py` — pipeline controller
- `aria_os/planner.py` — goal → structured plan dict; detects dimensional overrides to decide template vs LLM. `has_dimensional_overrides(goal, template_dims, part_id)` routes to LLM only for **>25% deviation** from template defaults — smaller changes use the template with spec-injected params. Feature keywords (keyway, involute, spline, etc.) always force LLM regardless of magnitude. `OVERRIDE_FEATURE_KEYWORDS` covers 8 part types.
- `aria_os/tool_router.py` — routes to `cadquery` / `fusion` / `grasshopper` / `blender` based on goal keywords and `part_id`. `CADQUERY_KEYWORDS` includes `"nozzle"`, `"rocket"`, `"lre"`, `"liquid rocket"`, `"turbopump"`, `"injector"` so LRE parts route to CadQuery headless instead of Grasshopper.
- `aria_os/orchestrator.py` — after `attach_brief_to_plan`, calls `extract_spec(goal)` + `merge_spec_into_plan(spec, plan)` to populate `plan["params"]` with user-specified dimensions. Prints `[SPEC] key=val (user) ...` for each extracted dim. After the merge, syncs user-specified dimensional keys (`od_mm`, `bore_mm`, `thickness_mm`, `height_mm`, `width_mm`, `depth_mm`, `length_mm`, `diameter_mm`) back into `plan["base_shape"]` so validation `expected_bbox` checks against what the user asked for, not planner template defaults. Grasshopper `write_grasshopper_artifacts` call is wrapped in a retry loop (up to `max_attempts`); `RuntimeError` is caught, logged, and retried — never propagates as unhandled traceback.

### CAD generation
- `aria_os/generator.py` — CadQuery templates for `KNOWN_PART_IDS`; LLM fallback for unknown parts
- `aria_os/llm_client.py` — **unified LLM client**. Priority: Anthropic → Gemini → Ollama → `None`. Never raises. All generators import `call_llm` from here. `get_anthropic_key()` / `get_google_key()` read from env or `.env`. `get_ollama_status()` feeds `/api/health`. `_LOCAL_MODEL_NOTE` injected into system prompt when Ollama is used. `analyze_image_for_cad(image_path, hint)` — vision AI: tries `_try_anthropic_vision` then `_try_gemini_vision`; supports new `google-genai` SDK and legacy `google-generativeai` SDK.
- `aria_os/llm_generator.py` — Anthropic/OpenAI backend; injects mechanical constants + failure patterns into system prompt; `_get_api_key()` now delegates to `llm_client.get_anthropic_key()` (kept for vision callers only)
- `aria_os/cad_prompt_builder.py` — builds engineering brief from CEM outputs + context for LLM prompt. `_build_dim_hints` emits **all** `plan["params"]` keys (including CEM-derived physics params) for every domain under a MANDATORY marker — LLM must use exact values, not recalculate.
- `aria_os/preview_ui.py` — **3D STL preview** before export. `show_preview(stl_path, part_id) -> ExportChoice`. Embeds STL as base64 in a self-contained Three.js HTML page (no server needed), opens in default browser, then prompts terminal for export choice: `"step" | "stl" | "both" | "skip"`. Activated via `--preview` flag or `orchestrator.run(preview=True)`.
- `aria_os/fusion_generator.py` — generates Fusion 360 Python API scripts (run inside Fusion)
- `aria_os/grasshopper_generator.py` — generates Grasshopper/Rhino Compute artifacts; **Grasshopper is the default tool for 6 core ARIA parts** (see `GRASSHOPPER_PART_IDS` in `tool_router.py`). `write_grasshopper_artifacts` raises `RuntimeError` (never writes a placeholder) when no template exists and LLM is unavailable — this propagates as a validation loop retry. Script size < 500 bytes is a hard failure. Ratchet ring union loop: repairs tooth brep before + after transform, retries with tol=0.01 on failure, raises `RuntimeError` if `Faces.Count < 20` post-loop.
- `aria_os/blender_generator.py` — generates Blender lattice artifacts

### Grasshopper integration module (`aria_os/gh_integration/`)
High-level pipeline helper added 2026-03. Use this when you need to run the full GH export flow from Python.

- `gh_aria_parts.py` — parametric defaults, CEM SF thresholds, and dual-script generation (GH Python component + CadQuery fallback) for the 6 known ARIA parts: `aria_spool`, `aria_cam_collar`, `aria_housing`, `aria_ratchet_ring`, `aria_brake_drum`, `aria_rope_guide`
- `gh_to_step_bridge.py` — `run_gh_pipeline(goal, part_id, repo_root)` → parses params, runs CEM check, exports STEP/STL, appends structured entry to `outputs/aria_generation_log.json`

Per-part GH output layout:
```
outputs/cad/grasshopper/<part>/
  params.json                   # parametric inputs
  <part>_gh_component.py        # paste into Grasshopper Python node
  <part>_cq_fallback.py         # headless CadQuery export (no Rhino needed)
  run_rhino_compute.py          # runner script
```

**CEM SF thresholds for GH parts** (fail if below):
| Part | SF check | Required |
|---|---|---|
| aria_ratchet_ring | tooth_shear | **8.0** (safety-critical — higher than default 2.0) |
| aria_spool | radial_load | 2.0 |
| aria_cam_collar | taper_engagement | 2.0 |
| aria_housing | wall_bending | 2.0 |
| aria_brake_drum | hoop_stress | 2.0 |

### Validation & export
- `aria_os/validator.py` — bbox check, STEP re-import (solid count ≥ 1), mesh integrity, housing spec
- `aria_os/exporter.py` — STEP + STL export; output paths under `outputs/cad/`
- `aria_os/cad_learner.py` — records every attempt outcome to `outputs/cad/learning_log.json`
- `aria_os/post_gen_validator.py` — **deepened validation loop** (up to 3 retries, failure-context injection):
  - `parse_spec(goal, plan)` → extracts `{od_mm, bore_mm, height_mm, n_teeth, has_bore, volume_min/max, tol_mm}`
  - `check_geometry(stl_path, spec)` → trimesh bbox/volume/bore/watertight checks
  - `_detect_bore(mesh, bb, spec)` → spec-derived threshold: when `bore_mm`+`od_mm` known, threshold = `1 - (bore_mm/od_mm)**2 * 0.5`; falls back to fixed 0.65. Avoids false negatives on large bores and false positives on thin walls.
  - `validate_step(step_path)` → STEP readability + solid count via CadQuery (header fallback)
  - `check_and_repair_stl(stl_path)` → watertight check + trimesh repair (fill_holes/fix_normals/fix_winding) + re-export
  - `check_output_quality(step_path, stl_path)` → combined STEP+STL check; returns `{passed, failures, step, stl}`
  - `run_validation_loop(generate_fn, goal, plan, step_path, stl_path, max_attempts=3, *, skip_visual, check_quality)` →
    - Calls `generate_fn(plan, step_path, stl_path, repo_root, previous_failures=[...])` on each retry
    - `previous_failures` is passed via `_call_generate_fn()` using `inspect.signature` (backward-compat)
    - Tracks best attempt (fewest failures); returns best on final failure with `validation_failures: list[str]`
    - Returns `quality_result` dict when `check_quality=True`; orchestrator passes `check_quality=True`
  - All backend generators accept `previous_failures: list[str] | None = None`; `cadquery_generator.py` injects into LLM prompt
  - **Output quality wired into orchestrator** (Item 4): `check_output_quality(step_path, stl_path)` runs for ALL backends after generation; result stored in `session["output_quality"]`. Logs repair events. Orchestrator also passes `check_quality=True` to `run_validation_loop` for GH/CadQuery; result in `session["validation"]["quality"]` and `session["validation"]["validation_failures"]`.
- `aria_os/cadquery_generator.py` — `_CQ_TEMPLATE_MAP` contains **16 templates**: 7 ARIA structural parts (`aria_ratchet_ring`, `aria_housing`, `aria_spool`, `aria_cam_collar`, `aria_brake_drum`, `aria_catch_pawl`, `aria_rope_guide`) + 7 generic mechanical parts (`aria_bracket`, `aria_flange`, `aria_shaft`, `aria_pulley`, `aria_cam`, `aria_pin`, `aria_spacer`) + 2 LRE parts (`lre_nozzle`, `aria_nozzle` — convergent+divergent hollow bell-nozzle revolved in XY plane around Y axis; params: `entry_r_mm=60`, `throat_r_mm=25`, `exit_r_mm=80`, `conv_length_mm=80`, `length_mm=200`, `wall_mm=3`). Every template produces valid geometry on first attempt. Unknown parts fall back to LLM. Template param key conventions (standard spec keys accepted across all templates):
  - `_cq_bracket`: `n_bolts` controls hole count; holes spaced evenly along width (15% margin); `bolt_dia_mm` → `hole_dia_mm` fallback
  - `_cq_brake_drum`: `od_mm`, `height_mm`/`width_mm`, `wall_mm`; hub bore from `bore_mm` (fallback: `od*0.12`); wall from `wall_mm` (fallback: `max(8, od*0.04)`); shaft_d clamped to `< od - 2*wall`
  - `_cq_catch_pawl`: `length_mm`, `width_mm`, `thickness_mm`; pivot bore from `bore_mm` → `pivot_hole_dia_mm` fallback
  - `_cq_rope_guide`: `width_mm`, `height_mm`, `thickness_mm`, `diameter_mm` (roller), `bore_mm`; legacy bracket_* keys still accepted as fallback
- `aria_os/spec_extractor.py` — **structured spec extraction** (Item 3): converts natural-language descriptions to typed dicts before any generator or router call.
  - `extract_spec(description) -> dict` — extracts: `od_mm`, `bore_mm`, `id_mm`, `thickness_mm`, `height_mm`, `width_mm`, `depth_mm`, `length_mm`, `diameter_mm`, `n_teeth`, `n_bolts`, `bolt_circle_r_mm`, `bolt_dia_mm`, `wall_mm`, `material`, `part_type`
  - `merge_spec_into_plan(spec, plan) -> dict` — merges spec into `plan["params"]` without overwriting existing non-None values
  - Part type keywords: ratchet_ring, brake_drum, cam_collar, rope_guide, catch_pawl, pulley, flange, spacer, bracket, housing, spool, shaft, cam, pin, **lre_nozzle** (nozzle/rocket) (longest match wins)
  - Material keywords: specific grades (`6061`→`aluminium_6061`, `7075`→`aluminium_7075`) checked before generic (`aluminium`, `steel`)
  - Additional patterns (2026-03): `"OD 50mm"` (space only), `"50mm outer"`, `"outer dia 50mm"`, `"diameter of 50mm"`, `"bore 50mm"` (space only); WxHxD box notation `"50x100x200mm"`; radius→diameter conversion; combined `"4xM8"` bolt shorthand sets both `n_bolts` and `bolt_dia_mm` simultaneously; `"4 holes"` → `n_bolts`
- `aria_os/multi_cad_router.py` — `CADRouter.route(goal, spec=None, *, dry_run=False)`: when `spec=None`, auto-extracts via `spec_extractor.extract_spec(goal)`; always includes `spec` key in returned dict.

### CEM (Computational Engineering Model) physics
Multi-domain CEM pipeline added as of 2026-03:

```
goal → cem_registry.resolve_cem_module() → "cem_aria" | "cem_lre" | ...
      → module.compute_*() → physics-derived geometry dict
      → cem_to_geometry.py → deterministic CadQuery (NO LLM in this path)
      → aria_os/cem_checks.py → SF ≥ 2.0 required to pass
```

Key files:
- `cem_registry.py` — maps goal keywords to CEM module names; **register new domains here** (current: `aria`, `lre`/`nozzle`/`rocket`/`turbopump`/`injector`)
- `cem_core.py` — base `Material` and `Fluid` classes; pre-defined materials (X1 420i, Inconel 718, 6061 Al) and fluids (LOX, kerosene, IPA) — import from here, never redefine
- `cem_aria.py` — thin shim that re-exports `aria_cem.py` (avoids shadowing by `aria_cem/` package)
- `cem_lre.py` — standalone LRE (liquid rocket engine) CEM module; `compute_lre_nozzle()` derives nozzle geometry from thrust + chamber pressure
- `cem_to_geometry.py` — CEM scalars → CadQuery scripts (deterministic, no LLM)
- `aria_os/cem_context.py` — loads live CEM geometry from `cem_design_history.json` for LLM prompt injection
- `aria_os/cem_checks.py` — per-part static + dynamic physics checks; SF < 1.5 = hard fail, 1.5–2.0 = warning

### API server (`aria_os/api_server.py`)
FastAPI server for the CAD pipeline (Item 5):
- `POST /api/generate` — accepts `{description, dry_run}`. Pydantic validates: empty/whitespace → 422, < 4 chars after strip → 422. Calls orchestrator; logs `description→backend→validation_passed→file_sizes` per run.
- `GET /api/health` — reports `available` + metadata for all 4 backends (cadquery, grasshopper, blender, fusion360).
- `GET /api/runs?limit=N` — returns last N run log entries from `_RUN_LOG`.
- `_append_run(entry)` — appends to in-memory `_RUN_LOG` and optionally to JSON file at `_LOG_PATH`.
- Run with: `uvicorn aria_os.api_server:app`

### Context & constants
- `context/aria_mechanical.md` — **single source of truth for all geometry constants** (never hardcode dims)
- `context/aria_failures.md` — **read before any CAD work**; known Fusion/CadQuery failure patterns
- `aria_os/context_loader.py` — loads all `context/*.md` into a dict injected into every LLM prompt

---

## Architecture: Firmware

Two fully independent layers. Safety layer operates with zero dependency on intelligence layer.

- `firmware/stm32/aria_main.cpp` — state machine, brake GPIO, VESC UART, PID tension loop, UART command handler
- `firmware/stm32/safety.cpp` — watchdog, fault recovery, power-on safety boot sequence
- `firmware/esp32/aria_esp32_firmware.ino` — voice (Edge Impulse), CV, BLE, UART bridge to STM32
- `aria_models/state_machine.py` — Python state machine that **must mirror STM32 exactly**
- `tools/aria_constants_sync.py` — verifies constants match between `aria_simulator.py` and `aria_main.cpp`

**Critical constants** (must stay in sync across `aria_main.cpp`, `aria_models/state_machine.py`, `tools/aria_simulator.py`):
```python
TENSION_BASELINE_N = 40.0       # PID target during CLIMBING
TENSION_TAKE_THRESHOLD_N = 200.0
TENSION_FALL_THRESHOLD_N = 400.0
VOICE_CONFIDENCE_MIN = 0.85
ROPE_SPEED_FALL_MS = 2.0
```

**PID gains — two separate sets (do not conflate):**
- `tools/aria_simulator.py`: `PID_KP=2.5, PID_KI=0.8, PID_KD=0.1` — normalized simulation gains (PID output ±100, not volts). **Simulator only.**
- `tools/aria_constants_sync.py` → firmware: `tensionPID_kp=0.022, ki=0.413, kd=0.0005` — hardware-validated gains from `aria_pid_tuner` (PID output 0–10V, safe for 360N max error). Marked `NEVER_PATCH`; update only after PID re-tuning on hardware.

**Firmware status:** `firmware/stm32/` and `firmware/esp32/` files are null-byte stubs (hardware not yet arrived). Write firmware content here when hardware is in hand.

Fail-safe principle: ESP32 crash → STM32 holds tension. STM32/VESC fault → brake + centrifugal clutch. Power cut → power-off brake + clutch.

---

## CAD Rules (mandatory)

1. **All geometry constants** come from `context/aria_mechanical.md`. Never hardcode.
2. **Fusion 360 scripts**: Direct Design mode only (force at script start). Build solid box → cut interior → features on existing faces. Never annular profile extrusion on first operation (known failure).
3. **CadQuery**: Solid first, then cuts/holes. Select faces by direction (`faces(">Z")`), never by index. Print `BBOX:x,y,z` at end for validation.
4. **No fillets/chamfers on first attempt** — add only after the solid shape validates cleanly.
5. **Bbox axis orientation**: CadQuery extrudes along Z. Verify expected bbox axes match extrude direction.
6. **CEM geometry path** (`cem_to_geometry.py`) must never call an LLM — deterministic only.
7. When adding a new CEM domain, add its keyword mapping to `cem_registry.py`.

### Known CadQuery failure patterns
| Error | Cause | Fix |
|---|---|---|
| `ChFi3d_Builder: only 2 faces` | Fillet on thin body | Remove fillet; add after solid validates |
| `BRep_API: command not done` | Invalid face refs in compound boolean | Simplify to extrude + cut only |
| `Nothing to loft` | Non-coplanar loft profiles | Use revolve for axisymmetric profiles |
| Bbox axis mismatch | CadQuery Z vs expected height | Specify extrude direction; verify plan |

---

## Output Paths

| Path | Contents | Git tracked? |
|---|---|---|
| `outputs/cad/meta/` | Dimension JSON per part | Yes — source of truth |
| `outputs/cad/step/` | STEP files | No — regenerable |
| `outputs/cad/stl/` | STL files | No — regenerable |
| `outputs/cad/generated_code/` | Raw LLM CadQuery scripts | No |
| `outputs/cad/grasshopper/<part>/` | Grasshopper params.json + script | Yes |
| `outputs/cad/learning_log.json` | Attempt outcomes (success/fail + error) | Yes |
| `outputs/aria_generation_log.json` | GH pipeline runs with CEM SF values + STEP/STL paths | No |
| `cem_design_history.json` | Latest CEM parameter snapshots (used by LLM prompt injection) | No |
| `sessions/` | Agent session logs | Yes |

---

## Dashboard CEM Tab (`aria_cem_tab.py`)

`render_cem_tab()` is a Streamlit tab for live parameter tuning → CSV generation for Fusion 360 import. To wire it into `aria_dashboard.py`:

```python
from aria_cem_tab import render_cem_tab
# Add "CEM Design (physics-derived geometry)" to the sidebar setups list
# Route: elif setup.startswith("CEM Design"): render_cem_tab()
```

The tab exports 5 CSV profiles: energy absorber, motor mount, one-way bearing seat, rope guide, wall bracket.

---

## Session Logging

After every run, append to `sessions/YYYY-MM-DD_task.md`:
```
## Session TIMESTAMP
**Status:** Success | Failure
**Goal:** <goal string>
**Attempts:** N
**Output STEP:** <path>    # if success
**Diagnosis:** <error>     # if failure, also update context/aria_failures.md
```

On failure after 3 attempts: write diagnosis to sessions/, stop, do not ask user unless stuck.
