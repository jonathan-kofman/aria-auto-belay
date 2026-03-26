# ARIA Auto-Belay System — Failure Mode and Effects Analysis (FMEA)

**Document:** FMEA-ARIA-001
**Date:** 2026-03-26
**Prepared by:** Safety & Reliability Engineering
**Applicable standard:** ANSI/ASSA Z359.14 (Self-Retracting Lifelines)
**Design reference:** context/aria_mechanical.md, aria_models/state_machine.py

## System Summary

ARIA is a wall-mounted lead climbing auto-belay with a BLDC motor (30:1 planetary gearbox) driving a 600 mm rope spool, a 200 mm centrifugal brake drum, a 24-tooth ratchet with dual pawls, and a power-off mechanical brake. The control architecture is a dual-MCU design: STM32 (safety layer) and ESP32 (intelligence layer). The STM32 operates independently — an ESP32 crash must never compromise braking. Total power loss engages the power-off brake and centrifugal clutch (fail-safe).

Key test limits per Z359.14: max arrest force 8000 N, max average arrest force 6000 N, max arrest distance 813 mm, static proof load 16000 N, minimum safety factor 2.0.

## Severity Scale

| Rating | Meaning |
|--------|---------|
| 1 | No effect |
| 2-3 | Minor degradation, no safety impact |
| 4-5 | Moderate — reduced function, operator aware |
| 6-7 | High — loss of a safety function, backup exists |
| 8-9 | Very high — potential injury, single backup remains |
| 10 | Catastrophic — potential fatality, no remaining backup |

## FMEA Table

| # | Failure Mode | Effect on System | Severity (S) | Occurrence (O) | Detection (D) | RPN | Recommended Action |
|---|---|---|---|---|---|---|---|
| **Braking Chain** | | | | | | | |
| 1 | VESC motor controller failure — motor stops responding | Loss of powered rope management (tension, payout, retract). Climber cannot get slack for clipping. Centrifugal clutch and ratchet still arrest falls. State machine enters ESTOP via STM32 watchdog on VESC heartbeat timeout. | 7 | 3 | 3 | **63** | Add VESC heartbeat monitor on STM32 with 200 ms timeout. Redundant UART + CAN bus to VESC. Audible alarm on motor fault. Require gym staff retrieval procedure. |
| 2 | Ratchet pawl fails to engage — tooth shear or wear | Fall arrest depends solely on centrifugal clutch and mechanical brake. With dual pawls (N_PAWLS=2), single-pawl failure still leaves one pawl. Dual-pawl failure is catastrophic if clutch also fails. Tooth shear SF threshold is 8.0 (safety-critical). | 9 | 2 | 5 | **90** | Enforce CEM SF >= 8.0 on tooth shear per design. Hardened steel pawl tips. Periodic visual inspection interval (500 climb-hours). Pawl engagement depth sensor (3 mm travel confirmation). Replace pawls at wear limit (0.5 mm tip loss). |
| 3 | Centrifugal clutch slip — inadequate friction at speed | Reduced braking force during fall. Arrest distance exceeds 813 mm limit. Ratchet pawl provides backup arrest. If both slip and pawl fail, uncontrolled descent. | 8 | 2 | 6 | **96** | Friction material rated for 140 kg at 2.0 m/s fall speed. Drum surface inspection every 1000 climbs. Rope speed sensor cross-check: if speed > threshold and tension < expected, flag clutch degradation. Annual drop test per Z359.14. |
| 4 | Mechanical brake fails to engage on power loss | Power-off brake is the last-resort backup. Failure means power loss leaves only centrifugal clutch (speed-dependent, ineffective at low speed). Climber at rest with no tension hold. | 10 | 1 | 4 | **40** | Spring-return brake design (fail-closed). Weekly functional test: kill power, verify brake holds 16 kN static proof load. Brake spring replacement interval. Independent brake circuit — no shared wiring with motor driver. |
| **Sensor Failures** | | | | | | | |
| 5 | Load cell failure — false zero or stuck reading | PID tension loop loses feedback. Motor may over-tension (injury) or under-tension (unexpected slack). STM32 detects stuck reading via rate-of-change check. TENSION_BASELINE_N = 40 N target lost. | 8 | 3 | 3 | **72** | Dual redundant load cells with cross-validation. STM32 flags stuck reading (delta < 0.1 N over 2 s while motor active). On load cell fault, enter ESTOP and engage brake. Calibration check at power-on (known tare). |
| 6 | Rope encoder failure — no speed data | Loss of fall detection (ROPE_SPEED_FALL_MS = 2.0 m/s threshold). System cannot distinguish paying out slack from a fall by speed alone. Tension-based fall detection (400 N threshold) still active. | 6 | 3 | 4 | **72** | Use tension spike (TENSION_FALL_THRESHOLD_N = 400 N) as independent fall trigger. Encoder health check: expect non-zero counts during any motor-active state. Flag encoder fault, continue with tension-only detection. Add accelerometer as tertiary fall indicator. |
| 7 | Camera/CV failure — no clip or zone detection | Cannot detect clip events (cv_clip) or zone intrusion (cv_zone). CLIMBING_PAUSED state unreachable. Climber may climb unclipped without system awareness. Not in the arrest chain — advisory function. | 5 | 4 | 5 | **100** | CV heartbeat monitored by ESP32. On CV loss, set LED strip to amber warning. Require manual clip confirmation via voice or app. Log CV downtime for maintenance review. Do not block climbing — CV is advisory, not safety-critical. |
| **Electrical** | | | | | | | |
| 8 | ESP32 crash — intelligence layer down | Loss of voice commands, CV processing, BLE app link. STM32 holds current tension via PID. No new state transitions except ESTOP. Climber can finish current position safely. | 5 | 4 | 2 | **40** | STM32 watchdog on ESP32 heartbeat (1 s timeout). On ESP32 loss, STM32 holds TENSION mode, activates LED alarm, allows only LOWER and ESTOP via hardware E-stop. ESP32 auto-reboot with WDT. OTA firmware recovery. |
| 9 | STM32 crash — safety layer down | Loss of PID tension control, brake GPIO, VESC communication. Motor stops (VESC timeout). Power-off brake and centrifugal clutch engage passively. Single most critical electronic failure. | 10 | 2 | 3 | **60** | Hardware watchdog (IWDG) with 100 ms timeout triggers brake GPIO via fail-safe circuit. Brake GPIO default state = engaged (active-low design). Independent voltage supervisor resets STM32 on brownout. Dual-bank firmware with golden image fallback. |
| 10 | Total power loss — both MCUs down | All electronics dead. Power-off mechanical brake engages (spring-return). Centrifugal clutch functional (passive, no power needed). Climber arrested and held by mechanical systems only. Cannot lower — requires staff intervention. | 7 | 2 | 1 | **14** | Power-off brake is fail-closed by design. UPS/supercapacitor for 30 s controlled lower sequence before full shutdown. Audible alarm (piezo, battery-backed) on power loss. Procedure: staff manually lowers climber via mechanical release. |
| 11 | UART link failure between ESP32 and STM32 | ESP32 intelligence cannot send commands to STM32. Voice, CV, and app inputs lost. Equivalent to ESP32 crash from STM32 perspective. STM32 continues autonomous tension hold. | 5 | 3 | 2 | **30** | STM32 treats UART silence > 1 s same as ESP32 crash. CRC on all UART frames — reject corrupted commands. Physical UART lines: short, shielded, no shared ground loops. Redundant SPI link as backup channel. |
| **Operational** | | | | | | | |
| 12 | Voice command misrecognition — wrong state transition | Incorrect state change (e.g., "take" heard as "slack"). Could cause unexpected tension or payout. VOICE_CONFIDENCE_MIN = 0.85 threshold mitigates low-confidence errors. VALID_TRANSITIONS table prevents illegal jumps (e.g., IDLE cannot go to LOWER). | 6 | 4 | 4 | **96** | Enforce 0.85 confidence threshold strictly. Require confirmation for high-consequence commands (LOWER, TAKE). App displays recognized command with 2 s cancel window. Log all voice events for post-incident review. State machine rejects invalid transitions — defense in depth. |
| 13 | E-stop button failure — button does not trigger ESTOP | Climber or staff cannot emergency-stop the system. All other protections (tension thresholds, fall detection, passive brakes) still active. ESTOP is reachable from every state in VALID_TRANSITIONS. | 8 | 1 | 3 | **24** | NC (normally-closed) E-stop circuit — wire break = ESTOP triggered. Daily press-test by gym staff (logged). Hardwired to STM32 GPIO and independently to brake relay — two paths. Second E-stop button at ground level. |
| 14 | Climber clips in without detection | System remains IDLE while climber begins climbing. No tension management — rope slack accumulates. Fall while IDLE means no powered arrest, only passive clutch and ratchet (still functional). | 6 | 3 | 6 | **108** | Load cell detects body weight on rope (> 15 N sustained) as secondary clip-in indicator. Require explicit "climbing" voice command or app tap to leave IDLE. LED strip shows red in IDLE — visual cue that system is not active. Proximity sensor or gate switch at rope port. |

