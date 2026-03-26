# ARIA Cross-Domain Integration Check
**Date:** 2026-03-26
**Status:** Issues Found (6 findings, 2 critical)

---

## 1. Constants Synchronization

### Tool output
`python tools/aria_constants_sync.py` reports **0 mismatches, 17 not-found** in firmware.
This is expected: firmware files (`firmware/stm32/aria_main.cpp`) are null-byte stubs (hardware not yet arrived).

### Manual cross-file verification

| Constant | CLAUDE.md | `tools/aria_simulator.py` | `state_machine.py` (root) | `aria_models/state_machine.py` | `tools/aria_constants_sync.py` | Status |
|---|---|---|---|---|---|---|
| TENSION_BASELINE_N (40.0) | 40.0 | 40.0 (`TENSION_BASELINE_N`) | 40.0 (`TENSION_TARGET_N`) | hardcoded in comments only | 40.0 (`TENSION_TARGET_N`) | OK (naming differs) |
| TENSION_TAKE_THRESHOLD_N (200.0) | 200.0 | 200.0 | 200.0 (`TENSION_TAKE_CONFIRM_N`) | 200 (literal, line 67) | 200.0 (`TENSION_TAKE_CONFIRM_N`) | OK |
| TENSION_FALL_THRESHOLD_N (400.0) | 400.0 | 400.0 | not present | not present | not present | **WARN** -- only in simulator |
| VOICE_CONFIDENCE_MIN (0.85) | 0.85 | 0.85 | 0.85 | not present (no threshold) | 0.85 | OK (absent from aria_models/) |
| ROPE_SPEED_FALL_MS (2.0) | 2.0 | 2.0 | not present | not present | not present | **WARN** -- only in simulator |

### CRITICAL FINDING 1: WATCH_ME tension target mismatch

| Source | Value | Variable |
|---|---|---|
| `tools/aria_simulator.py` | **25.0 N** | `TENSION_WATCH_ME_N` |
| `state_machine.py` (root) | **60.0 N** | `TENSION_TIGHT_N` |
| `tools/aria_constants_sync.py` | **60.0 N** | `TENSION_TIGHT_N` |
| `sessions/2026-03-10_firmware-audit.md` | **25.0 N** | `T_WATCH_ME` (tunable) |

The simulator uses 25 N for WATCH_ME mode but the authoritative state machine and constants sync tool both specify 60 N. This is a 2.4x discrepancy that will cause the simulator to behave differently from real firmware. The 60 N value should be canonical; the simulator needs to be updated.

### FINDING 2: `aria_models/state_machine.py` uses hardcoded literals

The file at `aria_models/state_machine.py` (the simple version) uses raw numeric literals (15, 200, 0.5) instead of named constants. The root `state_machine.py` (the authoritative version) properly defines all constants as named variables. The `aria_models/` version should either import from the root or define its own named constants for maintainability.

### FINDING 3: Two state machine files with different state sets

- `state_machine.py` (root): 9 states including `CLIMBING_PAUSED`
- `aria_models/state_machine.py`: 8 states, missing `CLIMBING_PAUSED`

These are not in sync. The root version is more complete and authoritative.

---

## 2. CEM <-> CAD Consistency

### Template dimensions vs `context/aria_mechanical.md`

| Part | Template Default | aria_mechanical.md | Match? |
|---|---|---|---|
| Ratchet ring OD | 213.0 mm | 213.0 mm (pocket dia) | OK |
| Ratchet ring thickness | 21.0 mm | 21.0 mm (pocket depth) | OK |
| Ratchet ring teeth | 24 | 24 | OK |
| Housing W x H x D | 700 x 680 x 344 mm | 700 x 680 x 344 mm | OK |
| Housing wall | 10.0 mm | 10.0 mm | OK |
| Spool diameter | 600.0 mm | 600.0 mm | OK |
| Spool hub OD | 47.2 mm | 47.2 mm (bearing OD) | OK |
| Brake drum OD | 200.0 mm | 200.0 mm | OK |
| Shaft diameter | 20.0 mm | 20.0 mm | OK |
| Cam collar OD | 55.0 mm | 55.0 mm (bearing shoulder OD) | OK |

All CadQuery template defaults correctly source from `aria_mechanical.md`. No hardcoded overrides found.

### CEM checks (`aria_os/cem_checks.py`) thresholds

