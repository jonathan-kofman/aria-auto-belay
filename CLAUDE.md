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

# Full pipeline: generate + FEA + GD&T drawing + PNG render + CAM script + setup sheet
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD" --machine "HAAS VF2"  # optional machine override

# List all generated parts with validation status, CEM SF, git SHA, generated-at
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

# Assembly from JSON config (runs post-assembly clearance check automatically)
python run_aria_os.py --assemble assembly_configs/aria_clutch_assembly.json
# Generate Fusion 360 constrained assembly script (auto-joints from proximity + part names)
python run_aria_os.py --constrain assembly_configs/clock_gear_train.json [--proximity 50]

# Print-fit scaling check
python run_aria_os.py --print-scale aria_ratchet_ring --scale 0.75

# Generate from a photo (vision AI extracts goal, then runs pipeline)
python run_aria_os.py --image photo.jpg
python run_aria_os.py --image photo.jpg "it's a bracket"   # optional hint

# Preview generated model in 3D browser before export
python run_aria_os.py --preview "ARIA ratchet ring, 213mm OD"
# Opens Three.js STL viewer in browser; choose export format in terminal:
#   [1] step  [2] stl  [3] both (default)  [4] skip

# Generate a GD&T engineering drawing SVG from any STEP file
python run_aria_os.py --draw outputs/cad/step/aria_spool.step
# → outputs/drawings/aria_spool.svg

# Generate Fusion 360 CAM script from a STEP file
python run_aria_os.py --cam outputs/cad/step/aria_housing.step --material aluminium_6061

# Run machinability check on a STEP file (undercut detection, axis classification)
python run_aria_os.py --cam-validate outputs/cad/step/aria_housing.step [--retries 2]
# → exits 0 on pass, 1 on fail; machinability.json written by validator

# Generate CNC operator setup sheet (markdown + JSON) from STEP + CAM script
python run_aria_os.py --setup outputs/cad/step/aria_housing.step outputs/cam/aria_housing/aria_housing_cam.py [--material aluminium_6061]
# → outputs/cam/<part>/setup_sheet.md
# → outputs/cam/<part>/setup_sheet.json  (validates against contracts/cam_setup_schema_v1.json)

# Generate civil engineering DXF (headless, state-specific standards)
python run_aria_os.py --autocad "drainage plan" --state TX --discipline drainage
# → outputs/cad/dxf/<slug>.dxf  +  <slug>.json (standards applied, metadata)
# Disciplines: transportation, drainage, grading, utilities, site
# State: 2-letter code (TX, CA, NY, etc.) or omit for AASHTO national defaults
python run_aria_os.py --autocad "road plan for subdivision" --state CO
python run_aria_os.py --autocad "storm sewer layout" --state FL --out outputs/cad/dxf/project1/

# Generate KiCad PCB script from a board description
python run_aria_os.py --ecad "ARIA ESP32 board, 80x60mm, 12V, UART, BLE, HX711"
# → outputs/ecad/<board_name>/<board_name>_pcbnew.py  (run in KiCad scripting console)
# → outputs/ecad/<board_name>/<board_name>_bom.json   (validates against contracts/ecad_bom_schema_v1.json)

# Run ECAD variant study (compare multiple board configurations)
python run_aria_os.py --ecad-variants "ARIA ESP32 board, 80x60mm" --variants variants/aria_board_variants.json
# → outputs/ecad/<board_slug>/variant_study.json

# Run FEA or CFD on a specific STEP file
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step [--fea|--cfd|--auto]

# Render PNG preview of any STL
python run_aria_os.py "part goal" --render
# → outputs/screenshots/<part_slug>.png

# Scenario: interpret real-world situation → decompose → generate all parts (with CEM checks)
python run_aria_os.py --scenario "a climber takes a lead fall on a 15m route"
python run_aria_os.py --scenario-dry-run "..."
python run_aria_os.py --scenario "..." --auto-confirm

