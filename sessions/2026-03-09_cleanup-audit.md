# Repo Cleanup Audit — 2026-03-09

Analysis-only audit (no deletions performed).

Repo: `c:\Users\jonko\Downloads\aria-auto-belay`  
Inventory scope: included everything except `.git/`, `node_modules/`, `.venv/`.

## Context + rules read
- `.cursorrules`
- `context/aria_mechanical.md`
- `context/aria_materials.md`
- `context/aria_test_standards.md`
- `context/aria_system_overview.md`
- `context/aria_firmware.md`
- `context/aria_failures.md`
- `context/aria_patent.md`

## Dependency methodology (best-effort)
- **Python**: derived from `import` / `from ... import ...` lines (regex extraction), mapped to local modules where possible (`aria_models`, `aria_os`, root modules).
- **JS/TS**: derived from `import ... from '...'` lines in `aria-climb/src/**`.
- **Non-code artifacts**: depended_by populated only when there is an obvious hard reference (e.g., CLI listing directories), otherwise blank.

---

## Inventory (high-level folders)
- `aria_os/` — KEEP (current ARIA-OS workflow core)
- `aria_models/` — KEEP (dashboard + physics models)
- `aria-climb/` — KEEP (companion app)
- `cad/` — KEEP (Fusion scripts)
- `context/` — KEEP (knowledge base)
- `docs/` — KEEP (docs/specs)
- `firmware/` — KEEP (STM32/ESP32)
- `outputs/` — REVIEW (generated artifacts policy decision)
- `sessions/` — KEEP (project history)
- `tools/` — KEEP (utilities)

Note: `tests/` directory is **missing** (so “tests empty” effectively means “no tests folder yet”).

---

## Inventory (files)

Format: `filename | category | reason | depends_on | depended_by`

### Root config / env / docs
- `.cursorrules | KEEP | Project operating rules & repo map |  | (human/agent workflow)`
- `.gitignore | KEEP | Repo hygiene |  | git`
- `.env.example | KEEP | Example env config (non-secret) |  | developers`
- `.env | REVIEW | Local config; ensure not committed / contains secrets |  | runtime`
- `README.md | KEEP | Repo entrypoint |  | developers`
- `CURSOR_GUIDE.md | KEEP | Dev/agent guide |  | developers`
- `requirements.txt | KEEP | Python deps (dashboard/tools/models) |  | python runtime`
- `requirements_aria_os.txt | KEEP | Python deps (ARIA-OS) |  | python runtime`

### Root dashboard + CEM + tabs (Streamlit)
- `aria_dashboard.py | KEEP | Main dashboard entry; imports tabs (explicit KEEP rule) | aria_*_tab.py, aria_models/*, aria_fault_behavior.py | (entrypoint)`
- `aria_cem_tab.py | KEEP | Dashboard tab | aria_cem.py, aria_design_history.py | aria_dashboard.py`
- `aria_testdata_tab.py | KEEP | Dashboard tab |  | aria_dashboard.py`
- `aria_report_tab.py | KEEP | Dashboard tab |  | aria_dashboard.py`
- `aria_clutch_sweep.py | KEEP | Dashboard tab |  | aria_dashboard.py`
- `aria_materials_tab.py | KEEP | Dashboard tab |  | aria_dashboard.py`
- `aria_statemachine_tab.py | KEEP | Dashboard tab | aria_models/state_machine.py | aria_dashboard.py`
- `aria_design_history.py | KEEP | Dashboard tab + history log |  | aria_dashboard.py, aria_cem_tab.py`
- `aria_cert_package.py | KEEP | Dashboard tool |  | aria_dashboard.py`
- `aria_offline_mode.py | KEEP | Dashboard support |  | aria_dashboard.py`
- `aria_drop_parser.py | KEEP | Dashboard support |  | aria_dashboard.py`
- `aria_fault_behavior.py | KEEP | Fault behavior spec + simulator |  | aria_dashboard.py`
- `aria_cem.py | KEEP | ARIA CEM computations | cem_core.py | aria_cem_tab.py (via dashboard)`
- `cem_core.py | KEEP | CEM core abstractions + utilities |  | aria_cem.py`
- `cem_design_history.json | KEEP | Design history data |  | aria_design_history.py (usage), humans`

