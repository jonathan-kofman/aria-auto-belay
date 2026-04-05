[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Why](./01-the-why.md) &middot; [Next: The Architecture &rarr;](./03-the-architecture.md)

# The Design

## Design Principles

1. **Fail safe, not fail proof.** Every failure mode must result in the climber being held, not dropped. If the motor fails, the brake engages. If the ESP32 crashes, the STM32 holds tension. If power is cut, the power-off brake and centrifugal clutch engage mechanically.
2. **No single point of failure.** Three independent arrest mechanisms: ratchet ring with pawls, centrifugal clutch on the brake drum, and a spring-engaged power-off brake. Any one of them can hold a falling climber alone.
3. **Behind the wall.** The entire mechanism mounts behind the climbing wall panel to a structural beam. Only the rope port, LED strip, and optional HMI are visible. This prevents tampering, protects the mechanism from chalk dust, and keeps the climbing surface clean.
4. **Two-layer architecture.** The STM32 safety layer operates with zero dependency on the ESP32 intelligence layer. The safety layer handles tension control, brake actuation, and watchdog monitoring. The intelligence layer handles voice, vision, and BLE. If the intelligence layer dies, the safety layer keeps the climber alive.
5. **Voice-first interaction.** Climbers interact with ARIA by voice: "take", "slack", "lower", "watch me". No buttons on the wall. No phone required during the climb. The companion app is for setup, monitoring, and gym management -- not for climbing.
6. **Physics before geometry.** Every mechanical part passes CEM (Computational Engineering Model) physics checks before a STEP file is exported. Safety factors are enforced programmatically. The ratchet ring requires SF >= 8.0 for tooth shear. All other structural parts require SF >= 2.0.

## Constraints

| Constraint | Value | Source |
|---|---|---|
| Max climber weight | {e.g. 120 kg} | ANSI/CWA belay device standard |
| Max fall factor | {e.g. 1.0} | Lead climbing geometry |
| Max rope speed (fall) | 2.0 m/s | Firmware threshold |
| Watchdog timeout | 500 ms | STM32 hardware watchdog |
| E-stop brake delay | <= 50 ms | Safety requirement |
| Voice confidence threshold | >= 0.85 | Edge Impulse model accuracy |
| Clip detection confidence | >= 0.75 | CV model accuracy |
| Operating temperature | {e.g. 5-40 C} | Indoor gym environment |
| Supply voltage | 12 V DC | Barrel jack input |
| Housing wall thickness | >= 10 mm | Structural minimum (6061 Al) |
| Rope slot | 30 x 80 mm | Rope diameter + routing clearance |

## Key Tradeoffs

| We Chose | Over | Because |
|---|---|---|
| BLDC + planetary gearbox | Stepper motor | Higher torque density, smoother tension control, quieter operation |
| STM32 + ESP32 dual-MCU | Single MCU | Safety layer must be independent of intelligence layer; no shared failure modes |
| Behind-wall mount | Exposed ceiling mount | Tamper resistance, aesthetics, chalk dust protection |
| Edge Impulse on-device voice | Cloud speech API | Zero latency, no internet dependency, works if WiFi goes down |
| Centrifugal clutch + ratchet + brake | Single brake mechanism | Triple redundancy; any one mechanism arrests a fall alone |
| CadQuery (headless) as primary CAD backend | Fusion 360 API | Runs on any server, no GUI license required, CI/CD compatible |
| 6061 aluminum housing | Steel or plastic | Machinability, strength-to-weight, corrosion resistance for gym environment |
| Power-off brake (spring engaged) | Power-on brake | Engages automatically on power loss; fail-safe by physics |
| PID tension control | Bang-bang control | Smooth rope feel for the climber; prevents jerking |
| HX711 load cell | Strain gauge bridge | Cost, availability, adequate resolution for tension measurement |

## What This Is NOT

- **Not a top-rope auto-belay.** ARIA manages lead climbing rope dynamics: slack payout, clipping detection, and dynamic fall arrest. It does not simply retract rope.
- **Not a replacement for gym safety staff.** ARIA replaces the rope-holding function of a belayer. Gyms still need staff for supervision, route setting, and emergency response.
- **Not a consumer product (yet).** ARIA is in development. Hardware has not arrived for testing. The firmware is written but untested on real hardware. The mechanical design is validated through simulation and CEM physics only.
- **Not wireless.** The device is hardwired to 12V DC power. BLE is used for the companion app, not for safety-critical communication.

[Next: The Architecture &rarr;](./03-the-architecture.md)