# System: two-pass whole-machine design (subsystems → parts → generate all + CEM checks)
python run_aria_os.py --system "design a desktop CNC router 300x300x100mm"
python run_aria_os.py --system-dry-run "design a 6-DOF robot arm, 1kg payload"
```

### Batch generation
```bash
python batch.py parts/clock_parts.json
python batch.py parts/f1_2026_parts.json --skip-existing
python batch.py parts/clock_parts.json --only "escape" --workers 4
python batch.py parts/clock_parts.json --render           # PNG preview per part → outputs/screenshots/
python batch.py parts/clock_parts.json --verify-mesh      # gear module compatibility
```

### Assembly
```bash
python assemble.py assembly_configs/clock_gear_train.json
python assemble.py assembly_configs/clock_gear_train.json --no-clearance   # skip clearance check
# Parametric assembly: add "depends_on": "parent_id", "offset": [x,y,z] to any part in the JSON

python assemble_constrain.py assembly_configs/clock_gear_train.json        # generates Fusion constrained script
python assemble_constrain.py assembly_configs/f1_2026.json --proximity 80
```

### Dashboard
```bash
# Windows (sets up .python/ local env automatically)
scripts/START_DASHBOARD.bat

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

# CAD pipeline test suite (all headless):
python -m pytest tests/ -q
#  tests/test_grasshopper_scripts.py — GH RhinoCommon script validity
#  tests/test_post_gen_validator.py  — validation loop, STEP/STL quality, repair
#  tests/test_cad_router.py          — multi-backend routing + 14-template smoke tests
#  tests/test_spec_extractor.py      — structured spec extraction (40 tests)
#  tests/test_api_server.py          — FastAPI server: 422 validation, health, runs log
#  tests/test_e2e_pipeline.py        — 5 diverse descriptions, one per backend:
#      cadquery (bracket, ratchet ring) — router + script generation assertions
#      grasshopper (cam collar)        — GH component + CQ fallback artifact write
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
npx expo start          # JS-only preview via Expo Go (no BLE)

