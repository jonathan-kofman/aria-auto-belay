[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Gotchas](./08-the-gotchas.md) &middot; [Next: Operations &rarr;](./10-operations.md)

# Safety

> **Warning:** ARIA is a life-safety device. A failure during a fall can result in serious injury or death. Every safety system described in this chapter must be verified and tested before any climbing takes place. No exceptions.

## Hazard Summary

| # | Hazard | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | Climber fall not arrested | Fatal | Very low (triple redundant) | Ratchet + clutch + power-off brake; any one arrests fall |
| 2 | Rope entanglement in spool | Serious injury | Low | Rope guide constrains path; rope slot dimensioned for single rope only |
| 3 | Electrical shock (12V) | Minor | Low | 12V DC is below touch-safe threshold; all connections insulated |
| 4 | Motor runaway (uncontrolled payout) | Serious injury | Very low | VESC current limits; STM32 watchdog resets to brake-engaged state |
| 5 | Brake failure (all three) | Fatal | Extremely low | Independent mechanisms; no shared failure mode |
| 6 | False voice command (unexpected retract) | Moderate | Low | Confidence threshold 0.85; TAKE requires 200 N tension confirmation |
| 7 | Structural mount failure | Fatal | Very low | M10 bolts to structural beam; 4-point mounting |
| 8 | Fire (electrical short) | Serious | Very low | Fused power supply; VESC overcurrent protection; solenoid flyback diode |
| 9 | Falling hardware (housing detaches) | Fatal | Very low | Redundant mounting bolts; periodic inspection required |
| 10 | Pinch points (spool, gears) | Moderate | Low | Behind-wall installation; housing fully enclosed; no user access to mechanism |

## Electrical Safety

### Low Voltage

ARIA operates on 12V DC. This is below the 50V AC / 120V DC threshold for electric shock hazard. However:

- Always de-energize the system before opening the housing.
- The BLDC motor can generate back-EMF when the shaft is rotated manually. Do not touch motor phase wires while rotating the shaft by hand.
- The brake solenoid is an inductive load. The flyback diode must be installed to prevent voltage spikes that can destroy the MOSFET driver.

### Overcurrent Protection

| Protection | Location | Function |
|---|---|---|
| Fused power supply | 12V input | Limits total system current |
| VESC current limit | Motor controller | Prevents motor overcurrent |
| MOSFET driver | Solenoid circuit | Controlled switching |
| Flyback diode | Solenoid | Absorbs inductive kick |

### Grounding

The aluminum housing is the system ground reference. All PCB ground planes should be connected to the housing via a star ground point. This prevents ground loops and ensures the housing is not floating.

## Mechanical Safety

### Fall Arrest Redundancy

ARIA uses three independent fall arrest mechanisms. Each operates on a different physical principle. No single failure disables all three.

| Mechanism | Principle | Trigger | Failure Mode |
|---|---|---|---|
| Ratchet ring + pawls | Mechanical interlock | Spool backdriving (rope payout under load) | Pawl wear, tooth damage |
| Centrifugal clutch | Friction via centrifugal force | High rotational speed (fall) | Shoe wear, spring fatigue |
| Power-off brake | Spring-engaged friction | Loss of electrical power or ESTOP command | Solenoid sticking (see Gotchas) |

### Structural Requirements

- Housing must be mounted to a structural beam capable of withstanding {e.g. 15 kN} (fall force with safety margin).
- All four M10 mounting bolts must be installed. Do not operate with fewer than four bolts.
- Mounting bolts must be inspected for tightness on a {e.g. monthly} schedule.

### Rope Requirements

- Use dynamic climbing rope rated for lead falls (EN 892 or UIAA certified).
- Inspect rope for damage before each climbing session.
- Replace rope per manufacturer guidelines or immediately if any core is visible.

## Emergency Procedures

### Climber Stuck on Wall (System Not Responding)

1. Send ESTOP command via companion app, or disconnect 12V power.
2. Brake engages immediately (power-off brake).
3. Climber is held by brake + ratchet.
4. Manually lower climber: {e.g. describe manual lowering procedure using backup belay or assisted descent}.
5. Do not restore power until the fault is diagnosed.

### Fall Arrest Activated (FALL_ARREST State)

1. System has caught a fall. Motor is OFF. Brake is engaged. Ratchet is locked.
2. Verify climber is conscious and uninjured (visual or voice check).
3. Send LOWER command to lower climber to ground.
4. If system does not respond to LOWER: use manual lowering procedure.
5. After climber is on ground: send RESET (hold for 2 seconds) or power cycle.
6. Inspect rope and all mechanical components before next climb.

### E-Stop Activated

1. Brake engages within 50 ms.
2. Motor is OFF. System is in ESTOP state.
3. To exit ESTOP: operator must hold reset for 2 continuous seconds (`ESTOP_RESET_HOLD_S = 2.0`).
4. System returns to IDLE after reset.
5. Investigate the cause of the E-stop before resuming climbing.

### Power Loss

1. Power-off brake engages automatically (spring force).
2. Ratchet remains engaged (mechanical, no power needed).
3. Centrifugal clutch engages if spool is spinning (mechanical).
4. Climber is held by all three mechanisms.
5. Restore power or manually lower climber.

### Fire / Smoke from Housing

1. Disconnect 12V power immediately.
2. Do not open housing until it has cooled.
3. Use CO2 or dry chemical extinguisher if flames are visible.
4. Evacuate the climbing area.
5. Do not re-energize until a full electrical inspection is completed.

## Operating Limits

| Parameter | Limit | Notes |
|---|---|---|
| Max climber weight | {e.g. 120 kg} | Per structural analysis + CEM SF |
| Max fall factor | {e.g. 1.0} | Lead climbing geometry |
| Max rope length | {e.g. 30 m} | Spool capacity |
| Operating temperature | {e.g. 5-40 C} | Indoor gym only |
| Max continuous operation | {e.g. 12 hours} | Solenoid thermal limit |
| Max altitude | {e.g. 2,500 m} | Motor cooling (air density) |
| Min inspection interval | {e.g. Monthly} | All mechanical components + bolts |
| Rope replacement interval | Per manufacturer spec | Or immediately on visible damage |

> **Warning:** Operating outside these limits voids all safety analysis. The CEM safety factors are computed for the conditions listed above. Higher weight, longer falls, or extreme temperatures require re-analysis.

[Next: Operations &rarr;](./10-operations.md)
