# ARIA-OS ⇄ CEM Integration — 2026-03-09

## Scope
- Wire ARIA-OS CAD generation to existing physics models:
  - `aria_models/static_tests.py`
  - `aria_models/dynamic_drop.py`
  - `aria_cem.py` (CEM)
- Consolidate CEM-related constants into `context/`.
- Add a meta JSON channel from CAD to CEM.
- Implement `aria_os/cem_checks.py` and call it from `aria_os/orchestrator.py`.

---

## PHASE 1 — Constants into `context/`

**Done:**
- `context/aria_mechanical.md` extended with:
  - **Pawl Geometry** table (tip width, thickness, arm length, body height, engagement depth, `N_PAWLS`).
  - **Ratchet Geometry** table (pitch radius, face width, number of teeth, pressure angle, module).
  - **Shaft Geometry** table (shaft diameter, span).
- New `context/aria_materials.md` created with:
  - 6061‑T6 Aluminum properties (yield, ultimate, E, density) → maps to `YIELD_HOUSING_MPA`.
  - 4140 steel (yield, ultimate, E, density) → maps to `YIELD_SHAFT_MPA`.
  - Pawl material (hardened steel) → `YIELD_PAWL_MPA`, `YIELD_RATCHET_MPA`.
- New `context/aria_test_standards.md` created with:
  - ANSI/ASSA Z359.14 limits (8kN peak, 6kN avg, 813mm arrest, 16kN static, SF=2.0).
  - Default drop test parameters (`DEFAULT_MASS_KG`, `DEFAULT_DROP_HEIGHT_M`, `DEFAULT_TRIGGER_G`, `DEFAULT_ROPE_K`, absorber k/c/FMAX).

No code in the models has been re-pointed to this context yet; this is a documentation + future single‑source‑of‑truth step.

---

## PHASE 2 — Meta JSON emission from generated code

**Implementation:**
- `aria_os/llm_generator.py` system prompt updated so every LLM script is instructed to end with:
  - BBOX and STEP/STL export (unchanged), plus:
  - A **meta JSON block**:
    - Uses `PART_NAME`, `STEP_PATH`, and `bb` (bounding box).
    - Writes `outputs/cad/meta/<step_stem>.json` with structure:
      - `"part_name": PART_NAME`
      - `"bbox_mm": {"x": bb.xlen, "y": bb.ylen, "z": bb.zlen}`
      - `"dims_mm": {}` (placeholder for part‑specific dimensions).
- `aria_os/orchestrator.py` now injects `PART_NAME` into the execution namespace:
  - `inject = {"STEP_PATH": ..., "STL_PATH": ..., "PART_NAME": part_name}` for LLM parts.
- `aria_os/exporter.py` gained:
  - `get_meta_path(goal_or_part_id: str) -> str` returning:
    - `outputs/cad/meta/<goal_or_part_id_normalized>.json`

**Current limitation:**
- Because Anthropic is not available in the current Python environment, LLM‑based generation fails, so **no new meta JSON files were emitted in this run**.
- `outputs/cad/meta/` is currently empty.

---

## PHASE 3 — `aria_os/cem_checks.py`

**New module:** `aria_os/cem_checks.py`

### Core dataclass
- `CEMCheckResult`:
  - `part_id: str`
  - `static_passed: Optional[bool]`
  - `static_min_sf: Optional[float]`
  - `static_failure_mode: Optional[str]`
  - `dynamic_passed: Optional[bool]`
  - `dynamic_peak_force_N: Optional[float]`
  - `dynamic_arrest_dist_mm: Optional[float]`
  - `cem_passed: Optional[bool]`
  - `cem_warnings: list[str]`
  - `overall_passed: bool`
  - `summary: str`