### Root simulation / analysis scripts (manual use)
- `aria_phase1_drop_protocol.py | KEEP | Drop protocol tooling |  | manual`
- `aria_flyweight_verify.py | KEEP | Mechanical verification tooling |  | manual`

### State machine duplicates (explicit duplicate rule)
- `state_machine.py | REVIEW | Duplicate filename vs `aria_models/state_machine.py`; needs canonicalization decision |  | referenced by docs/.cursorrules (conceptually)`
- `aria_models/state_machine.py | KEEP | Used by dashboard (`aria_models/__init__.py` / `aria_dashboard.py`) |  | aria_models/__init__.py, aria_dashboard.py`

### `aria_models/`
- `aria_models/__init__.py | KEEP | Aggregates models for dashboard use | aria_models/static_tests.py, aria_models/dynamic_drop.py, aria_models/state_machine.py | aria_dashboard.py`
- `aria_models/static_tests.py | KEEP | Static load SF checks |  | aria_models/__init__.py`
- `aria_models/dynamic_drop.py | KEEP | Drop simulation |  | aria_models/__init__.py`
- `aria_models/design_suggestions.py | KEEP | Design hints used by dashboard |  | aria_dashboard.py`

### `aria_os/`
- `aria_os/__init__.py | KEEP | Package entry | aria_os/orchestrator.py | run_aria_os.py`
- `aria_os/orchestrator.py | KEEP | ARIA-OS pipeline | aria_os/* | aria_os/__init__.py`
- `aria_os/context_loader.py | KEEP | Loads `context/*.md` | context/* | aria_os/*`
- `aria_os/planner.py | KEEP | Planning stage | aria_os/context_loader.py | aria_os/orchestrator.py`
- `aria_os/generator.py | KEEP | Code generation | aria_os/llm_generator.py, templates | aria_os/orchestrator.py`
- `aria_os/llm_generator.py | KEEP | LLM CadQuery generation |  | aria_os/generator.py, aria_os/modifier.py`
- `aria_os/validator.py | KEEP | Geometry/STEP validation | cadquery | aria_os/orchestrator.py, run_aria_os.py`
- `aria_os/exporter.py | KEEP | Export pathing |  | aria_os/orchestrator.py, aria_os/modifier.py`
- `aria_os/logger.py | KEEP | Session logging |  | aria_os/orchestrator.py`
- `aria_os/modifier.py | KEEP | Part modification workflow | aria_os/llm_generator.py | run_aria_os.py`
- `aria_os/assembler.py | KEEP | Assembly mode | cadquery | run_aria_os.py`
- `aria_os/goal_parser.py | KEEP | NL goal parsing helper |  | aria_os/planner.py (conceptually)`
- `aria_os/cem_checks.py | KEEP | ARIA-OS → CEM bridge | aria_models/static_tests.py, aria_models/dynamic_drop.py, aria_cem.py | aria_os/orchestrator.py`

### ARIA-OS CLI / config
- `run_aria_os.py | KEEP | ARIA-OS CLI entrypoint | aria_os/* | (entrypoint)`
- `assembly_configs/aria_clutch_assembly.json | KEEP | Assembly config used by `--assemble` |  | run_aria_os.py`

### `tools/` (utilities)
- `tools/aria_simulator.py | KEEP | Simulator referenced in docs/rules |  | manual`
- `tools/aria_pid_tuner.py | KEEP | PID tuning tool |  | manual`
- `tools/aria_monitor.py | KEEP | Monitoring tool |  | manual`
- `tools/aria_test_harness.py | KEEP | Test harness |  | manual`
- `tools/aria_hil_test.py | KEEP | HIL testing |  | manual`
- `tools/aria_constants_sync.py | KEEP | Constant syncing/verification |  | manual`
- `tools/aria_collect_audio.py | KEEP | Audio collection |  | manual`
- `tools/generate_mock_drop_csv.py | KEEP | Utility |  | manual`

### `cad/fusion_scripts/`
- `cad/fusion_scripts/aria_housing_complete.py | KEEP | Fusion script referenced by failures doc |  | context/aria_failures.md`
- `cad/fusion_scripts/aria_support_complete.py | KEEP | Fusion script |  | manual`
- `cad/fusion_scripts/aria_small_parts_complete.py | KEEP | Fusion script |  | manual`
- `cad/fusion_scripts/aria_rope_spool_complete.py | KEEP | Fusion script |  | manual`
- `cad/fusion_scripts/aria_cam_collar_complete.py | KEEP | Fusion script |  | manual`
- `cad/fusion_scripts/aria_ratchet_shaft_complete.py | KEEP | Fusion script |  | manual`

### `firmware/`
- `firmware/stm32/aria_main.cpp | KEEP | Safety layer main |  | context/aria_firmware.md`
- `firmware/stm32/safety.cpp | KEEP | Safety logic | firmware/stm32/safety.h | firmware/stm32/aria_main.cpp`
- `firmware/stm32/safety.h | KEEP | Safety header |  | firmware/stm32/safety.cpp`
- `firmware/stm32/calibration.cpp | KEEP | Calibration |  | context/aria_firmware.md`
- `firmware/stm32/wiring_verify.cpp | KEEP | Wiring verification | firmware/stm32/wiring_verify.h | context/aria_firmware.md`
- `firmware/stm32/wiring_verify.h | KEEP | Wiring verify header |  | firmware/stm32/wiring_verify.cpp`
- `firmware/esp32/aria_esp32_firmware.ino | KEEP | Intelligence layer |  | context/aria_firmware.md`
- `firmware/esp32/aria_wearable/aria_wearable.ino | KEEP | Wearable firmware |  | context/aria_firmware.md`

### `docs/`
- `docs/ARIA_SETUP.md | KEEP | Setup guide |  | humans`
- `docs/ARIA_APP_SPEC.md | KEEP | App spec |  | humans`
- `docs/ARIA_SAFETY_MONITORING.md | KEEP | Safety monitoring spec |  | humans`
- `docs/ARIA_CURSOR_BRIEF.md | KEEP | Cursor brief |  | humans`
- `docs/edge_impulse_setup.md | KEEP | Edge Impulse setup |  | humans`
- `docs/REAL_TESTING_CHECKLIST.md | KEEP | Testing checklist |  | humans`

### `context/`
- `context/aria_mechanical.md | KEEP | Mechanical constants |  | aria_os/context_loader.py`
- `context/aria_materials.md | KEEP | Materials constants |  | aria_os/context_loader.py`
- `context/aria_test_standards.md | KEEP | Test/ANSI constants |  | aria_os/context_loader.py`
- `context/aria_system_overview.md | KEEP | Overview |  | humans`
- `context/aria_firmware.md | KEEP | Firmware spec |  | humans`
- `context/aria_failures.md | KEEP | Fusion failures |  | humans`
- `context/aria_patent.md | KEEP | Patent context |  | humans`

### `sessions/` (explicit KEEP rule)
- `sessions/* | KEEP | Project history |  | humans/agent workflow`

### `outputs/` (explicit REVIEW rule)
- `outputs/** | REVIEW | Generated CAD artifacts and generated code; retention policy decision |  | run_aria_os.py --list/--validate`

Special case:
- `test_spacer.step | REVIEW | Stray generated artifact at repo root; should be moved under outputs/ or deleted after decision |  | manual`

### `aria-climb/` (React Native app)
All non-`node_modules` files under `aria-climb/` are **KEEP** (active app). A few items to REVIEW for policy:
- `aria-climb/google-services.json | REVIEW | Firebase config; decide commit policy (often committed, but ensure it’s intended) |  | build/runtime`

---

## Summary

- **Total files**: REVIEW (requires full filesystem enumeration to count precisely; this audit is structural and policy-focused)
- **Safe to delete**: 0 identified automatically (no bytecode/caches enumerated in scope)

### Needs Jonathan’s decision (REVIEW items)
- **Outputs retention**: `outputs/**`  
  - Question: keep generated STEP/STL and generated CadQuery scripts in git, or move to releases/git-lfs and prune by default?
- **Duplicate state machine**: `state_machine.py` vs `aria_models/state_machine.py`  
  - Question: which file is canonical, and should the other be archived or deleted?
- **Root stray artifact**: `test_spacer.step`  
  - Question: keep (move to `outputs/`) or delete?
- **Firebase config**: `aria-climb/google-services.json`  
  - Question: keep committed (common) or treat as environment-specific and ignore?

### Duplicates found
- `state_machine.py` ↔ `aria_models/state_machine.py`

