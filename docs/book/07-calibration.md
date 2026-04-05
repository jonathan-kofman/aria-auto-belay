[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Firmware](./06-the-firmware.md) &middot; [Next: The Gotchas &rarr;](./08-the-gotchas.md)

# Calibration

## First Power-On Checklist

Before applying 12V power for the first time after a complete build:

- [ ] All wiring inspected visually (no loose connections, no bare wire touching housing)
- [ ] Multimeter confirms no short between 12V and GND on the power bus
- [ ] STM32 and ESP32 both flash and boot correctly via USB (tested on bench)
- [ ] HX711 calibration values are flashed (see [Chapter 6](./06-the-firmware.md))
- [ ] Brake solenoid wiring confirmed: MOSFET driver, flyback diode polarity correct
- [ ] Motor phases connected to VESC (3-phase wires)
- [ ] VESC configured for FOC mode with correct motor parameters
- [ ] Rope is installed on spool but **not loaded** (no weight on rope)
- [ ] Housing is open or accessible for inspection during first power-on
- [ ] Fire extinguisher accessible (precaution for first power-on of new electronics)

**Power on sequence:**

1. Apply 12V. Listen for any unusual sounds (buzzing, clicking, arcing).
2. Confirm both MCU boards boot (serial output or LED indicators).
3. Confirm brake is engaged (shaft does not rotate by hand).
4. Confirm LED strip illuminates (if wired).
5. Check BLE advertisement from ESP32 (use companion app or nRF Connect).

## Sensor Verification

### HX711 Load Cell

| Test | Expected | How to Check |
|---|---|---|
| Zero reading (no load) | ~0 N (+/- 0.5 N) | Serial monitor: observe tension readout with rope slack |
| Known weight | Within 2% of actual | Hang a known weight (e.g. 5 kg = 49 N) from rope, compare reading |
| Repeatability | Same reading 10x | Remove and reapply weight 10 times, confirm consistent |
| Response time | < 100 ms | Pull rope sharply, observe tension spike timing on serial |

> **Tip:** If readings are wildly off, re-run the `cal` command (see [Chapter 6](./06-the-firmware.md)). The most common cause is a wrong `HX711_OFFSET` or `HX711_SCALE` value.

### Voice Recognition (Edge Impulse)

| Test | Expected | How to Check |
|---|---|---|
| "Take" command | Confidence >= 0.85 | Say "take" at normal volume from 3m; check serial output |
| "Slack" command | Confidence >= 0.85 | Same |
| "Lower" command | Confidence >= 0.85 | Same |
| "Watch me" command | Confidence >= 0.85 | Same |
| Background noise rejection | No false positives | Play gym ambient noise for 60 seconds; confirm no state changes |
| Distance | Reliable at {e.g. 5m} | Test at increasing distances from microphone |

### Camera / CV (Clip Detection)

| Test | Expected | How to Check |
|---|---|---|
| Frame capture | Clear image | Serial output or save test frame to SD/serial |
| Known clip action | Confidence >= 0.75 | Simulate clipping motion in camera FOV |
| False positive rejection | No triggers on non-clip motion | Wave hand, walk past camera; confirm no CLIPPING state |

## Actuator Verification

### BLDC Motor + VESC

| Test | Expected | How to Check |
|---|---|---|
| Free spin (no load) | Motor spins smoothly in both directions | Serial command or VESC tool |
| Stall torque | Holds at target tension | Apply load to rope, confirm PID holds {e.g. 40 N} |
| Direction | Correct for take-up and payout | Verify rope winds in the correct direction for each mode |
| Current limit | Does not exceed VESC limit | Monitor VESC current during stall test |

### Brake Solenoid

| Test | Expected | How to Check |
|---|---|---|
| Engaged (power off) | Shaft locked, cannot rotate | Try to rotate shaft by hand with 12V disconnected |
| Released (power on) | Shaft free | Apply 12V to solenoid, shaft should rotate freely |
| Transition time | < 50 ms | Oscilloscope on GPIO + mechanical observation |
| Heat | Solenoid warm but not hot after 10 min energized | Touch test; measure coil temp if concerned |

