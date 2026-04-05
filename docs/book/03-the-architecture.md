[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Design](./02-the-design.md) &middot; [Next: Bill of Materials &rarr;](./04-bom.md)

# The Architecture

## System Overview

```
                    CLIMBING WALL (front)
                    =====================
                     [ LED Strip ]  [ Rope Port ]  [ iPad HMI ]
                    ─────────────────────────────────────────────
                              STRUCTURAL BEAM
                    ─────────────────────────────────────────────
                    BEHIND WALL (rear)
                    ┌───────────────────────────────────────────┐
                    │              ARIA HOUSING                  │
                    │           (700 x 680 x 344 mm)            │
                    │                                           │
                    │  ┌─────────┐     ┌──────────────────┐     │
                    │  │  BLDC   │────>│  Planetary Gear   │     │
                    │  │  Motor  │     │     (30:1)        │     │
                    │  └─────────┘     └────────┬─────────┘     │
                    │                           │               │
                    │                    ┌──────v──────┐        │
                    │                    │    SPOOL     │        │
                    │                    │  (600mm dia) │        │
                    │                    │   + Rope     │        │
                    │                    └──────┬──────┘        │
                    │                           │               │
                    │           ┌────────────────┤               │
                    │           │                │               │
                    │    ┌──────v──────┐  ┌──────v──────┐       │
                    │    │  Ratchet    │  │   Brake     │       │
                    │    │  Ring +     │  │   Drum +    │       │
                    │    │  Pawls      │  │   Clutch    │       │
                    │    └─────────────┘  └─────────────┘       │
                    │                                           │
                    │  ┌─────────┐  UART  ┌──────────┐         │
                    │  │  STM32  │<======>│  ESP32   │         │
                    │  │ (safety)│        │ (intel)  │         │
                    │  └────┬────┘        └────┬─────┘         │
                    │       │                  │               │
                    │  HX711 Load Cell    Voice + CV + BLE     │
                    └───────────────────────────────────────────┘
                                               │
                                          BLE  │
                                               v
                                      ┌────────────────┐
                                      │  Companion App  │
                                      │ (React Native)  │
                                      └────────────────┘
```

## Mechanical

The mechanical system is built around a central shaft carrying the rope spool, with braking mechanisms on either side.

| Component | Material | Dimensions | Function |
|---|---|---|---|
| Housing | 6061 Al | 700 x 680 x 344 mm | Structural enclosure; 10 mm wall minimum |
| Spool | 6061 Al | 600 mm dia | Rope storage and payout |
| Ratchet ring | {e.g. 4140 steel} | 213 mm OD, 24 teeth, 21 mm thick | Anti-reverse; prevents spool backdriving |
| Catch pawls (x2) | {e.g. 4140 steel} | 45 mm arm, 6 mm tip, 9 mm thick | Engage ratchet teeth on fall |
| Brake drum | Cast iron / steel | 200 mm dia | Centrifugal clutch engagement surface |
| Cam collar | {e.g. 6061 Al} | {e.g. per CEM output} | Tapered engagement for clutch |
| Rope guide | {e.g. 6061 Al} | {e.g. per CEM output} | Roller guide for rope path |
| Shaft | Steel | 20 mm dia, 344 mm span | Central shaft through spool and bearings |
| Bearings (x2) | Standard | 47.2 mm OD | Support shaft in housing |
| Mounting bosses (x4) | 6061 Al | 30 mm dia, 20 mm tall, 10.5 mm bore | Wall-mount attachment points |

### Bearing and Shaft Layout

- Shaft diameter: 20 mm
- Shaft span: 344 mm (housing depth)
- Bearing OD: 47.2 mm
- Bearing shoulder OD: 55 mm
- Bearing shoulder height: 3 mm
- Spool center: X=350 mm, Y=330 mm from housing origin

### Braking System (Triple Redundant)

1. **Ratchet ring + pawls**: Mechanical anti-reverse. Pawls drop into ratchet teeth when spool tries to backdriven (rope paying out under load). 24 teeth at 100 mm pitch radius, pressure angle 26 deg, module 3 mm. CEM-validated SF >= 8.0 for tooth shear.
2. **Centrifugal clutch on brake drum**: Engages at high rotational speed (fall). Purely mechanical, no electrical input needed.
3. **Power-off brake**: Spring-engaged, electrically released. On power loss, spring forces brake shoes against the drum. Fail-safe by design.

## Electrical

### Component Table

