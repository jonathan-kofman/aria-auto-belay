# Bill of Materials

## ARIA Auto-Belay Hardware BOM

The ARIA device is a wall-mounted lead climbing auto-belay. It sits behind the climbing wall with only a flush rope port, LED status strip, and iPad HMI visible on the wall face. The mechanical base is the Lead Solo design by Tom McNeill -- a centrifugal clutch catch mechanism that operates with zero electronics.

### Electronics

| Component | Part | Purpose | Est. Cost |
|-----------|------|---------|-----------|
| Safety MCU | STM32F411 Black Pill | State machine, brake GPIO, HX711 tension, VESC UART, E-stop, fault recovery | ~$5 |
| Motor Driver | Makerbase VESC MINI 6.7 | FOC motor control via UART from STM32. No FOC runs on the STM32. | ~$45-55 |
| Intelligence MCU | Seeed XIAO ESP32-S3 Sense | Voice (Edge Impulse), computer vision, BLE, UART bridge to STM32. Camera + mic built in. | ~$15 |
| Load Cell | HX711 + 50kg load cell | Rope tension measurement via sheave reaction force | ~$8 |
| Encoder | AS5048A magnetic encoder | Spool position / rope payout tracking (SPI to STM32) | ~$12 |
| E-Stop | 40mm NC twist-release button | Physical emergency stop. NC in series with brake circuit. | ~$10-12 |
| Wearable | nRF52 + PDM mic (harness BLE mic) | Climber voice commands from harness | ~$8-15 |

### Mechanical

| Component | Specification | Material | Source |
|-----------|--------------|----------|--------|
| Housing | 700 x 680 x 344 mm, 10mm min wall | 6061-T6 Aluminum | CNC machined |
| Rope Spool | 600mm diameter | 6061-T6 Aluminum | CNC machined |
| Brake Drum | 200mm diameter (centrifugal clutch) | Cast iron / steel | Machined |
| Ratchet Ring | 213mm OD, 120.2mm bore, 21mm thick, 24 asymmetric teeth | Steel | CNC machined |
| Catch Pawl | 6mm tip width, 9mm thick, 45mm arm, 3mm engagement | Tool steel (heat treated) | CNC machined |
| Cam Collar | Tapered engagement surface | Steel | CNC machined |
| Rope Guide | Roller + bracket assembly | 6061-T6 Aluminum | CNC machined |
| Motor | 57mm BLDC planetary gearmotor, 24V, power-off brake, 30:1 ratio | -- | Purchased |
| Bearings | 47.2mm OD, 55mm shoulder OD, 3mm shoulder height | -- | Purchased |
| Shaft | 20mm diameter, 344mm span | Steel | Purchased/machined |
| Fasteners | Various | Stainless steel | Purchased |

### Drivetrain

```
Motor (57mm BLDC, 24V)
    |
    v
Planetary gearbox (30:1)
    |
    v
One-way bearing (motor cannot backdrive clutch)
    |
    v
Rope spool (600mm dia, 6061 Al)
    |
    v
Centrifugal clutch + brake drum (200mm dia)
```

### Safety Architecture

The system has three independent layers of fall protection:

1. **Mechanical layer** (no power required): Centrifugal clutch engages on rope speed > threshold. Works with all electronics dead.
2. **STM32 safety layer** (battery backup capable): Brake GPIO, E-stop monitoring, state machine, VESC fault detection. Independent of ESP32.
3. **ESP32 intelligence layer** (optional): Voice commands, computer vision, BLE app communication. If it crashes, STM32 holds safe tension.

**Fail-safe chain:**
- ESP32 crash -> STM32 holds tension independently
- STM32 / VESC fault -> Brake engages, centrifugal clutch catches falls mechanically
- Total power loss -> Power-off brake engages, clutch controls descent

### Critical Constants (Firmware + Simulation)

These values must stay in sync across `firmware/stm32/aria_main.cpp`, `aria_models/state_machine.py`, and `tools/aria_simulator.py`:

| Constant | Value | Notes |
|----------|-------|-------|
| TENSION_BASELINE_N | 40.0 | PID target during CLIMBING state |
| TENSION_TAKE_THRESHOLD_N | 200.0 | Climber weighting rope -> confirm TAKE |
| TENSION_FALL_THRESHOLD_N | 400.0 | Fall detection trigger |
| VOICE_CONFIDENCE_MIN | 0.85 | Edge Impulse wake word threshold |
| ROPE_SPEED_FALL_MS | 2.0 | Fall speed detection (m/s) |

### Estimated Total BOM Cost

**~$246-309** for electronics and purchased components. Machined parts (housing, spool, brake drum, ratchet ring) are additional -- these are designed and manufactured through the ARIA-OS pipeline itself.
