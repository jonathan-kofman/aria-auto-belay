[&larr; Back to Table of Contents](./README.md) &middot; [Previous: Safety](./09-safety.md) &middot; [Next: Appendix &rarr;](./11-appendix.md)

# Operations

## Normal Operation

### Startup Sequence

1. Apply 12V power.
2. Wait for boot (~3 seconds). LED strip should illuminate indicating IDLE state.
3. Confirm BLE is advertising (companion app should discover the device).
4. Verify tension reads ~0 N on serial or companion app (no load on rope).
5. System is ready. Climber ties in and begins climbing.

### During a Climb

The system operates autonomously. No operator input is required during normal climbing.

| State | What Happens | How It Looks |
|---|---|---|
| IDLE | Motor off, waiting for climber | LED: {e.g. solid blue} |
| CLIMBING | PID holds 40 N tension, takes in slack | LED: {e.g. pulsing green} |
| CLIPPING | Pays out 0.65 m slack for clip | LED: {e.g. flashing yellow} |
| TAKE | Retracts rope, confirms at 200 N | LED: {e.g. solid yellow} |
| REST | Holds rope, 10-min timeout | LED: {e.g. slow pulse blue} |
| LOWER | Pays out rope slowly | LED: {e.g. downward chase green} |
| WATCH_ME | Tight tension (60 N), 3-min timeout | LED: {e.g. solid white} |
| UP | Drives climber up | LED: {e.g. upward chase green} |
| CLIMBING_PAUSED | Zone intrusion detected, hold | LED: {e.g. flashing orange} |
| FALL_ARREST | Fall caught, motor off, brake on | LED: {e.g. solid red} |
| ESTOP | Emergency stop, brake engaged | LED: {e.g. flashing red} |

### Shutdown Sequence

1. Confirm no climber is on the rope.
2. Lower any remaining rope to ground.
3. Disconnect 12V power. Brake engages automatically.
4. System is safe to leave unattended.

## Troubleshooting

| Symptom | Check First | Then Check | Fix |
|---|---|---|---|
| No LED on power-on | 12V supply voltage at barrel jack | Fuse in power supply | Replace fuse; verify supply |
| STM32 not booting | USB serial output | 3.3V regulator output | Replace regulator; reflash STM32 |
| ESP32 not booting | USB serial output | 5V rail voltage | Check regulator; reflash ESP32 |
| Tension reads 0 always | HX711 wiring (data + clock) | Load cell connector | Re-seat JST; re-calibrate HX711 |
| Tension reads max always | HX711 offset value | Load cell physical mount | Re-calibrate; check for mechanical binding |
| Motor does not spin | VESC power LED | VESC UART connection to STM32 | Re-configure VESC; check UART wiring |
| Motor runs rough | Phase wire connections | VESC motor detection | Re-crimp phases; re-run detection |
| Voice commands ignored | Microphone wiring | `VOICE_CONFIDENCE_MIN` threshold | Check mic; lower threshold to 0.80 |
| False voice triggers | Ambient noise level | `VOICE_CONFIDENCE_MIN` threshold | Raise threshold to 0.90; retrain model |
| BLE not advertising | ESP32 serial output | WiFi/BLE coexistence issue | Restart ESP32; update Arduino core |
| Brake does not release | Solenoid wiring | MOSFET driver | Check GPIO pin; test MOSFET with bench supply |
| Brake does not engage | Solenoid sticking (thermal) | Spring tension | Improve ventilation; use PWM hold; replace solenoid |
| Ratchet slipping | Pawl engagement | Tooth burrs | Deburr teeth; inspect pawl tip; increase spring preload |
| Companion app: "no devices found" | BLE permissions on phone | ESP32 BLE status | Grant location permission; restart ESP32 |
| System stuck in ESTOP | ESTOP_RESET_HOLD_S | Fault condition persisting | Hold reset 2 full seconds; clear fault cause first |
| Rope jams in rope slot | Rope path through guide | Rope condition | Clear jam; inspect rope for fraying; check guide alignment |

## Maintenance Schedule

| Interval | Task | Notes |
|---|---|---|
| Before each session | Visual rope inspection | Check for cuts, core exposure, excessive wear |
| Before each session | Tension zero check | Confirm ~0 N with no load |
| Weekly | LED strip and BLE functionality check | Confirm from climbing side |
| Weekly | Listen for unusual motor or bearing noise | During a test cycle (no climber) |
| Monthly | Mounting bolt torque check | All four M10 bolts |
| Monthly | Ratchet ring and pawl inspection | Check for tooth wear, pawl tip condition, spring tension |
| Monthly | Brake pad inspection | Check for wear; measure pad thickness |
| Monthly | Run `python tools/aria_constants_sync.py` | Verify firmware/model constant alignment |
| Quarterly | Full system power cycle and state walk-through | Exercise every state transition |
| Quarterly | Bearing inspection | Check for play, noise, rough spots |
| Quarterly | Load cell recalibration | Compare against known weight |
| Annually | Rope replacement | Or sooner per manufacturer guidelines |
| Annually | Brake pad replacement | Even if not visibly worn |
| Annually | Full mechanical inspection by qualified technician | All structural components, fasteners, springs |

> **Tip:** Keep a maintenance log. Record dates, findings, and any parts replaced. This log is essential for liability and insurance purposes.

### Firmware Updates

1. Download updated firmware files.
2. Connect STM32 via USB. Flash `aria_main.cpp`. Verify boot on serial.
3. Connect ESP32 via USB. Flash `aria_esp32_firmware.ino`. Verify boot on serial.
4. Run `python tools/aria_constants_sync.py --verbose` to confirm no constant drift.
5. Run full calibration check (see [Chapter 7](./07-calibration.md), Performance Validation).

> **Warning:** After every firmware update, re-run the performance validation checklist. Never skip this step, even for "minor" changes. A single mismatched constant can change safety behavior.

### Companion App Updates

The companion app (aria-climb) is updated via app store or EAS builds. App updates do not affect the firmware or safety layer. The app is a monitoring and configuration tool only -- it is never in the safety path.

[Next: Appendix &rarr;](./11-appendix.md)
