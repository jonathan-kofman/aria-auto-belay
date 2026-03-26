# ARIA Quality & Certification Audit Report

**Date:** 2026-03-26
**Status:** Completed with findings
**Auditor role:** Quality Engineer & Test/Certification Engineer

---

## 1. Test Suite Execution Results

### 1.1 CAD Pipeline Tests (`python -m pytest tests/ -q`)

**Result: 6 passed, 0 failed** (0.42s)

All tests in `tests/test_grasshopper_scripts.py`:

| Test | Status |
|------|--------|
| `test_ratchet_ring_script_valid_python` | PASS |
| `test_housing_script_valid_python` | PASS |
| `test_brake_drum_script_valid_python` | PASS |
| `test_spool_script_valid_python` | PASS |
| `test_no_backslash_paths` | PASS |
| `test_all_templates_produce_valid_python` | PASS |

### 1.2 Physics / State Machine Unit Tests (`python aria_models/static_tests.py`)

**Result: PASS** (no output = no assertions fired, runs cleanly)

Note: This file is designed to be called by the dashboard, not as a standalone test runner. It defines functions (`simulate_static_pawl`, `ansi_proof_load_check`) but has no `if __name__ == "__main__"` test block. There are no dedicated unit tests that exercise these functions with edge cases.

### 1.3 Scenario Tests (`python tools/aria_test_harness.py`)

**Result: NOT RUNNABLE** (requires connected STM32 hardware on `/dev/ttyS0`)

The test harness enters interactive serial mode immediately. It cannot be run in CI or headless environments. There is no mock/simulation mode.

---

## 2. Test Coverage Analysis

### 2.1 What IS tested

| Area | Test file | Coverage |
|------|-----------|----------|
| Grasshopper templates (6 parts) | `tests/test_grasshopper_scripts.py` | Valid Python syntax, correct RhinoCommon API calls, no old API patterns, BBOX print, no backslash paths |

### 2.2 What is NOT tested (gaps)

| Gap | Severity | Details |
|-----|----------|---------|
| **CadQuery templates (16 templates)** | HIGH | Zero test coverage. No smoke tests for any of the 16 `_CQ_TEMPLATE_MAP` entries. Templates are never executed in tests. |
| **post_gen_validator.py** | HIGH | Zero test coverage. `parse_spec()`, `check_geometry()`, `check_output_quality()`, `run_validation_loop()` are untested. |
| **spec_extractor.py** | MEDIUM | Referenced in CLAUDE.md as having 40 tests (`tests/test_spec_extractor.py`) but this file does not exist in `tests/`. |
| **dynamic_drop.py** | HIGH | Zero test coverage. No tests verify ANSI limit enforcement (8000N, 813mm, 6000N). |
| **static_tests.py** | HIGH | Functions exist but no unit tests exercise them. No edge case tests (zero dimensions, extreme loads). |
| **cem_checks.py** | HIGH | Zero test coverage. No tests verify SF thresholds or pass/fail logic. |
| **tool_router.py / multi_cad_router.py** | MEDIUM | Referenced in CLAUDE.md as having 14 smoke tests (`tests/test_cad_router.py`) but this file does not exist. |
| **api_server.py** | MEDIUM | Referenced in CLAUDE.md as having tests (`tests/test_api_server.py`) but this file does not exist. |
| **e2e pipeline** | MEDIUM | Referenced as `tests/test_e2e_pipeline.py` but does not exist. |
| **Firmware state machine** | MEDIUM | `aria_models/state_machine.py` has no test coverage. |
| **Constants sync** | LOW | `tools/aria_constants_sync.py` exists but is never tested automatically. |

### 2.3 Documentation vs Reality

CLAUDE.md references **186 tests across 5 test files**. In reality:
- Only **1 test file** exists: `tests/test_grasshopper_scripts.py` (6 tests)
- **4 referenced test files are missing**: `test_post_gen_validator.py`, `test_cad_router.py`, `test_spec_extractor.py`, `test_api_server.py`, `test_e2e_pipeline.py`
- Actual test count: **6**, not 186

---

## 3. Validation Pipeline Review

### 3.1 `aria_os/post_gen_validator.py` Assessment

**Strengths:**
- Multi-layer validation: spec parsing, geometry checks, output quality, visual AI review
- Retry loop with failure context injection (up to 3 attempts)
- Best-attempt tracking across retries
- Bore detection via volume-fraction heuristic
- Auto-repair of non-watertight STL (fill_holes, fix_normals, fix_winding)
- Part-specific tolerance tiers (tight/medium/loose)

**Weaknesses and missing checks:**
1. **No minimum wall thickness check.** Parts can pass with paper-thin walls that would fail under load.
2. **No self-intersection check.** Only watertight is checked; self-intersecting meshes pass.
3. **No minimum feature size check.** Teeth, bores, or other features could be below printable resolution.
4. **Bore detection is volume-ratio only** (line 255: `mesh.volume / solid_vol < 0.65`). A part with many small holes but no through-bore could false-positive. A thick-walled tube could false-negative.
5. **Volume bounds only computed for cylindrical parts** (when both OD and height are known). Box-shaped parts (housing, bracket) get no volume validation.
6. **No face count or triangle quality check** on STL output (degenerate triangles, slivers).
7. **Visual check gracefully degrades to pass** when API key is missing -- silent skip with no warning in the final result's `passed` flag.

### 3.2 `aria_os/validator.py` Assessment

**Strengths:**
- Feature completeness heuristic (bore, slot, bolt circle detection in code)
- Mesh integrity check via numpy-stl (degenerate triangle detection)
- Grasshopper script validation (syntax, required API calls, size threshold)
- Housing spec bbox validation