# EAS cloud build (no local Android SDK required)
npm install -g eas-cli
eas build --profile development --platform android
```

**App architecture** (`aria-climb/src/`):
- `store/authStore.ts` — Zustand: `user`, `isLoading`, `pendingRoleSelect`, `isGymMode`, `signOut`
- `store/bleStore.ts` — BLE scan state, discovered devices, connection, per-device telemetry
- `store/alertStore.ts` / `store/sessionStore.ts` — alert list + session list
- `services/ble/bleManager.ts` — scan, connect, notify subscribe, auto-reconnect with backoff
- `services/ble/bleCharacteristics.ts` — ARIA BLE service UUID + TELEMETRY/COMMAND/STATUS characteristic UUIDs
- `services/ble/bleProvisioning.ts` — gym owner provisioning: scan → send WiFi+gym config → reboot
- `services/ble/bleProvisioningVerifier.ts` — poll Firestore until device comes online post-provision
- `services/firebase/ariaDevice.ts` — `getGymDevice`, `subscribeToAllGymDevices`, `issueCommand`
- `services/firebase/incidents.ts` — `subscribeToIncidents`, `resolveIncident`
- `services/firebase/sessions.ts` — `subscribeToSessions`, `saveSession`
- `hooks/useARIADevice.ts` — unified hook: `useARIADevice(deviceId)` for BLE; `useARIADevice(gymId, deviceId)` for Firestore+BLE
- `hooks/useGymDevices.ts` — subscribe to all devices for a gym
- `screens/climber/GymOnboardingScreen.tsx` — QR scan → BLE pair → navigate to live session
- `screens/climber/LiveSessionScreen.tsx` — real-time tension bar, animated state badge, rope speed / current / battery
- `screens/auth/LoginScreen.tsx` / `SignupScreen.tsx` / `RoleSelectScreen.tsx` / `ClaimGymScreen.tsx` — full auth flow
- `screens/gym/DashboardScreen.tsx` — gym owner device overview
- `screens/gym/DeviceDetailScreen.tsx` / `DeviceHealthScreen.tsx` / `DeviceSettingsScreen.tsx` — per-device management
- `screens/gym/ProvisioningScreen.tsx` — guided BLE provisioning wizard
- `screens/gym/AlertHistoryScreen.tsx` / `SessionHistoryScreen.tsx` / `RouteManagementScreen.tsx` / `SafetyCameraTestScreen.tsx`
- `types/aria.ts` — `ARIAState`, `ARIATelemetry`, `ARIADevice`, `Incident`, `MaintenanceAction`, `COLLECTIONS`, physics constants
- `types/device.ts` — `FirestoreDevice`, `ARIAAdvertisedDevice`, `ProvisioningStatus`
- `utils/blePacketParser.ts` — 20-byte binary BLE packet parser with XOR checksum
- `locales/` — i18n strings: en, de, es, fr, ja

**To get BLE working:** native build only (`expo run:android` or EAS). Expo Go does not support `react-native-ble-plx`.
**Firebase:** add `google-services.json` to `aria-climb/android/app/` before first build.

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
- `aria_os/tool_router.py` — routes to `cadquery` / `fusion` / `grasshopper` / `blender` based on goal keywords and `part_id`. `CADQUERY_KEYWORDS` includes `"nozzle"`, `"rocket"`, `"lre"`, `"liquid rocket"`, `"turbopump"`, `"injector"` so LRE parts route to CadQuery headless instead of Grasshopper. `GRASSHOPPER_PART_IDS` covers 6 core ARIA parts: `aria_cam_collar`, `aria_spool`, `aria_housing`, `aria_ratchet_ring`, `aria_brake_drum`, `aria_rope_guide`.
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

### Physics analysis (`aria_os/physics_analyzer.py`)
FEA + CFD on generated STEP files. Called automatically after generation (prompt) or via `--analyze-part` / `--fea` / `--cfd` flags.
- **FEA**: beam bending, thick-cylinder hoop stress, gear tooth bending, plate bending, bolt circle shear
- **CFD**: pipe flow (Darcy-Weisbach), nozzle flow (isentropic, mach, thrust), heat transfer, drag estimate
- Returns SF, pass/fail, warnings. SF < 1.5 = hard fail.

### CAM generation (`aria_os/cam_generator.py`)
Reads STEP geometry → selects tools from `tools/fusion_tool_library.json` → computes SFM-based feeds/speeds → writes complete Fusion 360 Python CAM script.
- Tool selection: largest endmill ≤ min_feature_mm AND ≤ max_dim×0.4; fallback = smallest available
- Materials: `aluminium_6061` (SFM=300), `aluminium_7075` (SFM=260), `x1_420i` (SFM=85), `inconel_718` (SFM=40), `steel_4140` (SFM=90), `pla`, `abs`
- Operations: 3D Adaptive Clearing → Parallel Finish → Contour → Drill cycles
- Run in Fusion: Tools → Scripts → add generated `.py` → Run
- Returns `Path` to written script — callers must not cast to `str` before using `.parent`

### CAM validation (`aria_os/cam_validator.py`)
Machinability checks on generated STEP files.
- `check_machinability(step_path)` — runs radii, cavity depth, thin wall, undercut checks → writes `outputs/cam/<part>/machinability.json`
- `check_undercuts(step_path)` — OCC face-normal analysis against 6 cardinal directions
- `classify_machining_axes(undercut_results)` → `["3axis"]` / `["4axis"]` / `["5axis"]`
- `run_machinability_check()` — backward-compat wrapper (copies `failures` → `violations`)

### CAM setup sheet (`aria_os/cam_setup.py`)
Generates operator-facing setup sheet from STEP + CAM script.
- `write_setup_sheet(step_path, cam_script_path, material, out_dir, part_id, machine_name)` → writes `setup_sheet.md` + `setup_sheet.json`
- `detect_second_op(step_path)` — bottom face area analysis; flags flip requirement
- `suggest_fixturing(bbox_mm)` — returns vise / fixture plate / V-block recommendation
- `CAM_SETUP_SCHEMA_VERSION = "1.0"` — injected as `"schema_version"` first key in JSON
- `stock_dims` falls back to `{"x_mm": 0.1, "y_mm": 0.1, "z_mm": 0.1}` when no STEP exists (keeps JSON schema-valid)

### CAM physics (`aria_os/cam_physics.py`)
- `get_machine_profile(name)` → Tormach 1100 (1.5 kW / 10 Nm) or HAAS VF2 (22 kW / 122 Nm); key is `max_spindle_power_w`
- `validate_feeds_speeds(tool_dia_mm, material, depth_of_cut_mm, width_of_cut_mm, overhang_mm, spindle_power_w=1500)` → MRR, required power, Ra, deflection, `passed`

### Civil engineering AutoCAD/DXF generation (`aria_os/autocad/`)
Headless DXF generation for all civil engineering disciplines. No AutoCAD needed — uses ezdxf.
- **Entry point**: `generate_civil_dxf(description, state, discipline, output_path)` → writes `.dxf` + `.json` sidecar
- **`aria_os/autocad/__init__.py`** — exports `generate_civil_dxf`, `generate_all_disciplines`, layer/standards helpers
- **`aria_os/autocad/layer_manager.py`** — `LAYER_DEFS` (50+ layers, NCS-compliant), `DISCIPLINE_LAYERS`, `get_layer()`
- **`aria_os/autocad/standards_library.py`** — `get_standard(state, discipline)` deep-merges AASHTO 7th Ed. national defaults with all 50-state DOT overrides; covers roads, drainage, grading, structural, ada
- **`aria_os/autocad/civil_elements.py`** — ezdxf entity builders for roads, drainage, grading, utilities, survey, site, structural, annotation
- **`aria_os/autocad/dxf_exporter.py`** — main DXF writer; calls `get_standard()` then discipline-specific plan generator; writes JSON sidecar with standards applied
- **`aria_os/generators/autocad_generator.py`** — orchestrator-compatible `generate_autocad(plan, step_path, stl_path, repo_root)` entry point
- **`cem/cem_civil.py`** — civil CEM: Manning's pipe sizing, Bishop slope stability, retaining wall Coulomb analysis, rational method; `compute_for_goal()` returns SF values + geometry params
- **Tool routing**: `AUTOCAD_KEYWORDS` in `tool_router.py` routes "road plan", "drainage plan", "grading plan", "site plan", "dxf", "autocad", etc. → "autocad" backend (highest priority, checked before CadQuery)
- **State standards**: frost depth, seismic category, wind speed, min pipe cover — all 50 states + DC in `_STATE_OVERRIDES`
- **Output**: `outputs/cad/dxf/<slug>.dxf` + `<slug>.json`

### ECAD generation (`aria_os/ecad_generator.py`)
Generates KiCad pcbnew Python script from board description (no LLM, keyword matching).
- Extracts board dims (`80x60mm` pattern), selects components (ESP32, STM32, barrel jack, JST connectors, HX711, VESC, etc.)
- `extract_firmware_pins(repo_root)` scrapes `#define PIN_*` and `const int *PIN*` from STM32/ESP32 firmware — injects into pcbnew script + BOM
- `ECAD_BOM_SCHEMA_VERSION = "1.0"` — injected as `"schema_version"` first key in BOM JSON
- Outputs: `<board_name>_pcbnew.py` (run in KiCad scripting console) + `<board_name>_bom.json` + `validation.json`
- Retry loop (max 2): on ERC errors with LLM available, rebuilds component list with failure context injected