## Risk Priority Summary

| RPN Range | Risk Level | Count | Item Numbers |
|-----------|-----------|-------|--------------|
| 100+ | **High — action required** | 3 | #3 (clutch slip, 96), #7 (CV failure, 100), #12 (voice misrecognition, 96), #14 (undetected clip-in, 108) |
| 50-99 | **Medium — monitor and mitigate** | 4 | #1 (VESC failure, 63), #2 (pawl failure, 90), #5 (load cell, 72), #6 (encoder, 72), #9 (STM32 crash, 60) |
| < 50 | **Low — acceptable with current controls** | 5 | #4 (mech brake, 40), #8 (ESP32 crash, 40), #10 (power loss, 14), #11 (UART failure, 30), #13 (E-stop, 24) |

## Key Observations

1. **Highest RPN (#14, 108):** Undetected clip-in scores highest due to poor detection (D=6). Mitigation priority: add a physical presence sensor at the rope port and enforce explicit activation.

2. **Highest severity items (#4, #9, S=10):** Mechanical brake failure and STM32 crash are catastrophic single-point failures. Both are mitigated by fail-safe hardware design (spring-return brake, hardware watchdog). Their low RPN reflects this.

3. **Passive safety chain is robust:** Total power loss (RPN=14) is the lowest risk because the centrifugal clutch and power-off brake require no electronics. This validates the fail-safe architecture.

4. **Detection is the dominant risk driver:** Items #3, #7, #12, #14 all have D >= 4. Investment in monitoring (clutch performance trending, CV health, voice logging, clip-in sensing) yields the best RPN reduction.

5. **Dual-pawl ratchet reduces occurrence but not severity:** Single-pawl failure is tolerable (O=2 reflects dual redundancy), but severity remains 9 because total pawl system failure during concurrent clutch degradation is life-threatening.

---

## Session 2026-03-26T00:00:00
**Status:** Success
**Goal:** FMEA document for ARIA auto-belay system (14 failure modes)
**Output:** sessions/2026-03-26_safety-fmea.md
