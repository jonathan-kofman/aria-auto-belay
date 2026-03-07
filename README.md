# ARIA — Autonomous Rope Intelligence Architecture

**A hybrid mechanical + AI-assisted lead climbing auto belay device**

[![Status](https://img.shields.io/badge/status-pre--purchase%20%7C%20firmware%20dev-yellow)](https://github.com/jonathan-kofman/aria-auto-belay)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **What is this?** There is no commercially available lead auto belay device in the United States. ARIA is an attempt to build one — starting from the Lead Solo mechanical design and adding an intelligent motor-assisted slack management system on top.

---

## The Problem

Indoor lead climbing requires a human belayer. Every gym with lead walls has idle capacity: intermediate and advanced climbers who want to train alone can't use lead routes without a certified partner. Top-rope auto belays (TruBlue, etc.) exist, but they don't work for lead climbing — the rope feeds from the top, not the base, and can't pay out slack as a climber moves up and clips quickdraws.

**The gap:** ~300 US gyms have lead walls. Zero have a US-certified lead auto belay they can purchase.

---

## What ARIA Does

ARIA sits at the base of a lead wall and manages the rope for a solo lead climber:

- **Catches falls** via a centrifugal clutch (purely mechanical, zero electronics required)
- **Manages slack** via a BLDC motor that feeds rope out as the climber ascends
- **Detects clipping** via computer vision — pre-feeds slack before the climber pulls
- **Responds to voice** — yell "take", "slack", "lower", "rest", "watch me", "up"
- **Two-factor safety** — voice commands require physical sensor confirmation before executing

```
Climber yells "TAKE"
       ↓
ESP32 detects wake word (>85% confidence)
       ↓
STM32 opens 500ms confirmation window
       ↓
Load cell must read >200N (climber physically weighting rope)
       ↓
Only then: spool locks, climber hangs safely
```

---

## Architecture

Two completely independent layers. The safety layer operates with zero dependency on the intelligence layer.

```
┌─────────────────────────────────────────────────────────┐
│                    MECHANICAL LAYER                      │
│         Centrifugal clutch — operates with NO power      │
│         Catches falls independently of all electronics   │
└─────────────────────────────────────────────────────────┘
                           │
                    one-way bearing
                    (motor cannot
                    backdrive clutch)
                           │
┌─────────────────────────────────────────────────────────┐
│              STM32F411 — SAFETY LAYER                    │
│  Brake GPIO + E-stop  │  HX711 tension  │  AS5048A encoder│
│  ARIA state machine   │  VESC UART      │  Fault recovery  │
│  UART ← ESP32         │  UART → VESC    │                  │
└─────────────────────────────────────────────────────────┘
           │ UART                    │ UART
           ▼                         ▼
┌──────────────────────┐   ┌─────────────────────────────┐
│  VESC MINI 6.7       │   │  XIAO ESP32-S3 Sense         │
│  FOC motor control   │   │  Voice + CV + BLE + UART     │
└──────────────────────┘   └─────────────────────────────┘
```

**Fail-safe principle:** If the ESP32 crashes → STM32 holds safe tension independently. If the STM32 or VESC faults → brake engages; centrifugal clutch catches falls mechanically. If power cuts → power-off brake in gearmotor engages; clutch controls descent.

---

## State Machine

```
IDLE → CLIMBING → CLIPPING (auto) → CLIMBING
              ↓ voice
           TAKE / REST / LOWER / WATCH ME / UP
              ↓ zone intrusion (10s)
           CLIMBING_PAUSED (brake on, alert)
              ↓ any fault / E-stop
           EMERGENCY_STOP (brake on, power cycle to clear)
```

| State | Entry | Motor / Brake | Exit |
|-------|-------|----------------|------|
| IDLE | No climber | Brake on | CV detects climber + tension > 15N |
| CLIMBING | Climber on wall | Motor: tension control | Voice or clip detected |
| CLIPPING | CV: clip gesture | Motor: pre-pay slack | Auto after clip duration |
| TAKE | Voice + load cell | Lock spool | "climbing" voice or upward movement |
| REST | Voice "rest" | Hold position | "climbing" voice or timeout |
| LOWER | Voice "lower" | Controlled payout | Tension drops < 15N |
| WATCH ME | Voice "watch me" | Tighter tension | "climbing" voice or timeout |
| UP | Voice "up" | Near-zero tension | "climbing" voice |
| CLIMBING_PAUSED | Zone intrusion 10s | Brake on, motor hold | Zone cleared or "climbing" voice |
| EMERGENCY_STOP | E-stop button or VESC fault | Brake on | Power cycle |

---

## Hardware

| Component | Purpose | Cost |
|-----------|---------|------|
| STM32F411 Black Pill | Safety layer (state machine, sensors, brake GPIO, E-stop) | ~$5 |
| Makerbase VESC MINI 6.7 | FOC motor driver (UART from STM32) | ~$45–55 |
| 57mm BLDC planetary gearmotor | Slack management, 24V, power-off brake | ~$85–120 |
| Seeed XIAO ESP32-S3 Sense | Voice + CV + BLE (camera+mic built in) | ~$15 |
| HX711 + 50kg load cell | Rope tension via sheave reaction force | ~$8 |
| AS5048A magnetic encoder | Spool position / payout | ~$12 |
| E-stop button (40mm, NC, twist-release) | Physical emergency stop | ~$10–12 |
| Wearable voice unit (nRF52 + PDM mic) | Harness BLE mic for climber commands | ~$8–15 |
| Lead Solo mechanical design | Centrifugal clutch catch | Machined |

**Total BOM:** ~$246–309 (hardware not yet purchased). **Mechanical base:** [Lead Solo](https://fitdesignawards.com/winners/fit/2024/257/0/) by Tom McNeill — 200mm brake drum, 600mm rope spool, 6061-T6 housing. Full BOM and wiring: [`docs/ARIA_SETUP.md`](docs/ARIA_SETUP.md).

---

## Software

| Path | What it does |
|------|--------------|
| **Dashboard & models** | |
| `aria_dashboard.py` | Streamlit virtual testing (static, dynamic drop, state machine) + design suggestions + **Hardware Bring-Up checklist**, **PID tuner**, and **live Test Session logger/replay** |
| `aria_models/` | Physics and state machine (static tests, drop sim, false-trip check) |
| `START_DASHBOARD.bat` | One-click dashboard on Windows (sets up local Python if needed) |
| **App** | |
| `aria-climb/` | React Native app — Gym Mode (iPad) + Climber Mode (phone), Firebase + BLE (sessions, incidents, device control, provisioning, calibration, device health) |
| **Firmware** | |
| `firmware/stm32/aria_main.cpp` | STM32 state machine, brake GPIO, VESC UART (no FOC on STM32), PID tension loop, UART command handler (`CMD:PAUSE/RESUME/LOCKOUT/RETURN/CALIBRATE`) |
| `firmware/stm32/safety.cpp` | Watchdog + fault recovery + power-on safety boot sequence (brake first, then sensors, then motor) |
| `firmware/stm32/calibration.cpp` | HX711 calibration + motor alignment |
| `firmware/esp32/aria_esp32_firmware.ino` | Voice + CV + BLE + UART intelligence layer |
| `firmware/esp32/aria_wearable/` | Wearable BLE mic firmware |
| **Tools** | |
| `tools/aria_simulator.py` | Headless state machine simulator |
| `tools/aria_monitor.py` | Real-time serial monitor for STM32 |
| `tools/aria_test_harness.py` | Automated STM32 test suite |
| `tools/aria_pid_tuner.py` | Motor PID tuning |
| `tools/aria_collect_audio.py` | Edge Impulse wake word dataset recorder |

---

## Quick Start (No Hardware Required)

```bash
# Clone
git clone https://github.com/jonathan-kofman/aria-auto-belay
cd aria-auto-belay
```

**Get everything working (one-time):**

- **Dashboard (Windows, no system Python):** Double‑click `START_DASHBOARD.bat`. It creates `.python\` and installs deps from `requirements.txt` (streamlit, plotly, pyserial, etc.). If you already had the dashboard running but CEM charts or other features failed, run `START_DASHBOARD.bat` again — it will install any missing packages (e.g. plotly).
- **Dashboard (system Python):** `pip install -r requirements.txt` then `streamlit run aria_dashboard.py`.
- **Audio (Edge Impulse):** Double‑click `RECORD_EDGE_IMPULSE_AUDIO.bat`; it will install sounddevice, soundfile, numpy if needed. For the same env as the dashboard, use `.python\python.exe` (run `START_DASHBOARD.bat` once first).
- **Simulator / constants sync:** `python tools/aria_simulator.py`, `python tools/aria_constants_sync.py`. Use `python` or `.python\python.exe` depending on which env you use.

**Virtual testing (dashboard)** — Windows: double‑click `START_DASHBOARD.bat` (or run `run_dashboard.bat`). It sets up local Python and launches the Streamlit dashboard for static, dynamic drop, and state-machine tests, plus:

- **Hardware Bring-Up**: pre‑power‑on wiring/ESTOP checklist with per‑step status and readiness %.
- **PID Tuner**: Kp/Ki/Kd sliders, simple step‑response preview, and “Copy to firmware” that updates `tensionPID` gains in `firmware/stm32/aria_main.cpp`.
- **Test Session**: live serial streaming from STM32 (tension, rope position, state), JSON session recording, replay with charts, and optional Firebase push.

See [`CURSOR_GUIDE.md`](CURSOR_GUIDE.md) for details.

**Simulator (CLI)** — `python tools/aria_simulator.py` then e.g. `scenario climb`, `voice take`, `status`.

**ARIA Climb app** — `cd aria-climb`, `npm install --legacy-peer-deps`, add Firebase `google-services.json`, then `npx expo run:android`. See [`aria-climb/README.md`](aria-climb/README.md) and [`aria-climb/RUN_APP_TONIGHT.md`](aria-climb/RUN_APP_TONIGHT.md).

---

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Mechanical — Lead Solo design, housing CAD, sheave, mount | In progress |
| 2 | Motor + VESC + brake — slack management firmware | In progress |
| 3 | Voice — Edge Impulse wake words + wearable BLE | In progress |
| 4 | Camera safety monitoring — zone intrusion, session detection | Planned |
| 5 | Full fusion — BLE app, climber ID, bolt map UI, rope tracking | Planned |

Dashboard, simulator, test harness, PID tuner, and audio collector exist. Full status: [`docs/ARIA_SETUP.md`](docs/ARIA_SETUP.md).

---

## Flashing the STM32

**Prerequisites:** Arduino IDE 2.x (or platformio) with STM32 board package, ST-Link V2 (SWDIO→PA13, SWCLK→PA14, GND, 3.3V).

**Board:** Generic STM32F4 Series → STM32F411CEUx, upload method: STLink.

**First boot:** Serial at 115200; type `cal` within 3 seconds for HX711 calibration. Motor alignment runs once and saves to EEPROM. STM32 talks to VESC over UART (no FOC on STM32). See [`docs/ARIA_SETUP.md`](docs/ARIA_SETUP.md) for full setup.

---

## Flashing the ESP32

**Prerequisites:**
- Arduino IDE 2.x with ESP32 board package (Espressif)
- Board: XIAO_ESP32S3
- Edge Impulse library (see `docs/edge_impulse_setup.md`)

---

## Wiring

STM32 connects to AS5048A (SPI), HX711 (GPIO), VESC MINI (UART2), and ESP32-S3 (UART). Brake coil via MOSFET; E-stop NC in series with brake circuit. Full wiring and power architecture: **[`docs/ARIA_SETUP.md`](docs/ARIA_SETUP.md)**.

---

## Contributing

This is an active build. If you have experience with:
- SimpleFOC and STM32 motor control
- ANSI Z359.14 fall protection standards
- Indoor climbing gym operations

Feel free to open an issue or reach out.

---

## Context

**Why is there no lead auto belay in the US?**
- US product liability environment is significantly more demanding than Europe
- ANSI Z359.14 certification is a multi-month, five-figure program
- ProGrade (the only existing product) is a 3-person Italian company with no US distribution
- The $6M auto belay lawsuit verdict in 2023 raised the barrier further

ARIA is a research and development prototype. It is **not** a certified safety device. Do not use for real climbing without appropriate engineering validation and certification.

---

## License

MIT License — see [LICENSE](LICENSE)

Hardware designs and firmware are provided for research and educational purposes. This is not a certified safety device.

---

*Built at Northeastern University — MEng Advanced & Intelligent Manufacturing*