- SF >= 2.0 pass threshold used for static checks (line 93: `sf >= 2.0`)
- Mechanical defaults loaded from context via `get_mechanical_constants()` -- correct delegation
- Yield values from `aria_models/static_tests.py`:
  - Pawl: 1800 MPa (A2 tool steel) -- reasonable for hardened tool steel
  - Ratchet: 1300 MPa (4140 QT) -- reasonable
  - Housing: 276 MPa (6061-T6) -- matches materials table
  - Shaft: 1000 MPa (4140 HT) -- matches materials table (`4140_ht` = 1000 MPa yield)

### FINDING 4: `gh_integration/` module referenced in CLAUDE.md does not exist

CLAUDE.md documents `aria_os/gh_integration/` with `gh_aria_parts.py` and `gh_to_step_bridge.py`, including per-part CEM SF thresholds (e.g., ratchet_ring tooth_shear SF >= 8.0). However, this directory does not exist in the codebase. The documented SF thresholds cannot be verified against implementation.

---

## 3. Assembly Interface Check

### `assembly_configs/aria_clutch_assembly.json`

**Dimensional consistency with aria_mechanical.md:**
- Ratchet ring at origin, 213mm OD, 21mm thick -- correct
- Cam collar at Z=21 (abutting ratchet ring rear face) -- geometrically sound
- Pawl levers at X=+/-106 (ratchet OD/2 = 106.5) -- 0.5mm offset, acceptable for engagement clearance

**FINDING 5: Duplicate part names in assembly**

The assembly has two sets of `pawl_lever_1` and `pawl_lever_2` entries:
1. Lines 97-123: `pawl_lever_1/2` referencing `llm_aria_pawl_lever_optimized_steel.step` at X=+/-106
2. Lines 201-228: `pawl_lever_1/2` referencing `llm_aria_pawl_lever_t6_aluminum.step` at X=+/-106.5

This creates ambiguity. They reference different STEP files (optimized steel vs T6 aluminum) and have slightly different positions. An assembler iterating over parts would create overlapping geometry. One set should be removed or renamed.

**Constraint integrity:**
- Coaxial constraints between ratchet_ring and cam_collar (Z-axis) -- correct, both cylindrical and concentric
- Face contact ratchet_ring >Z to cam_collar <Z -- correct, cam sits behind ratchet
- Face contact ratchet_ring >Z to pawl_lever 1/2 -- geometrically correct (pawls engage ring face)
- Coaxial constraints to bearing_retainer_front/rear -- correct

---

## 4. Pipeline Data Flow (`aria_os/orchestrator.py`)

### Session dict field population trace

| Stage | Fields Set | Verified |
|---|---|---|
| Init | `goal`, `attempts=0`, `step_path=""`, `stl_path=""` | OK |
| Plan | via `planner_plan()` -- `plan` dict separate from session | OK |
| Spec extract | `_spec` dict merged into `plan["params"]` | OK |
| CEM inject | `plan["cem_context"]` set if CEM resolves | OK |
| Route | `session["cad_tool"]`, `session["cad_route"]`, `session["engineering_brief"]` | OK |
| Generate (CQ) | `session["step_path"]`, `session["stl_path"]`, `session["bbox"]`, `session["script_path"]` | OK |
| Generate (GH) | `session["script_path"]` | OK |
| Generate (Fusion) | `session["script_path"]` | OK |
| Validation loop | `session["validation"]` with geo/vis/quality/attempts/status/validation_failures | OK |
| Quality check | `session["output_quality"]` | OK |
| CEM check | `session["cem"]` with passed/summary/static_min_sf/static_failure_mode | OK |
| Learning log | `record_attempt()` called with all derived values | OK |
| Completion | `session["automation_artifacts"]`, `session["attempts"]=1` | OK |

**Data flow is complete.** All required fields are populated at each stage. The `_passed` derivation (line 439) correctly combines validation status, CEM result, and output quality.