### Static check integration (`static_tests.simulate_static_pawl`)
- Helper: `_run_static_checks(part_id, meta)`:
  - Applies to part_ids containing: `"pawl"`, `"lever"`, `"ratchet"`, `"ring"`, `"housing"`, `"shaft"`, `"spool"`, `"collar"`.
  - Loads meta JSON (if present) and looks for `meta["dims_mm"]` keys such as:
    - `"tip_width"`, `"engagement_depth"`, `"thickness"`, `"arm_length"`, `"body_height"`, `"wall_thickness"`, `"shaft_diameter"`, `"shaft_span"`.
  - Calls `simulate_static_pawl(load_steps=[2000,4000,8000,12000,16000], **overrides)` with:
    - Pawl overrides (if pawl/lever).
    - Housing wall thickness override (if housing).
    - Shaft overrides (if shaft/spool/collar).
  - Extracts:
    - `static_passed = df["passed"].all()`.
    - `static_min_sf = df["min_sf"].min()` (worst across loads).
    - `static_failure_mode` by looking at the highest‑load row and picking which of `sf_contact/sf_bending/sf_housing/sf_shaft` is minimum there.

### Dynamic drop integration (`dynamic_drop.simulate_drop_test`)
- Helper: `_run_dynamic_checks(part_id)`:
  - Applies only when `"housing"` is in `part_id.lower()`.
  - Calls `simulate_drop_test()` with defaults (from `dynamic_drop.py`).
  - Returns:
    - `dynamic_passed = summary["passed"]`
    - `dynamic_peak_force_N = summary["peak_force_N"]`
    - `dynamic_arrest_dist_mm = summary["arrest_distance_mm"]`

### System CEM integration (`aria_cem.ARIAModule`)
- Helper: `_run_cem_system_check()`:
  - Instantiates `ARIAInputs()` with defaults, `ARIAModule(inputs)`, runs `compute()` and `validate()`.
  - Returns:
    - `cem_passed = bool(ok)`
    - `cem_warnings = module.warnings`
  - In this run:
    - `validate: False`
    - `warnings: ['WARNING: Rope capacity 38.5m < required 40.0m']`

### Overall aggregation
- `run_cem_checks(part_id, meta_path, context) -> CEMCheckResult`:
  - Loads meta JSON (if present).
  - Runs `_run_static_checks`, `_run_dynamic_checks`, `_run_cem_system_check`.
  - Sets `overall_passed = True` unless any of `static_passed`, `dynamic_passed`, `cem_passed` is explicitly `False`.
  - Builds a human‑readable `summary`, e.g.:
    - `"Static PASS (min SF=3.20 @ sf_bending); Dynamic PASS (...); System CEM FAIL"`.

---

## PHASE 4 — Wiring into `orchestrator.py`

**Changes:**
- Imports:
  - `from .exporter import export, get_output_paths, get_meta_path`
  - `from . import cem_checks`
- LLM validation namespace now injects:
  - `{"STEP_PATH": ..., "STL_PATH": ..., "PART_NAME": part_name}`
- After geometry export, the orchestrator now runs:
  - `meta_path_str = get_meta_path(part_id or part_name, repo_root)`
  - `cem_result = cem_checks.run_cem_checks(part_id or part_name, Path(meta_path_str), context)`
  - Attaches to `session`:
    - `cem_overall_passed`
    - `cem_summary`
    - `cem_static_min_sf` (if available)
  - Prints:
    - `[CEM FAIL] ...` or `[CEM PASS] ...`
  - Any exceptions in CEM integration are caught and stored in `session["cem_error"]` so geometry pipeline never crashes because of CEM.

**Note:** Orchestrator does **not yet gate geometry saves on CEM failure**; CEM is advisory in this iteration. The `.cursorrules` section documents the intended future behavior (e.g. static SF < 1.5 as hard reject).

---

## PHASE 5 — Tests (Pawl, Ratchet, Housing)

### Environment constraints
- System `python 3.11.9` **does not** have:
  - `anthropic` (LLM generator dependency)
  - `cadquery` (CadQuery/STEP validation dependency)
- The previous `.venv` Python (`.venv/Scripts/python.exe`) is no longer found on disk from this environment.

This means:
- All **LLM‑routed parts** (`generate the ARIA pawl lever`, `generate the ARIA ratchet ring`) fail with:
  - `Generation failed: LLM generation failed: anthropic package required for LLM generation. Install with: pip install anthropic`
  - No new `.step/.stl` or meta JSON were generated for these tests in this environment.
- The **template‑routed housing shell** fails at the CadQuery import step:
  - `Diagnosis: No module named 'cadquery'`

### Direct model runs (without ARIA-OS pipeline)
To still exercise the physics:

1. **Static tests:**
   - Command:
     - `python -c "from aria_models import static_tests as st; print(st.simulate_static_pawl([2000,4000,8000,12000,16000]).to_string(index=False))"`
   - Output (excerpt):
     - At 16,000 N:
       - `sf_contact = 4.05`
       - `sf_bending = 3.63`
       - `sf_housing = 3.45`
       - `sf_shaft = 0.57`
       - `min_sf = 0.57`, `passed = False`
     - **Conclusion:** in the current static model, **shaft bending** is the critical mode; safety factor drops below 1.0 at full 16kN proof load.

2. **Dynamic drop:**
   - Command:
     - `python -c "from aria_models import dynamic_drop as dd; _, s = dd.simulate_drop_test(); print(s)"`
   - Output:
     - `{'arrest_distance_mm': 66.35, 'peak_force_N': 2470.96, 'avg_force_N': 2284.18, 'trigger_fired': True, 'absorber_activated': False, 'ansi_peak_limit_N': 8000.0, 'ansi_avg_limit_N': 6000.0, 'ansi_distance_limit_mm': 813.0, 'passed': True}`
     - **Conclusion:** with default parameters, **dynamic drop passes ANSI limits with large margin**.

3. **ARIA CEM:**
   - Command:
     - `python -c "from aria_cem import ARIAInputs, ARIAModule; m = ARIAModule(ARIAInputs()); g = m.compute(); ok = m.validate(); print('validate:', ok); print('warnings:', m.warnings)"`
   - Output:
     - `validate: False`
     - `warnings: ['WARNING: Rope capacity 38.5m < required 40.0m']`
   - **Conclusion:** current default CEM design fails the rope‑capacity check (38.5m vs 40m), but is otherwise structurally and dynamically within limits (per earlier `aria_cem.py` validation set).

### Meta JSON status
- Because LLM generation and CadQuery imports both failed in this environment:
  - **No new meta JSON files were written** under `outputs/cad/meta/`.
  - `cem_checks.run_cem_checks()` currently operates with **no meta** (it falls back to defaults).

---

## PHASE 6 — `.cursorrules` update

**Done:**
- `.cursorrules` now references:
  - `context/aria_materials.md` for yield/elastic properties.
  - `context/aria_test_standards.md` for ANSI limits and default drop parameters.
- Added **CEM Integration** section:
  - Documents policy:
    - Static SF < 1.5: hard failure (future).
    - Static SF 1.5–2.0: warning, outputs saved with flag.
    - Static SF ≥ 2.0: pass.
  - Notes that:
    - Meta JSON lives at `outputs/cad/meta/<part>.json`.

---

## Final Assessment — Is this integration giving meaningful engineering signal?

- **Yes, at the model level**:
  - `static_tests` clearly surfaces the shaft as the weak link at 16kN (SF≈0.57), which is actionable.
  - `dynamic_drop` shows comfortable margin vs ANSI dynamic limits with current absorber/rope parameters.
  - `aria_cem` encodes a full device‑level check and flags rope capacity shortfall directly.
- **Part-level ARIA-OS coupling is partially wired but not fully exercised**:
  - The **meta JSON emission path** is in place for LLM‑generated parts, but cannot be tested here due to missing `anthropic` and `cadquery` in the active interpreter.
  - `cem_checks.run_cem_checks()` is fully implemented and callable from `orchestrator.py`, but currently runs with **default geometry/material values**, not real dimensions extracted from meta JSON (because no meta exists yet).
- **Next steps to make the signal truly CAD‑driven:**
  - Restore a Python environment with both **`cadquery`** and **`anthropic`** available to ARIA-OS so LLM code + validation can run end‑to‑end.
  - Extend generated scripts (LLM or templates) to populate `dims_mm` in meta for pawl, ratchet, housing, and shaft so that:
    - `simulate_static_pawl()` runs with **actual geometry** from the part, not just defaults.
  - Optionally, refactor `aria_cem` and `static_tests` constants to read directly from the new `context/` files instead of internal literals.

In its current state, the CEM integration provides **real physics checks via `static_tests`, `dynamic_drop`, and `aria_cem`**, but they are still driven primarily by **assumed geometry** rather than dimensions extracted from the ARIA‑OS CAD pipeline. Once meta JSON population and environment dependencies are fixed, the integration will be able to reject or flag generated parts based on true static SF, dynamic arrest behavior, and system‑level CEM results. 