**Weaknesses:**
1. **STEP validation is size-only** (line 14: `GRASSHOPPER_ONLY = True`). No CadQuery re-import to verify solid integrity. A corrupt STEP file that happens to be large enough passes.
2. **`validate()` uses `exec()` on generated code** (line 129) with no sandboxing. Malicious or buggy LLM output could execute arbitrary code.
3. **Bbox tolerance is hardcoded 0.5mm** (line 148) regardless of part size. A 700mm housing has the same absolute tolerance as a 20mm pin.
4. **`validate_mesh_integrity` falls back to file-size check** when numpy-stl is not installed, with a 10KB threshold that is too low for meaningful validation.

---

## 4. ANSI Z359.14 Compliance Check

### 4.1 Limits from `context/aria_test_standards.md`

| Requirement | Standard Value | Status |
|-------------|---------------|--------|
| Max arrest force | 8000 N | Enforced in `dynamic_drop.py` line 150 |
| Max avg arrest force | 6000 N | Enforced in `dynamic_drop.py` line 151 |
| Max arrest distance | 813 mm | Enforced in `dynamic_drop.py` line 149 |
| Static proof load | 16000 N | Used as max load step in `cem_checks.py` line 79 |
| Min safety factor | 2.0 | Enforced in `static_tests.py` line 202 |

### 4.2 Compliance Findings

**FINDING 1 (CRITICAL): Ratchet ring SF=8.0 threshold NOT enforced in code.**
- CLAUDE.md documents that `aria_ratchet_ring` requires SF >= 8.0 for tooth_shear (safety-critical).
- `cem_checks.py` line 93 uses `sf >= 2.0` -- the generic threshold, not 8.0.
- A ratchet ring with SF=2.5 would pass all checks despite the documented 8.0 requirement.
- **Risk: Under-designed ratchet ring could pass validation and proceed to manufacture.**

**FINDING 2 (HIGH): Dynamic checks not run during per-part validation.**
- `run_cem_checks()` (called per part) always sets `dynamic_passed=None` (line 334).
- Dynamic drop test validation (8000N, 813mm, 6000N) only runs in `run_full_system_cem()` (line 385).
- Normal CAD pipeline (`orchestrator.py` -> `cem_checks.run_cem_checks()`) never triggers dynamic checks.
- ANSI arrest force/distance limits are only enforced if `--cem-full` is explicitly invoked.

**FINDING 3 (HIGH): No automated test validates ANSI limits.**
- `dynamic_drop.py` correctly implements the limits, but no test file calls `simulate_drop_test()` and asserts the limits hold.
- A code change that accidentally modifies `limit_peak`, `limit_avg`, or `limit_dist` would go undetected.
- Similarly, no test calls `simulate_static_pawl()` and verifies SF >= 2.0 at 16000N.

**FINDING 4 (MEDIUM): `ansi_proof_load_check()` uses hardcoded defaults, ignores passed dimensions.**
- `static_tests.py` line 217: `_housing_wall_stress_mpa(ansi_load_n)` ignores the `housing_wall_mm` parameter.
- The function accepts `housing_wall_mm` as a parameter but passes only `ansi_load_n` to the stress function.
- Result: proof load check always uses the default 10mm wall, not the actual part dimensions.

**FINDING 5 (MEDIUM): No enforcement of SF >= 2.0 as a gate in the CAD pipeline.**
- CEM checks produce SF values and log them, but the orchestrator does not block STEP/STL export when SF < 2.0.
- A part with SF=0.5 can still be exported. The CEM result is informational only.
- The `status` returned can be `"success_cem_warning"` and still pass the validation loop (line 761 of `post_gen_validator.py`).

**FINDING 6 (LOW): False trip test (`simulate_false_trip_check`) is never called by any test or pipeline.**
- The function exists in `dynamic_drop.py` (line 174) but is orphaned -- no caller in the codebase invokes it during automated testing.

---

## 5. Summary of Recommendations

### Critical (must fix before any physical testing)
1. **Enforce SF=8.0 for ratchet ring tooth_shear** in `cem_checks.py` -- add per-part SF threshold map.
2. **Write unit tests for ANSI limits** -- at minimum, tests that call `simulate_drop_test()` and `simulate_static_pawl()` and assert compliance values.
3. **Fix `ansi_proof_load_check()`** to pass `housing_wall_mm` to `_housing_wall_stress_mpa()`.

### High priority
4. **Add CadQuery template smoke tests** -- each of the 16 templates should be executed and produce valid STEP+STL.
5. **Create the 4 missing test files** referenced in CLAUDE.md, or update CLAUDE.md to reflect actual test inventory.
6. **Wire dynamic checks into per-part CEM** or make `--cem-full` mandatory before export approval.
7. **Make CEM SF a hard gate** -- block STEP/STL export when SF < 2.0 (or part-specific threshold).

### Medium priority
8. Add wall thickness validation to `post_gen_validator.py`.
9. Add volume bounds for non-cylindrical parts (box, bracket shapes).
10. Add a mock/simulation mode to `aria_test_harness.py` for CI.
11. Sandbox the `exec()` call in `validator.py`.

### Low priority
12. Wire `simulate_false_trip_check()` into automated testing.
13. Improve bbox tolerance scaling (percentage-based rather than fixed 0.5mm).
14. Add STL triangle quality checks (degenerate triangle count, aspect ratio).

---

## 6. Test Execution Environment

- Python 3.11.14 on Linux 6.18.5
- pytest 9.0.2
- cadquery 2.7.0, trimesh 4.11.5
- No LLM API keys configured (all LLM-dependent paths use heuristic fallback)
- No hardware connected (STM32/ESP32 tests skipped)