### ECAD variant runner (`aria_os/ecad_variant_runner.py`)
- `run_variant_study(base_description, variants, repo_root)` — generates and validates multiple board configs
- `print_variant_table(results)` — ASCII table (ERC/DRC pass, power draw mA, cost $)
- `save_variant_study(results, board_slug, repo_root)` → `outputs/ecad/<board>/variant_study.json`

### Output contracts (`contracts/`)
All structured JSON outputs carry `"schema_version"` as first key and validate against JSON Schema (draft 2020-12) files in `contracts/`.
- `contracts/cam_setup_schema_v1.json` — `setup_sheet.json` schema (fields, types, units)
- `contracts/ecad_bom_schema_v1.json` — BOM JSON schema (components, firmware_pins, validation block)
- Test coverage: `tests/test_output_contracts.py` — 20 tests (unit schema checks + integration round-trips)

### GD&T drawing generator (`aria_os/drawing_generator.py`)
Generates A3 landscape SVG engineering drawings with 3 orthographic views, dimension annotations, GD&T symbols, title block.
- Called interactively after each generation (y/N prompt), or silently via `auto_draw=True` in `orchestrator.run()`, or via `--draw` / `--full` flags.

### Clearance checker (`aria_os/clearance_checker.py`)
Post-assembly interpenetration and tight-clearance check using trimesh.
- `check_clearance(parts, min_clearance_mm=0.5)` — loads each part's STL, applies position transforms, checks proximity between pairs within 100mm
- Returns `{pairs, violations, passed}` with `"ok"` / `"tight"` / `"interpenetrating"` per pair
- Runs automatically after `assemble.py`; skip with `--no-clearance`

