# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

---

## What This Is

ARIA (Autonomous Rope Intelligence Architecture) — a wall-mounted lead climbing auto-belay device. This repo contains **hardware-specific code only**:

1. **Firmware** — STM32 safety layer + ESP32 intelligence layer (hardware not yet arrived)
2. **aria-climb** — React Native / Expo companion app
3. **Dashboard** — Streamlit virtual test dashboard for hardware validation
4. **Models** — State machine, drop physics, CEM analysis

The generic CAD pipeline (ARIA-OS) lives in the sibling repo `aria-os-export`. Import bridge: `aria_os_bridge.py` auto-adds it to `sys.path`.

---

## Commands

### Dashboard
```bash
# Windows (sets up .python/ local env automatically)
scripts/START_DASHBOARD.bat

# System Python
pip install -r requirements.txt
streamlit run aria_dashboard.py
```

### Simulator & tools
```bash
python tools/aria_simulator.py          # headless state machine CLI (scenario climb, voice take, status)
python tools/aria_constants_sync.py     # verify constants match between simulator and firmware
python tools/aria_pid_tuner.py          # PID Kp/Ki/Kd sweep
python tools/aria_hil_test.py           # hardware-in-loop tests (requires connected hardware)
python tools/aria_test_harness.py       # automated scenario PASS/FAIL tests
```

### Tests
```bash
python aria_models/static_tests.py      # unit tests for state machine / physics
```

### aria-climb app
```bash
cd device/aria-climb
npm install --legacy-peer-deps
npx expo run:android    # add google-services.json first
npx expo start          # JS-only preview via Expo Go (no BLE)

# EAS cloud build (no local Android SDK required)
npm install -g eas-cli
eas build --profile development --platform android
```

### ARIA-OS (CAD pipeline — in aria-os-export)
```bash
# Requires aria-os-export as sibling directory
cd ../aria-os-export
pip install -r requirements_aria_os.txt
python run_aria_os.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
```

---

## Architecture: Firmware

Two fully independent layers. Safety layer operates with zero dependency on intelligence layer.

- `device/firmware/stm32/aria_main.cpp` — state machine, brake GPIO, VESC UART, PID tension loop, UART command handler (524 lines)
- `device/firmware/stm32/safety.cpp` — watchdog, fault recovery, power-on safety boot sequence (404 lines)
- `device/firmware/esp32/aria_esp32_firmware.ino` — voice (Edge Impulse), CV, BLE, UART bridge to STM32 (743 lines)
- `device/firmware/stm32/wearable/aria_wearable.ino` — wearable companion firmware (BLE to phone)
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

**Firmware status:** All firmware files implemented (merged 2026-03-27). Hardware not yet arrived — untested on real hardware.

**First-time hardware setup:** flash STM32 → serial `"cal"` → copy HX711_OFFSET/HX711_SCALE → reflash.

Fail-safe principle: ESP32 crash → STM32 holds tension. STM32/VESC fault → brake + centrifugal clutch. Power cut → power-off brake + clutch.

---

## Architecture: Models & CEM

### aria_models/
- `state_machine.py` — `AriaStateMachine` + `Inputs` dataclass. States: IDLE, CLIMBING, CLIPPING, TAKE, REST, LOWER, WATCH_ME, FALL, BRAKE.
- `drop_physics.py` — `simulate_drop_test()`: fall dynamics, arrest force, deceleration distance
- `static_pawl.py` — `simulate_static_pawl()`: pawl engagement under static load
- `false_trip.py` — `simulate_false_trip_check()`: false positive detection margin
- `design_suggestions.py` — `get_static_suggestions()`, `get_drop_suggestions()`, `get_false_trip_suggestions()`, `get_state_machine_suggestions()`
- `static_tests.py` — unit test suite

### aria_cem/
ARIA-specific CEM (Computational Engineering Model) for drop test physics:
- `inputs.py` — `ARIAInputs` dataclass
- `module.py` — `ARIAModule`, `compute_aria()`, `compute_for_goal()`
- Brake drum sizing, ratchet/pawl geometry, rope spool sizing, centrifugal clutch, housing wall thickness
- Standards: ANSI Z359.14 (SRL), CE EN 15151-2 (belay devices)
- Target: 8 kN arrest force, <6m fall distance, <6 kN peak force on climber

---

## Architecture: Dashboard

`aria_dashboard.py` — 70KB Streamlit dashboard with 15 tabs:

### Hardware tabs (12 — self-contained)
| Tab | Module | Purpose |
|---|---|---|
| CEM Design | `dashboard/aria_cem_tab.py` | Physics parameter tuning → CSV export |
| Test Data | `dashboard/aria_testdata_tab.py` | Load cell CSV upload + analysis |
| Reports | `dashboard/aria_report_tab.py` | ANSI Z359.14 PDF generation |
| Clutch Sweep | `dashboard/aria_clutch_sweep.py` | Flyweight × spring preload heatmap |
| Materials | `dashboard/aria_materials_tab.py` | Material database browser |
| State Machine | `dashboard/aria_statemachine_tab.py` | Firmware state timeline + transitions |
| Design History | `dashboard/aria_design_history.py` | CEM snapshot log |
| Cert Package | `dashboard/aria_cert_package.py` | ANSI Z359.14 certification ZIP |
| Offline Mode | `dashboard/aria_offline_mode.py` | Firebase offline session queue |
| Drop Parser | `dashboard/aria_drop_parser.py` | Load cell CSV → ANSI arrest metrics |
| Fault Table | `dashboard/aria_fault_behavior.py` | Firmware fault catalog + HIL simulator |
| Drop Protocol | `dashboard/aria_phase1_drop_protocol.py` | Phase 1 sandbag drop test protocol |

### OS-generic tabs (3 — require aria-os-export)
| Tab | Module | Purpose |
|---|---|---|
| CAD Pipeline | `dashboard/aria_cad_tab.py` | Parts library, material study, assembly |
| API Server | `dashboard/aria_api_tab.py` | ARIA-OS FastAPI server UI |
| Outputs | `dashboard/aria_outputs_tab.py` | Browse generated STEP/STL/CAM files |

These 3 tabs gracefully degrade with a "install aria-os-export" message when the pipeline isn't available.

---

## Architecture: aria-climb App

React Native / Expo companion app (`device/aria-climb/`).

**App architecture** (`device/aria-climb/src/`): Zustand stores (`auth`, `ble`, `alert`, `session`), BLE services (scan/connect/provision/verify), Firebase services (devices/incidents/sessions), hooks (`useARIADevice`, `useGymDevices`), screens for climber flow (onboarding, live session) and gym flow (dashboard, device management, provisioning, alerts). Types in `types/aria.ts` + `types/device.ts`. BLE packet parser in `utils/`. i18n: en/de/es/fr/ja.

**BLE:** native build only (`expo run:android` or EAS). Expo Go does not support `react-native-ble-plx`.
**Firebase:** add `google-services.json` to `device/aria-climb/android/app/` before first build.

---

## Context Files

All in `context/` — read before any hardware or CEM work:
- `aria_mechanical.md` — **single source of truth for all geometry constants**
- `aria_firmware.md` — firmware architecture, pin assignments, state machine spec
- `aria_materials.md` — material selection and properties
- `aria_failures.md` — known failure patterns and fixes
- `aria_safety.md` — safety requirements, ANSI Z359.14 compliance
- `aria_calibration.md` — HX711 calibration, PID tuning procedures
- `aria_testing.md` — test protocols, pass/fail criteria

---

## Repo Structure

```
aria_dashboard.py          — Main Streamlit dashboard (70KB)
aria_os_bridge.py          — sys.path bridge to ../aria-os-export
aria_models/               — State machine, physics models, design suggestions
aria_cem/                  — ARIA-specific CEM (drop test physics)
dashboard/                 — 15 Streamlit tab modules
device/
  firmware/stm32/          — STM32 safety layer firmware
  firmware/esp32/          — ESP32 intelligence layer firmware
  aria-climb/              — React Native companion app
  training/                — Edge Impulse voice training data
tools/                     — Simulator, HIL test, PID tuner, constants sync
context/                   — Hardware context files (7 .md files)
cad-pipeline/              — ARIA-specific assembly configs and part specs
data/                      — Test data (drop test CSVs, calibration logs)
docs/
  book/                    — Hardware project book (20alexl template)
  aria-os-book/            — ARIA-OS project book (reference)
sessions/                  — Session logs
outputs/                   — Generated outputs (gitignored)
```

---

## Import Bridge (aria-os-export)

`aria_os_bridge.py` adds `../aria-os-export` to `sys.path` when the sibling directory exists. The dashboard imports it automatically. Three tabs (CAD, API, Outputs) use it optionally.

To enable: just have `aria-os-export` as a sibling directory, or `pip install -e ../aria-os-export`.

See `TODO_IMPORT.md` for full post-split documentation.

---

## Session Logging

After every run, append to `sessions/YYYY-MM-DD_task.md`:
```
## Session TIMESTAMP
**Status:** Success | Failure
**Goal:** <goal string>
**Attempts:** N
**Output:** <path>      # if success
**Diagnosis:** <error>   # if failure
```

On failure after 3 attempts: write diagnosis to sessions/, stop, do not ask user unless stuck.
