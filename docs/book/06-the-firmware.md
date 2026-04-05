[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Build](./05-the-build.md) &middot; [Next: Calibration &rarr;](./07-calibration.md)

# The Firmware

## Platform Table

| MCU | Role | Framework | Language | Flash Method |
|---|---|---|---|---|
| STM32 | Safety layer | PlatformIO / Arduino | C++ | USB (ST-Link or built-in bootloader) |
| ESP32 | Intelligence layer | Arduino IDE / PlatformIO | C++ (Arduino) | USB serial |

## First Flash

### STM32 (Safety Layer)

1. Connect STM32 board to PC via USB.
2. Open `firmware/stm32/aria_main.cpp` in Arduino IDE or PlatformIO.
3. Install required libraries:
   - SimpleFOC
   - HX711 (by bogde or compatible)
4. Select the correct board and port.
5. Flash.
6. Open serial monitor at 115200 baud.
7. Confirm boot message: you should see state machine initialization and an IDLE state report.

### ESP32 (Intelligence Layer)

1. Connect ESP32 board to PC via USB.
2. Open `firmware/esp32/aria_esp32_firmware.ino` in Arduino IDE or PlatformIO.
3. Install required libraries:
   - Edge Impulse inference SDK (for voice model)
   - BLE library (included with ESP32 Arduino core)
   - Camera driver (if applicable to your module)
4. Select ESP32 board and port.
5. Flash.
6. Open serial monitor at 115200 baud.
7. Confirm boot: BLE should advertise, UART bridge should report ready.

> **Tip:** Flash both boards on the bench via USB before installing them inside the housing. It is much harder to reach USB ports once the housing is closed.

## Configuration

### STM32 First-Time Setup

The HX711 load cell requires calibration values specific to your hardware:

1. Flash `aria_main.cpp` with default `HX711_OFFSET` and `HX711_SCALE` values.
2. Open serial monitor at 115200.
3. Send `cal` command via serial.
4. The firmware enters calibration mode: it will print raw ADC values.
5. Follow the on-screen prompts to zero the load cell (no load) and apply a known weight.
6. Copy the printed `HX711_OFFSET` and `HX711_SCALE` values.
7. Update the constants in `aria_main.cpp`.
8. Reflash.

### Firmware Constants

These constants must stay in sync across STM32 firmware, ESP32 firmware, and the Python state machine model. Run `python tools/aria_constants_sync.py --verbose` to verify alignment.

| Constant | Value | Unit | Description |
|---|---|---|---|
| `TENSION_CLIMB_MIN_N` | 15.0 | N | Min tension to enter CLIMBING from IDLE |
| `TENSION_TARGET_N` | 40.0 | N | PID target during CLIMBING |
| `TENSION_TIGHT_N` | 60.0 | N | Tight tension in WATCH_ME state |
| `TENSION_TAKE_CONFIRM_N` | 200.0 | N | Min tension to confirm TAKE after voice |
| `TENSION_FALL_THRESHOLD_N` | 400.0 | N | Fall detection threshold |
| `TENSION_LOWER_EXIT_N` | 15.0 | N | Tension below which LOWER returns to IDLE |
| `ROPE_SPEED_FALL_MS` | 2.0 | m/s | Rope speed that confirms a fall |
| `VOICE_CONFIDENCE_MIN` | 0.85 | -- | Minimum Edge Impulse confidence to act |
| `CLIP_DETECT_CONFIDENCE` | 0.75 | -- | Minimum CV confidence for clip detection |
| `CLIP_PAYOUT_M` | 0.65 | m | Rope payout during CLIPPING state |
| `REST_TIMEOUT_S` | 600.0 | s | Auto-exit from REST after 10 minutes |
| `WATCH_ME_TIMEOUT_S` | 180.0 | s | Auto-exit from WATCH_ME after 3 minutes |
| `ZONE_PAUSE_TIMEOUT_S` | 10.0 | s | Zone intrusion pause auto-resume |
| `ESTOP_BRAKE_DELAY_MS` | 50.0 | ms | Max delay from ESTOP to brake engage |
| `WATCHDOG_TIMEOUT_MS` | 500.0 | ms | STM32 hardware watchdog timeout |
| `TAKE_CONFIRM_WINDOW_S` | 0.5 | s | Window after voice "take" for load confirm |
| `ESTOP_RESET_HOLD_S` | 2.0 | s | Hold reset button for 2s to exit ESTOP |

### PID Gains

> **Warning:** PID gains are hardware-validated values from `aria_pid_tuner`. Do not change these without re-running the PID tuning procedure on real hardware. These are marked `NEVER_PATCH` in the constants sync tool.