### Validation & export
- `aria_os/validator.py` — bbox check, STEP re-import (solid count ≥ 1), mesh integrity, housing spec
- `aria_os/exporter.py` — STEP + STL export; output paths under `outputs/cad/`
- `aria_os/cad_learner.py` — records every attempt outcome to `outputs/cad/learning_log.json`
- **Version tracking**: orchestrator writes `outputs/cad/meta/<part_id>.json` after every generation with: goal, params, CEM SF, bbox, cad_tool, generated_at, git_sha. `--list` shows SHA + generated-at + `[STALE]` flag if STEP is newer than meta.
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
- `aria_os/multi_cad_router.py` — `CADRouter.route(goal, spec=None, *, dry_run=False)` (**class method, not instance method**): when `spec=None`, auto-extracts via `spec_extractor.extract_spec(goal)`; always includes `spec` key in returned dict. Orchestrator calls `CADRouter.route(goal)` directly — never instantiate `CADRouter()`.

### CEM (Computational Engineering Model) physics
Multi-domain CEM pipeline added as of 2026-03:

```
goal → cem_registry.resolve_cem_module() → "cem_aria" | "cem_lre" | ...
      → module.compute_*() → physics-derived geometry dict
      → cem_to_geometry.py → deterministic CadQuery (NO LLM in this path)
      → aria_os/cem_checks.py → SF ≥ 2.0 required to pass
```

Key files:
- `cem/cem_registry.py` — maps goal keywords to CEM module names; **register new domains here** (current: `aria`, `lre`/`nozzle`/`rocket`/`turbopump`/`injector`). `resolve_cem_module(goal, part_id)` returns module name or `None`.
- `cem/cem_core.py` — base `Material` and `Fluid` classes; pre-defined materials (X1 420i, Inconel 718, 6061 Al) and fluids (LOX, kerosene, IPA) — import from here, never redefine
- `cem/cem_aria.py` — thin shim that re-exports `aria_cem.py` (avoids shadowing by `aria_cem/` package). `compute_for_goal(goal, params)` entry point used by the orchestrator.
- `cem/cem_lre.py` — standalone LRE (liquid rocket engine) CEM module; `compute_lre_nozzle(LREInputs)` derives nozzle geometry from thrust + chamber pressure. `compute_for_goal(goal, params)` entry point. Supports LOX/RP-1, LOX/LH2, LOX/IPA, N2O4/UDMH propellants.
- `cem/cem_to_geometry.py` — CEM scalars → CadQuery scripts (deterministic, no LLM). `scalars_to_cq_script(part_id, params)` dispatches to per-part templates for: `aria_ratchet_ring`, `aria_brake_drum`, `aria_spool`, `aria_housing`, `aria_cam_collar`, `aria_rope_guide`, `lre_nozzle`. `write_cq_script(part_id, params, path)` writes to disk.

