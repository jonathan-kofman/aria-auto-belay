# ARIA — Autonomous Rope Intelligence Architecture

**A hybrid mechanical + AI-assisted lead climbing auto belay device**

[![Status](https://img.shields.io/badge/status-building-yellow)](https://github.com)
[![Phase](https://img.shields.io/badge/phase-2%20software%20complete-blue)](https://github.com)
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
│  SimpleFOC motor FOC  │  HX711 tension  │  AS5048A encoder│
│  ARIA state machine   │  IWDG watchdog  │  Fault recovery  │
│  UART ← commands      │  UART → state   │                  │
└─────────────────────────────────────────────────────────┘
                           │ UART
┌─────────────────────────────────────────────────────────┐
│           XIAO ESP32-S3 Sense — INTELLIGENCE LAYER       │
│  Edge Impulse wake words  │  OV2640 clip detection       │
│  FreeRTOS: voice task     │  CV task  │  UART task        │
└─────────────────────────────────────────────────────────┘
```

**Fail-safe principle:** If the ESP32 crashes → STM32 holds safe tension independently. If the STM32 motor faults → centrifugal clutch catches falls mechanically. If power cuts → clutch locks.

---

## State Machine

```
IDLE → CLIMBING → CLIPPING (auto) → CLIMBING
              ↓ voice
           TAKE / REST / LOWER / WATCH ME / UP
              ↓ any fault
           ESTOP (latch, power cycle to clear)
```

| State | Entry | Motor | Exit |
|-------|-------|-------|------|
| IDLE | No climber | Off | CV detects climber + tension > 15N |
| CLIMBING | Climber on wall | PID: 40N tension | Voice or clip detected |
| CLIPPING | CV: clip gesture | Fast payout 0.65m | Auto after clip duration |
| TAKE | Voice + load cell | Lock spool | "climbing" voice or upward movement |
| REST | Voice "rest" | Hold position | "climbing" voice or 10min timeout |
| LOWER | Voice "lower" | 0.5 m/s descent | Tension drops < 15N |
| WATCH ME | Voice "watch me" | PID: 25N (tighter) | "climbing" voice or 3min timeout |
| UP | Voice "up" | Near-zero tension | "climbing" voice |
| ESTOP | Button or fault | Motor disabled | Power cycle |

---

## Hardware

| Component | Purpose | Cost |
|-----------|---------|------|
| STM32F411 Black Pill | Safety/motor MCU | ~$8 |
| ST-Link V2 | Flash STM32 | ~$10 |
| Seeed XIAO ESP32-S3 Sense | Voice + CV (camera+mic built in) | ~$20 |
| HX711 + 50kg load cell | Rope tension sensing | ~$10 |
| AS5048A magnetic encoder | Spool speed/position | ~$12 |
| T-Motor GB54-2 BLDC + 30:1 gearbox | Slack management | ~$160 |
| Lead Solo mechanical design | Centrifugal clutch catch | Machined |

**Mechanical base:** [Lead Solo](https://fitdesignawards.com/winners/fit/2024/257/0/) by Tom McNeill — 200mm brake drum, 600mm rope spool, 6061 aluminium housing. Published 2024, not commercially available.

---

## Software

| File | What it does |
|------|-------------|
| `firmware/stm32/aria_main.cpp` | STM32 state machine + SimpleFOC motor control |
| `firmware/stm32/safety.cpp` | Hardware watchdog + 5-fault recovery system |
| `firmware/stm32/calibration.cpp` | HX711 multi-point calibration + motor alignment |
| `firmware/esp32/aria_esp32_firmware.ino` | Voice + CV + UART intelligence layer |
| `tools/aria_simulator.py` | Full state machine simulator — **run this first** |
| `tools/aria_monitor.py` | Real-time serial dashboard for STM32 |
| `tools/aria_test_harness.py` | Automated state transition test suite |
| `tools/aria_pid_tuner.py` | Auto-tune PID gains via step response |
| `tools/aria_collect_audio.py` | Edge Impulse wake word dataset recorder |

---

## Quick Start (No Hardware Required)

```bash
# Clone
git clone https://github.com/yourusername/aria-auto-belay
cd aria-auto-belay

# Run the simulator
python3 tools/aria_simulator.py

# Try scenarios
ARIA> scenario climb
ARIA> scenario fall
ARIA> scenario watch_me

# Or inject manually
ARIA> voice take
ARIA> sensor load_cell_n=680
ARIA> status
```

---

## Build Phases

- [x] **Phase 1 — Software** (complete): Full firmware stack, simulator, test suite
- [ ] **Phase 2 — Mechanical**: Lead Solo centrifugal clutch prototype at Northeastern
- [ ] **Phase 3 — Motor**: BLDC + gearbox + STM32 PID tension control
- [ ] **Phase 4 — Voice**: Edge Impulse wake words on ESP32
- [ ] **Phase 5 — Vision**: Clipping gesture detection via OV2640
- [ ] **Phase 6 — Integration**: Full system on real wall

---

## Flashing the STM32

**Prerequisites:**
- Arduino IDE 2.x with STM32 board package
- SimpleFOC library (Library Manager: "Simple Field Oriented Control")
- ST-Link V2 connected to Black Pill (SWDIO→PA13, SWCLK→PA14, GND, 3.3V)

**Board settings:**
- Board: Generic STM32F4 Series → STM32F411CEUx
- Upload method: STLink

**First boot:**
1. Open serial monitor at 115200
2. Type `cal` within 3 seconds for HX711 calibration
3. Motor alignment runs automatically (saves to EEPROM, skips next boot)

---

## Flashing the ESP32

**Prerequisites:**
- Arduino IDE 2.x with ESP32 board package (Espressif)
- Board: XIAO_ESP32S3
- Edge Impulse library (see `docs/edge_impulse_setup.md`)

---

## Wiring

```
STM32 Black Pill ←→ AS5048A Encoder
  PA4 (SPI CS)   →  CS
  PA5 (SCK)      →  CLK  
  PA6 (MISO)     →  MISO
  PA7 (MOSI)     →  MOSI

STM32 Black Pill ←→ HX711
  PB0            →  DOUT
  PB1            →  SCK

STM32 Black Pill ←→ Motor Driver
  PA8            →  Phase A PWM
  PA9            →  Phase B PWM
  PA10           →  Phase C PWM
  PB10           →  Enable

STM32 Black Pill ←→ ESP32-S3
  PA2 (UART TX)  →  GPIO44 (RX)
  PA3 (UART RX)  →  GPIO43 (TX)
  GND            →  GND
```

Full wiring guide: [`docs/ARIA_SETUP.md`](docs/ARIA_SETUP.md)

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