**Note:** `session["attempts"]` is hardcoded to 1 at line 371, regardless of actual retry count during CQ/GH generation. The internal retry count is not surfaced to the session dict (the validation loop's attempt count IS recorded in `session["validation"]["attempts"]` but the generation retry count is lost).

---

## 5. Material Constants

### `context/aria_materials.md` vs `cem_core.py`

| Material | Property | aria_materials.md | cem_core.py | Match? |
|---|---|---|---|---|
| 6061-T6 Al | yield_MPa | 276 | 276 | OK |
| 6061-T6 Al | ultimate_MPa | 310 | 310 | OK |
| 6061-T6 Al | density (kg/m3) | 2700 | 2700 | OK |
| Inconel 718 | yield_MPa | 1100 | **700** | **MISMATCH** |
| Inconel 718 | ultimate_MPa | 1375 | **900** | **MISMATCH** |
| Inconel 718 | density (kg/m3) | 8190 | **8220** | Minor (~0.4%) |

### CRITICAL FINDING 6: Inconel 718 yield strength mismatch

`cem_core.py` defines MATERIAL_INCONEL718 with `yield_strength_MPa=700` and `yield_at_temp_MPa=700`, representing the 700C (elevated temperature) de-rated value. The `context/aria_materials.md` lists 1100 MPa, which is the room-temperature value.

**Impact:** Any CEM calculation using `MATERIAL_INCONEL718` from `cem_core.py` will compute wall thicknesses ~57% thicker than necessary for room-temperature applications, or conversely, any design using the materials.md value for high-temperature service will be undersized. The two files serve different domains (cem_core.py targets LRE/rocket with hot gas paths; materials.md is a general reference), but a developer selecting "Inconel 718" without understanding the temperature context could get dangerous results.

**Recommendation:** Add a comment or separate entry in `aria_materials.md` for the elevated-temperature de-rated value, or add a room-temperature entry to `cem_core.py` so both conditions are explicitly available.

### Other materials in `cem_core.py` not in `aria_materials.md`

- `X1 420i` (420SS + Bronze sinter) -- not in materials table (specialized DMLS material)
- `Copper C18150` -- not in materials table (regen cooling liner material)

These are LRE-domain materials and their absence from the ARIA climbing device materials table is expected.

### `static_tests.py` yield values vs `aria_materials.md`

| Component | static_tests.py | aria_materials.md equivalent | Match? |
|---|---|---|---|
| Housing (6061-T6) | 276 MPa | 276 MPa (`6061_t6`) | OK |
| Shaft (4140 HT) | 1000 MPa | 1000 MPa (`4140_ht`) | OK |
| Ratchet (4140 QT) | 1300 MPa | not listed (QT variant) | N/A |
| Pawl (A2 tool steel) | 1800 MPa | not listed | N/A |

The ratchet ring uses 4140 QT (quench+temper to higher HRC than the HT variant), and pawls use A2 tool steel -- both are specialist heat treatments not in the general materials table. This is acceptable since they are safety-critical parts with specific metallurgical requirements.

---

## Summary of Findings

| # | Severity | Description | Files Affected |
|---|---|---|---|
| 1 | **CRITICAL** | WATCH_ME tension: simulator uses 25 N, authoritative state machine uses 60 N | `tools/aria_simulator.py` line 28 |
| 2 | LOW | `aria_models/state_machine.py` uses hardcoded literals instead of named constants | `aria_models/state_machine.py` |
| 3 | MEDIUM | Root `state_machine.py` has 9 states (includes CLIMBING_PAUSED); `aria_models/state_machine.py` has 8 | Both state machine files |
| 4 | LOW | `aria_os/gh_integration/` documented in CLAUDE.md but does not exist | CLAUDE.md |
| 5 | MEDIUM | Duplicate `pawl_lever_1/2` entries in assembly config with different materials and positions | `assembly_configs/aria_clutch_assembly.json` |
| 6 | **CRITICAL** | Inconel 718 yield: cem_core.py=700 MPa (hot), materials.md=1100 MPa (room temp) -- no cross-reference | `cem_core.py`, `context/aria_materials.md` |

### Passing checks
- All 5 critical constants (TENSION_BASELINE, TAKE_THRESHOLD, FALL_THRESHOLD, VOICE_CONFIDENCE, ROPE_SPEED_FALL) are consistent between CLAUDE.md and `tools/aria_simulator.py`
- All CadQuery template defaults match `context/aria_mechanical.md` geometry constants
- CEM checks correctly load mechanical defaults from context
- Pipeline session dict is fully populated at each stage
- 6061-T6 and 4140-HT material properties are consistent across all three sources
- Assembly mating constraints reference correct dimensions and faces
