# ARIA Auto-Belay — Project Book

> Living document. Update after every significant session.
> Last updated: 2026-04-06

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Product** | ARIA (Autonomous Rope Intelligence Architecture) |
| **Type** | Wall-mounted AI-driven lead climbing auto-belay |
| **Repo** | aria-auto-belay (hardware-specific code) |
| **CAD Pipeline** | aria-os-export (sibling repo, optional import) |
| **Maintainer** | Jonathan Kofman |
| **Target Market** | Climbing gyms with lead walls |
| **Standard** | ANSI Z359.14 (SRL), CE EN 15151-2 (belay devices) |

---

## 2. Current Phase

**Phase: PRE-HARDWARE / SOFTWARE COMPLETE**

All software is written. Hardware has not arrived. Cannot test firmware, BLE, or physical mechanisms until hardware is in hand.

| Component | Status | Blocking On |
|---|---|---|
| STM32 firmware | Written (524 lines) | Hardware arrival |
| ESP32 firmware | Written (743 lines) | Hardware arrival |
| Safety layer | Written (404 lines) | Hardware arrival |
| Wearable firmware | Written | Hardware arrival |
| Python state machine | Complete, tested | Nothing |
| Drop physics model | Complete, tested | Nothing |
| CEM (physics engine) | Complete | Nothing |
| Dashboard (15 tabs) | Complete, working | Nothing |
| Simulator | Complete | Nothing |
| aria-climb app | Fully coded | google-services.json + hardware |
| Constants sync tool | Complete | Hardware for validation |
| PID tuner | Complete | Hardware for tuning |
| HIL test harness | Complete | Hardware |
| Cert package generator | Complete | Test data from hardware |

---

## 3. Hardware Status

### What's Been Ordered / Needed
- [ ] STM32 dev board (Nucleo or Blue Pill)
- [ ] ESP32 dev board (ESP32-S3 recommended for BLE 5)
- [ ] BLDC motor + 30:1 planetary gearbox
- [ ] VESC motor controller
- [ ] HX711 load cell + amplifier
- [ ] Brake drum assembly
- [ ] Ratchet ring + pawl mechanism
- [ ] Centrifugal clutch components (flyweights, springs)
- [ ] Rope spool (600mm diameter)
- [ ] Housing (6061 aluminum, CNC)
- [ ] Power supply (48V for VESC)
- [ ] Wiring harness + connectors

### First Power-On Checklist
1. Flash STM32 with `aria_main.cpp`
2. Serial connect → send `"cal"` → HX711 calibration
3. Copy `HX711_OFFSET` and `HX711_SCALE` → reflash
4. Verify brake engages on power-off (fail-safe)
5. Verify watchdog fires within 500ms
6. Run `tools/aria_constants_sync.py` → all constants match
7. Flash ESP32 with `aria_esp32_firmware.ino`
8. Verify BLE advertising
9. Verify UART bridge (ESP32 ↔ STM32)
10. Run `tools/aria_hil_test.py` → basic state transitions

---

## 4. Software Architecture

### Layers
```
┌─────────────────────────────────────┐
│  aria-climb (React Native app)      │  ← BLE + Firebase
├─────────────────────────────────────┤
│  ESP32 (Intelligence Layer)         │  ← Voice, CV, BLE, UART
├─────────────────────────────────────┤
│  STM32 (Safety Layer)               │  ← State machine, PID, brake
├─────────────────────────────────────┤
│  Mechanical (Passive Safety)        │  ← Ratchet, clutch, brake
└─────────────────────────────────────┘
```

### Fail-Safe Cascade
1. ESP32 crash → STM32 holds tension (independent layer)
2. STM32/VESC fault → power-off brake + centrifugal clutch engage
3. Power cut → power-off brake + centrifugal clutch
4. All electronics fail → ratchet ring catches mechanically

### State Machine
```
IDLE → CLIMBING → {CLIPPING, TAKE, REST, WATCH_ME} → LOWER → IDLE
                → FALL → BRAKE → LOWER → IDLE
```

---

## 5. Certification Roadmap

### ANSI Z359.14 Requirements
| Requirement | Threshold | How We Test | Status |
|---|---|---|---|
| Peak arrest force | ≤ 6000 N | Drop test + load cell | Tool ready (`aria_drop_parser.py`) |
| Arrest distance | ≤ 1000 mm | Drop test measurement | Tool ready |
| Average arrest force | ≤ 4000 N | Computed from load cell CSV | Tool ready |
| Static strength | 3x rated load | Static load test | Protocol ready |
| Braking redundancy | 2 independent systems | Ratchet + clutch + brake | Design complete |
| Environmental | -30°C to +50°C | Climate chamber | Not started |
| Cycle life | 5000 arrest cycles | Endurance test | Not started |

### Test Phases
- [ ] **Phase 1: Mechanical-only drop test** — sandbag + ratchet/pawl, no electronics (`aria_phase1_drop_protocol.py`)
- [ ] **Phase 2: Powered drop test** — full system, motor active, load cell logging
- [ ] **Phase 3: Environmental** — temperature, humidity, dust
- [ ] **Phase 4: Endurance** — 5000 cycle test
- [ ] **Phase 5: Third-party lab** — send to certified test facility

