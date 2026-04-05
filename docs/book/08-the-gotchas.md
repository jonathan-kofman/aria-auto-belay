[&larr; Back to Table of Contents](./README.md) &middot; [Previous: Calibration](./07-calibration.md) &middot; [Next: Safety &rarr;](./09-safety.md)

# The Gotchas

Lessons learned, failure modes encountered during development, and things that will waste your time if you do not know about them.

---

## Gotcha: HX711 Gives Garbage Readings After Power Cycle

**Symptom:** Load cell reads wildly incorrect values (e.g. -50000 or +99999) after a power cycle, even though it was calibrated correctly before.

**Cause:** The HX711 requires a stable power supply during its internal reset sequence. If the 3.3V rail sags during power-on (common when VESC and motor draw inrush current), the HX711 initializes with bad internal state.

**Fix:** Add a 100 uF capacitor across the HX711 VCC/GND pins. If the problem persists, add a 200 ms delay in firmware before the first HX711 read after boot.

**Cost if ignored:** False tension readings. The PID loop drives the motor based on garbage data. At best, the rope jerks. At worst, the system does not detect a fall.

---

## Gotcha: UART TX/RX Crossed Between STM32 and ESP32

**Symptom:** STM32 and ESP32 are both running but neither receives messages from the other. Serial monitor on each board shows outgoing messages but no incoming.

**Cause:** UART TX and RX are not crossed. TX on the STM32 must connect to RX on the ESP32, and vice versa. This is the most common wiring mistake in dual-MCU systems.

**Fix:** Swap the two UART wires between the boards.

**Cost if ignored:** The intelligence layer (voice, CV) cannot communicate with the safety layer. Voice commands are detected but never acted on.

---

## Gotcha: Brake Solenoid Sticks When Hot

**Symptom:** After extended operation (30+ minutes of continuous climbing), the brake does not engage when power is removed. Shaft continues to rotate.

**Cause:** The solenoid coil heats up, causing thermal expansion of the plunger or housing. The plunger sticks in the released position.

**Fix:** Ensure adequate ventilation around the solenoid. Use a PWM hold current (reduce duty cycle to 50-70% after initial pull-in) to minimize heat. If the problem persists, use a solenoid rated for continuous duty.

**Cost if ignored:** Loss of the power-off brake. The other two arrest mechanisms (ratchet + clutch) still function, but you have lost one layer of redundancy.

---

## Gotcha: Ratchet Pawl Does Not Engage Every Tooth

**Symptom:** During rotation testing, the ratchet occasionally slips -- the pawl clicks past a tooth without catching.

**Cause:** Machining burrs on the ratchet teeth, pawl tip wear, or insufficient spring tension. The pawl engagement depth is only 3 mm, so even a small burr can prevent full engagement.

**Fix:** Deburr all ratchet teeth with a fine file or stone. Inspect pawl tip for wear (6 mm wide, must be sharp-edged). Increase spring preload if pawl is sluggish.

**Cost if ignored:** Catastrophic. If both pawls miss simultaneously during a fall, the ratchet does not arrest. This is the primary fall arrest mechanism.

---

## Gotcha: SimpleFOC Motor Detection Fails

**Symptom:** VESC motor detection wizard completes but motor runs rough, vibrates, or does not spin at all.

**Cause:** The motor detection measures electrical parameters (resistance, inductance, flux linkage). If connections are loose or if one phase wire has high resistance (bad crimp), the parameters are wrong and FOC control fails.

**Fix:** Re-crimp all motor phase connections. Use a multimeter to measure resistance between each pair of phase wires -- all three pairs should read the same value (+/- 5%). Re-run motor detection.

**Cost if ignored:** Poor motor control. The PID loop cannot hold stable tension if the motor is not running FOC correctly.

---

## Gotcha: ESP32 BLE Stops Advertising After WiFi Connect

**Symptom:** BLE works during initial setup, but after the ESP32 connects to WiFi (for provisioning or OTA), BLE advertisements stop and the companion app cannot find the device.

**Cause:** ESP32 shares a single radio for WiFi and BLE. Simultaneous WiFi + BLE is supported but requires careful configuration. Some ESP32 Arduino core versions have bugs where WiFi STA mode disables BLE advertising.

**Fix:** Update ESP32 Arduino core to latest stable version. After WiFi operations complete, explicitly restart BLE advertising. If coexistence is unreliable, use WiFi only during provisioning and disable it during normal operation.

**Cost if ignored:** Companion app cannot connect during climbing. Telemetry goes dark. Not safety-critical (STM32 operates independently) but degrades the user experience.

---

## Gotcha: Voice Model Triggers on Gym Music

**Symptom:** System transitions to TAKE or LOWER without any climber voice command. Happens when music is playing through gym speakers.

**Cause:** The Edge Impulse model was trained on voice samples but not on music. Certain music patterns (especially vocals) trigger false positives.

**Fix:** Retrain the Edge Impulse model with gym ambient noise (including music) as negative samples. Alternatively, increase `VOICE_CONFIDENCE_MIN` to 0.90 or higher.

**Cost if ignored:** Unexpected state transitions during climbing. The system may retract rope when the climber does not want it.

---

## Common Build Mistakes

| Mistake | What Happens | How to Avoid |
|---|---|---|
| Using PLA for internal brackets | Brackets soften and deform near motor heat | Use PETG or ASA for all printed parts |
| Forgetting flyback diode on solenoid | MOSFET dies on first brake engage cycle | Always install diode before first power-on |
| Not threadlocking motor mount bolts | Bolts vibrate loose over days of operation | Loctite 242 on all structural fasteners |
| Mounting HX711 near motor | Electrical noise corrupts tension readings | Keep HX711 as far from motor/VESC as possible |
| Using wrong baud rate on UART | Garbled communication, random state changes | Both sides must be 115200. Verify in code and with scope |
| Skipping bearing preload check | Shaft play causes vibration and noise | Verify zero play after bearing installation |
| Over-tightening cable glands | Crushes signal wires, intermittent connections | Hand-tight plus 1/4 turn only |
| Forgetting to cross UART TX/RX | Zero communication between MCUs | Label wires before connecting: "STM TX -> ESP RX" |

## Things That Look Broken But Aren't

| Symptom | Looks Like | Actually |
|---|---|---|
| Motor makes a brief whine on state transition | Motor fault | Normal: SimpleFOC re-initializes FOC angle on mode change. Lasts < 200 ms. |
| Tension reads 2-3 N with no load | Sensor drift | Normal: HX711 has small thermal drift. Firmware zeros this periodically. |
| LED strip flickers during motor acceleration | Electrical fault | Normal: motor inrush causes brief voltage dip on 5V rail. Add a capacitor if it bothers you. |
| ESP32 reboots every ~8 hours | Crash bug | Normal: if `WATCHDOG_TIMEOUT_MS` is configured on ESP32 side, it resets as a safety measure. STM32 holds tension through the reboot. |
| Brake makes a clunk when engaging | Mechanical failure | Normal: spring-driven engagement is not silent. A sharp clunk is expected. Absence of clunk is the problem. |
| Companion app shows "reconnecting..." briefly | BLE failure | Normal: BLE connection parameters allow brief disconnects. Auto-reconnect with exponential backoff is built in. |

[Next: Safety &rarr;](./09-safety.md)