| Gain | Value | Notes |
|---|---|---|
| `tensionPID_kp` | 0.022 | Proportional; safe for 10V limit at 360N max error |
| `tensionPID_ki` | 0.413 | Integral |
| `tensionPID_kd` | 0.0005 | Derivative |

The Python simulator uses different gains (`Kp=2.5, Ki=0.8, Kd=0.1`) that are normalized for a +/- 100 output range. These are simulation-only values and must not be used in firmware.

## Firmware Architecture

### STM32 Directory

```
firmware/stm32/
  aria_main.cpp        # 524 lines: state machine, PID loop, motor control, UART handler
  safety.cpp           # 404 lines: watchdog, fault recovery, power-on boot sequence
```

### ESP32 Directory

```
firmware/esp32/
  aria_esp32_firmware.ino     # Main firmware: voice, CV, BLE, UART bridge
  aria_wearable/
    aria_wearable.ino         # Wearable companion firmware (BLE to phone)
```

### Python State Machine Mirror

```
aria_models/
  state_machine.py     # 11-state machine that MUST mirror STM32 exactly
```

## Key Modules

### STM32: aria_main.cpp

- **State Machine**: 11 states: IDLE, CLIMBING, CLIPPING, TAKE, REST, LOWER, WATCH_ME, UP, CLIMBING_PAUSED, FALL_ARREST, ESTOP
- **Motor Modes**: Each state maps to a motor mode (OFF, TENSION, PAYOUT_FAST, RETRACT_HOLD, HOLD, PAYOUT_SLOW, TENSION_TIGHT, UP_DRIVE)
- **PID Loop**: Runs at {e.g. 1 kHz}. Reads HX711 tension, computes PID output, sends torque command to VESC via UART.
- **UART Command Handler**: Receives commands from ESP32 (voice results, CV results). Parses and triggers state transitions.
- **Brake Control**: GPIO pin drives MOSFET for brake solenoid. Brake engaged = GPIO LOW (solenoid de-energized, spring pushes brake on). Brake released = GPIO HIGH.

### STM32: safety.cpp

- **Watchdog**: 500 ms hardware watchdog. If main loop hangs, watchdog resets the MCU. On reset, the brake is engaged (power-off default).
- **Fault Recovery**: Detects overcurrent, sensor disconnect, and communication loss. Transitions to ESTOP on fault.
- **Power-On Boot**: On power-up, brake is engaged, motor is off, system enters IDLE. Requires explicit operator action to begin.

### ESP32: aria_esp32_firmware.ino

- **Voice Model**: Edge Impulse inference. Listens continuously, classifies voice commands with confidence threshold 0.85.
- **CV Model**: Camera captures frames, runs clip detection model. Detects when climber clips into a quickdraw.
- **BLE Service**: Exposes TELEMETRY, COMMAND, and STATUS characteristics. Companion app subscribes to telemetry for real-time display.
- **UART Bridge**: Forwards voice and CV results to STM32. Receives state and telemetry from STM32 for BLE broadcast.

## Communication Protocol

### UART (STM32 <-> ESP32)

- Baud: 115200
- Format: text-based command/response
- Direction: bidirectional

| Direction | Message | Meaning |
|---|---|---|
| ESP32 -> STM32 | `VOICE:TAKE:0.92` | Voice command "take" detected at 92% confidence |
| ESP32 -> STM32 | `VOICE:SLACK:0.88` | Voice command "slack" at 88% |
| ESP32 -> STM32 | `VOICE:LOWER:0.91` | Voice command "lower" at 91% |
| ESP32 -> STM32 | `VOICE:WATCHME:0.87` | Voice command "watch me" at 87% |
| ESP32 -> STM32 | `CV:CLIP:0.80` | Clip detected at 80% confidence |
| STM32 -> ESP32 | `STATE:CLIMBING` | Current state broadcast |
| STM32 -> ESP32 | `TELEM:T=42.3,S=0.5,I=1.2` | Tension (N), rope speed (m/s), motor current (A) |

### BLE (ESP32 <-> Companion App)

- Service UUID: defined in `aria-climb/src/services/ble/bleCharacteristics.ts`
- Characteristics: TELEMETRY (notify), COMMAND (write), STATUS (read/notify)
- Packet format: 20-byte binary with XOR checksum (parsed by `blePacketParser.ts`)

| Characteristic | Direction | Content |
|---|---|---|
| TELEMETRY | ESP32 -> App | State, tension, rope speed, battery, motor current |
| COMMAND | App -> ESP32 | Operator commands (e-stop, reset, configure) |
| STATUS | ESP32 -> App | Device health, firmware version, error flags |

[Next: Calibration &rarr;](./07-calibration.md)