| # | Component | Spec | Qty | Function |
|---|---|---|---|---|
| 1 | STM32 MCU | {e.g. STM32F4xx} | 1 | Safety layer: state machine, PID, brake GPIO, VESC UART |
| 2 | ESP32 MCU | {e.g. ESP32-WROOM-32} | 1 | Intelligence layer: voice, CV, BLE, UART bridge |
| 3 | BLDC Motor | {e.g. per sizing study} | 1 | Rope tension and payout |
| 4 | VESC Motor Controller | {e.g. VESC 6.x} | 1 | FOC motor drive, UART to STM32 |
| 5 | HX711 Load Cell Amp | 24-bit ADC | 1 | Tension measurement |
| 6 | Load Cell | {e.g. 500 N capacity} | 1 | Rope tension sensor |
| 7 | Edge Impulse Voice Model | On ESP32 | 1 | Voice command classification |
| 8 | Camera Module | {e.g. OV2640 or similar} | 1 | Clip detection CV |
| 9 | Power Supply | 12V DC | 1 | System power |
| 10 | LED Strip | WS2812B or similar | 1 | Status indication on wall face |
| 11 | Barrel Jack | 12V input | 1 | Power connector |

### Power Budget

| Component | Typical Draw | Peak Draw | Notes |
|---|---|---|---|
| STM32 | ~50 mA | ~100 mA | Always on |
| ESP32 | ~80 mA | ~240 mA (BLE + WiFi active) | Always on |
| BLDC Motor | {e.g. 500 mA idle} | {e.g. 5 A under load} | Via VESC |
| HX711 | ~1.5 mA | ~1.5 mA | Continuous sampling |
| LED Strip | ~60 mA | ~300 mA | Depends on pattern |
| Camera | ~50 mA | ~100 mA | Active during climbing |
| **Total** | **{e.g. ~750 mA}** | **{e.g. ~6 A}** | 12V supply must handle peak |

### Communication Buses

| Bus | From | To | Baud/Speed | Purpose |
|---|---|---|---|---|
| UART | STM32 | ESP32 | 115200 | State, telemetry, commands |
| UART | STM32 | VESC | {e.g. 115200} | Motor commands, current feedback |
| I2C / SPI | STM32 | HX711 | Clock-driven | Load cell ADC reads |
| BLE | ESP32 | Companion App | BLE 4.2+ | Telemetry, configuration, provisioning |
| GPIO | STM32 | Brake solenoid | Digital out | Brake engage/release |

## Software

ARIA has three software systems:

### 1. STM32 Firmware (Safety Layer)

- SimpleFOC motor control
- HX711 load cell reading
- 11-state state machine (IDLE, CLIMBING, CLIPPING, TAKE, REST, LOWER, WATCH_ME, UP, CLIMBING_PAUSED, FALL_ARREST, ESTOP)
- PID tension control loop (Kp=0.022, Ki=0.413, Kd=0.0005)
- UART command handler (receives from ESP32)
- Hardware watchdog (500 ms timeout)
- Brake GPIO control

### 2. ESP32 Firmware (Intelligence Layer)

- Edge Impulse voice classification ("take", "slack", "lower", "watch me")
- Computer vision clip detection
- BLE service for companion app (telemetry, commands, status characteristics)
- UART bridge to STM32
- WiFi for gym provisioning and OTA updates

### 3. ARIA-OS (CAD Pipeline)

The AI-driven CAD pipeline that designs every mechanical part in the device:
- Natural language to validated STEP files
- 39 parametric CadQuery templates + LLM fallback
- CEM physics validation (safety factors enforced before export)
- Multi-backend routing: CadQuery, Grasshopper, Blender, Fusion 360, AutoCAD
- Visual verification via vision LLM
- Onshape cloud upload, DFM analysis, and manufacturing quotes

### 4. Companion App (aria-climb)

- React Native / Expo
- BLE connection to ESP32 for real-time telemetry
- Gym owner dashboard: device fleet management, provisioning, alerts
- Climber experience: live tension display, session history, QR-based gym onboarding
- Firebase backend for multi-device gym management

## How They Connect

```
Companion App (React Native)
        |
        | BLE (telemetry/commands/status)
        v
    ESP32 (Intelligence)
        |
        | UART 115200 (state sync, voice results, CV results)
        v
    STM32 (Safety)
        |
        |--- UART --> VESC --> BLDC Motor --> Planetary Gear --> Spool
        |--- GPIO --> Brake Solenoid
        |--- I2C/SPI --> HX711 --> Load Cell
        |
        v
    Mechanical System (spool, ratchet, clutch, brake drum)
```

> **Tip:** The STM32 never depends on the ESP32 being alive. If the ESP32 crashes or loses power, the STM32 continues to hold tension and will engage the brake if watchdog conditions are met.

[Next: Bill of Materials &rarr;](./04-bom.md)