### Certification Package
`dashboard/aria_cert_package.py` generates a ZIP containing:
- Cover page with device specs
- CEM analysis report
- ANSI compliance summary
- Drop test results (CSV + analysis)
- Static load test results
- State machine validation report
- Constants sync verification
- Design history snapshots
- HIL test report
- Open items list

---

## 6. App Status (aria-climb)

| Feature | Status |
|---|---|
| Auth flow (Login/Signup/RoleSelect) | Complete |
| Climber screens (Home, LiveSession, Onboarding) | Complete |
| Gym owner screens (Dashboard, Devices, Provisioning) | Complete |
| BLE stack (scan, connect, provision) | Complete |
| Firebase integration | Complete |
| i18n (en/de/es/fr/ja) | Complete |
| google-services.json | **Missing** — needed before first build |
| First Android build | **Not done** |
| Real device BLE test | **Blocked on hardware** |

### To build:
```bash
cd device/aria-climb
# Add google-services.json to android/app/
eas build --profile development --platform android
```

---

## 7. Dashboard Tabs (15 total)

| Tab | What It Does | Works Now? |
|---|---|---|
| CEM Design | Physics parameter tuning → CSV | Yes |
| Test Data | Load cell CSV upload + analysis | Yes (needs test data) |
| Reports | ANSI Z359.14 PDF generation | Yes (placeholder data) |
| Clutch Sweep | Flyweight × spring heatmap | Yes |
| Materials | Material database browser | Yes |
| State Machine | Firmware state timeline | Yes |
| Design History | CEM snapshot log | Yes |
| Cert Package | ANSI certification ZIP | Yes (placeholder data) |
| Offline Mode | Firebase offline queue | Yes |
| Drop Parser | Load cell → ANSI metrics | Yes (needs CSVs) |
| Fault Table | Firmware fault catalog | Yes |
| Drop Protocol | Phase 1 sandbag protocol | Yes |
| CAD Pipeline | ARIA-OS parts browser | Needs aria-os-export |
| API Server | ARIA-OS API UI | Needs aria-os-export |
| Outputs | Browse STEP/STL/CAM files | Needs aria-os-export |

---

## 8. Next Steps (Priority Order)

### Now (no hardware needed)
- [x] Repo split fix — dashboard, imports, bridge
- [x] CLAUDE.md rewrite for hardware scope
- [x] Project book creation
- [ ] Dashboard end-to-end test (`scripts/START_DASHBOARD.bat`)
- [ ] Cert package dry run with placeholder data
- [ ] Generate mock drop test CSV for drop parser testing
- [ ] App: configure google-services.json
- [ ] App: first EAS build

### When Hardware Arrives
- [ ] First power-on (see checklist in Section 3)
- [ ] HX711 calibration
- [ ] PID tuning on real hardware
- [ ] Phase 1 drop test (sandbag + ratchet/pawl)
- [ ] Full HIL test suite
- [ ] BLE connection test with app
- [ ] Constants sync validation (firmware vs Python)

### After Initial Testing
- [ ] Phase 2 powered drop test
- [ ] Cert package with real test data
- [ ] Submit to third-party test lab
- [ ] Environmental testing
- [ ] Endurance testing (5000 cycles)

---

## 9. Key Files Quick Reference

| File | Purpose |
|---|---|
| `aria_dashboard.py` | Main dashboard entry point (70KB) |
| `aria_os_bridge.py` | sys.path bridge to aria-os-export |
| `aria_models/state_machine.py` | Python state machine (mirrors STM32) |
| `aria_cem/module.py` | ARIA CEM physics engine |
| `device/firmware/stm32/aria_main.cpp` | STM32 safety layer |
| `device/firmware/stm32/safety.cpp` | Watchdog + fault recovery |
| `device/firmware/esp32/aria_esp32_firmware.ino` | ESP32 intelligence layer |
| `tools/aria_simulator.py` | Headless state machine CLI |
| `tools/aria_constants_sync.py` | Firmware ↔ Python constant verification |
| `tools/aria_pid_tuner.py` | PID gain sweep tool |
| `tools/aria_hil_test.py` | Hardware-in-loop test harness |
| `dashboard/aria_cert_package.py` | ANSI Z359.14 cert ZIP generator |
| `dashboard/aria_drop_parser.py` | Load cell CSV → arrest metrics |
| `dashboard/aria_phase1_drop_protocol.py` | Phase 1 sandbag drop protocol |
| `context/aria_mechanical.md` | Geometry constants (single source of truth) |
| `PROJECT_STATUS.md` | Version/phase tracker |

---

## 10. Revision History

| Date | Change |
|---|---|
| 2026-04-06 | Initial project book — post repo split |
| 2026-03-27 | Firmware merged (all three layers) |
| 2026-03-31 | Hardware book v1.0 completed |
