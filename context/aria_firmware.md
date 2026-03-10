# ARIA Firmware Architecture & State Machine

## Two-Layer Architecture

### STM32F411 — Safety Layer (C++)
**Never bypassed. Owns:** watchdog timer, fault detection, motor emergency stop,
clutch lock/unlock, wiring verification on boot.

Files:
- `firmware/stm32/aria_main.cpp` — main loop, state validation
- `firmware/stm32/safety.cpp/.h` — fault logic, E-stop conditions
- `firmware/stm32/calibration.cpp` — motor/sensor calibration routines
- `firmware/stm32/wiring_verify.cpp/.h` — boot-time wiring checks

Safety conditions that trigger E-stop (motor off, clutch locked):
- Rope tension exceeds threshold (fall detected)
- Watchdog timeout (ESP32 comms lost)
- Motor overcurrent
- Any sensor out-of-range on boot

### XIAO ESP32-S3 — Intelligence Layer (Arduino/C++)
**Owns:** state orchestration, voice command processing, BLE, CV, HMI comms.

Files:
- `firmware/esp32/aria_esp32_firmware.ino` — main intelligence loop
- `firmware/esp32/aria_wearable/aria_wearable.ino` — chest-strap BLE unit

Communication: UART between ESP32 and STM32.
ESP32 sends state transition requests → STM32 validates and executes.

---

## System States

### IDLE
**What it means:** Device powered, no climber present.
**Motor:** Off. Clutch: Unlocked (rope feeds freely).
**Entry condition:** Boot complete, no load on rope.
**Exit condition:** Rope tension rises (climber grabs rope) → CLIMBING.

### CLIMBING
**What it means:** Climber is actively moving up.
**Motor:** Running — taking up slack as climber ascends.
**PID:** Active, maintaining slight tension to prevent rope pile.
**Exit conditions:**
- Climber pauses at bolt → CLIPPING
- Voice "take" → TAKE
- Fall detected → immediate clutch lock (safety layer, not a state)

### CLIPPING
**What it means:** Climber has paused to clip a quickdraw.
**Motor:** Slow/stopped. Extra slack fed out.
**Detection:** Rope stops moving for >N seconds.
**Exit condition:** Rope tension resumes upward movement → CLIMBING.

### TAKE
**What it means:** Climber has requested "take" — device holds current rope position.
**Motor:** Holds. Clutch: engaged to prevent rope pay-out.
**Trigger:** Voice command "take" OR button press on wearable.
**Exit condition:** Voice "climbing" or "up" → CLIMBING / UP.

### REST
**What it means:** Climber is resting on the rope (sitting into harness).
**Motor:** Holding tension.
**Detection:** Static load, no upward movement.
**Exit condition:** Load releases → CLIMBING or LOWER.

### LOWER
**What it means:** Controlled descent.
**Motor:** Controlled pay-out at descent rate.
**Safety:** STM32 monitors descent speed — exceeds threshold → E-stop.
**Trigger:** Voice "lower" OR automatic after REST + release.
**Exit condition:** Climber reaches ground → IDLE.

### WATCH_ME
**What it means:** Demo / attention mode. Signals via LED that device is active.
**Trigger:** Voice "watch me".
**Motor:** Standby.

### UP
**What it means:** Powered ascent assist — motor actively pulls rope up.
**Motor:** Full take-up speed.
**Trigger:** Voice "up".
**Exit condition:** Slack gone or voice "take"/"rest".

---

## Voice Commands → State Transitions
| Voice Command | From State      | To State   |
|---------------|-----------------|------------|
| "take"        | CLIMBING, REST  | TAKE       |
| "lower"       | TAKE, REST      | LOWER      |
| "up"          | TAKE, IDLE      | UP         |
| "slack"       | TAKE            | CLIPPING   |
| "rest"        | CLIMBING        | REST       |
| "watch me"    | IDLE            | WATCH_ME   |

## Edge Impulse Voice Model
- 8 classes: lower, noise, rest, slack, take, unknown, up, watch_me
- Dataset: dataset/ (audio samples per class)
- Training: Edge Impulse cloud (see docs/edge_impulse_setup.md)
- Collection tool: tools/aria_collect_audio.py

## Python Simulation / Testing
- Full simulator: tools/aria_simulator.py
- State machine model: aria_models/state_machine.py + state_machine.py (root)
- PID tuner: tools/aria_pid_tuner.py
- HIL test: tools/aria_hil_test.py
- Test harness: tools/aria_test_harness.py

## CEM (Computer Engineering Model) Layer
- cem_core.py — core CEM simulation engine
- aria_cem.py — main CEM entry point
- aria_cem_tab.py — dashboard CEM tab
- aria_fault_behavior.py — fault injection and behavior modeling
- cem_design_history.json — versioned design decision log

## Build Phases
| Phase | Scope                        | Status         |
|-------|------------------------------|----------------|
| 1     | Mechanical only              | In progress (CAD) |
| 2     | Motor + PID                  | Software building |
| 3     | Voice commands               | Software building |
| 4     | CV (zone intrusion)          | Planned        |
| 5     | Full fusion (all layers)     | Planned        |