### Ratchet and Clutch (Mechanical)

| Test | Expected | How to Check |
|---|---|---|
| Ratchet engagement | Shaft locks in payout direction | Rotate spool by hand in payout direction; should catch |
| Ratchet release | Shaft free in take-up direction | Rotate in take-up direction; should be free |
| Clutch engagement | Engages at high speed | Spin shaft rapidly by hand or with motor burst |
| Clutch release | Disengages at low speed | Slow rotation should not engage clutch |

## Calibration Procedures

### 1. HX711 Load Cell Calibration

Already covered in [Chapter 6](./06-the-firmware.md) under First-Time Setup. Summary:

1. Send `cal` over serial at 115200 baud.
2. Follow prompts: zero with no load, apply known weight.
3. Record `HX711_OFFSET` and `HX711_SCALE`.
4. Update firmware and reflash.

### 2. PID Tension Loop Tuning

> **Warning:** PID tuning must be performed on real hardware. The values in firmware (`Kp=0.022, Ki=0.413, Kd=0.0005`) are the result of a systematic tuning process. Do not adjust these casually.

If re-tuning is required (new motor, new gearbox, different rope):

1. Run `python tools/aria_pid_tuner.py` -- this automates a Kp/Ki/Kd sweep.
2. The tuner connects via serial to the STM32 and applies test loads.
3. It outputs recommended gains with stability metrics.
4. Update `tensionPID_kp`, `tensionPID_ki`, `tensionPID_kd` in firmware.
5. Reflash and verify step response (apply sudden load, observe settling time).

### 3. VESC Motor Configuration

1. Connect VESC to PC via USB.
2. Open VESC Tool.
3. Run motor detection wizard (measures resistance, inductance, flux linkage).
4. Set current limits appropriate for your motor.
5. Enable UART communication at 115200 baud.
6. Save configuration.

### 4. Voice Model Threshold Tuning

The default confidence threshold is 0.85. If experiencing too many false positives in a noisy gym:

1. Increase `VOICE_CONFIDENCE_MIN` to 0.90 or 0.92.
2. Reflash ESP32.
3. Retest with the voice command tests above.

If commands are not being recognized:

1. Check microphone placement and orientation.
2. Lower threshold to 0.80 (minimum safe value -- below this, false positives increase significantly).
3. Consider retraining the Edge Impulse model with gym-specific audio samples.

## Performance Validation

After all calibrations, run these end-to-end tests before allowing any climbing:

- [ ] **IDLE to CLIMBING**: Apply > 15 N tension to rope. System should transition to CLIMBING and hold 40 N.
- [ ] **Voice "take"**: Say "take". System should transition to TAKE and retract rope until tension reaches 200 N confirmation.
- [ ] **Voice "lower"**: Say "lower". System should pay out rope smoothly. Exits to IDLE when tension drops below 15 N.
- [ ] **Fall arrest (simulated)**: Drop a {e.g. 10 kg} weight from {e.g. 2 m} above last clip. Ratchet should catch. Tension should spike above 400 N. System should transition to FALL_ARREST.
- [ ] **E-stop**: Press E-stop (if installed) or send ESTOP command. Brake should engage within 50 ms. Motor should stop. System should require 2-second hold of reset to exit ESTOP.
- [ ] **Power loss**: Disconnect 12V. Brake should engage immediately (power-off brake). Ratchet and clutch should hold any load.
- [ ] **Watchdog**: Deliberately hang the STM32 main loop (test firmware). Watchdog should reset MCU within 500 ms. Brake should be engaged after reset.

> **Warning:** Do not allow climbing until all performance validation tests pass. ARIA is a safety-critical device. An untested unit is an unsafe unit.

[Next: The Gotchas &rarr;](./08-the-gotchas.md)