Note: backward-compat shims remain at the original root paths (`cem_registry.py`, `cem_core.py`, etc.) so all existing imports continue to work.
- `aria_os/cem_context.py` — loads live CEM geometry from `cem_design_history.json` for LLM prompt injection
- `aria_os/cem_checks.py` — per-part static + dynamic physics checks; SF < 1.5 = hard fail, 1.5–2.0 = warning. `_run_cem_system_check` calls `compute_for_goal()` on the resolved CEM module (fixed 2026-03 — previously called non-existent `ARIAModule` class).
- `aria_os/cem_generator.py` — `resolve_and_compute(goal, part_id, params, repo_root)` — the orchestrator entry point; resolves CEM module via registry then calls `compute_for_goal()`.

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

**Firmware status:** All firmware files are implemented (merged 2026-03-27 from cursor/development-environment-setup branch). Hardware not yet arrived — untested on real hardware.
- `firmware/stm32/aria_main.cpp` — 524 lines: SimpleFOC motor control, HX711 load cell, state machine, PID tension loop. First-time setup: flash → serial `"cal"` → copy HX711_OFFSET/HX711_SCALE → reflash.
- `firmware/stm32/safety.cpp` — 404 lines: watchdog, fault recovery, power-on boot sequence.
- `firmware/esp32/aria_wearable/aria_wearable.ino` — wearable companion firmware (BLE to phone).

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
| `outputs/cad/meta/` | Version-tracked JSON per part: goal, params, CEM SF, bbox, git SHA, generated_at | Yes — source of truth |
| `outputs/cad/step/` | STEP files | No — regenerable |
| `outputs/cad/stl/` | STL files | No — regenerable |
| `outputs/cad/generated_code/` | Raw LLM CadQuery scripts | No |
| `outputs/cad/grasshopper/<part>/` | Grasshopper params.json + script | Yes |
| `outputs/cad/dxf/` | Civil engineering DXF files + JSON sidecar (state + standards applied) | No |
| `outputs/cad/learning_log.json` | Attempt outcomes (success/fail + error) | Yes |
| `outputs/cam/<part>/` | Fusion 360 CAM script + CAM summary JSON + `setup_sheet.md` + `setup_sheet.json` + `machinability.json` | No |
| `outputs/drawings/` | GD&T engineering drawing SVGs | No |
| `outputs/ecad/<board>/` | KiCad pcbnew script + BOM JSON + `validation.json` + `variant_study.json` | No |
| `outputs/screenshots/` | PNG renders of STL files (via `--render` or `batch.py --render`) | No |
| `outputs/aria_generation_log.json` | GH pipeline runs with CEM SF values + STEP/STL paths | No |
| `outputs/api_run_log.json` | API server run log (persisted from `_RUN_LOG`, last 500 entries) | No |
| `cem_design_history.json` | Latest CEM parameter snapshots (used by LLM prompt injection) | No |
| `contracts/cam_setup_schema_v1.json` | JSON Schema for `setup_sheet.json` (all fields, types, units) | Yes |
| `contracts/ecad_bom_schema_v1.json` | JSON Schema for `<board>_bom.json` | Yes |
| `sessions/` | Agent session logs | Yes |

---

## Dashboard CEM Tab (`dashboard/aria_cem_tab.py`)

`render_cem_tab()` is a Streamlit tab for live parameter tuning → CSV generation for Fusion 360 import. To wire it into `aria_dashboard.py`:

```python
from dashboard.aria_cem_tab import render_cem_tab
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
