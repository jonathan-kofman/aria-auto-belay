# ARIA Setup Guide
## Autonomous Rope Intelligence Architecture

**Version:** 0.4
**Hardware Status:** Pre-purchase (firmware development phase)
**Repository:** https://github.com/jonathan-kofman/aria-auto-belay

---

## Project Status Summary

### What's Done
The electrical and firmware architecture is the most complete part of the project. The BOM is optimized, MCU responsibilities are clean, the failsafe is solved, sensor fusion is designed, the app is fully specced, bolt detection is designed, rope wear management is documented, and all housing-level design decisions are now locked. You could start building Phase 2 firmware today with full confidence in the architecture.

### What's In Progress
Phase 2–3 firmware is actively being written before hardware purchase. The simulator, test harness, PID tuner, and audio collector tools exist. The STM32 implementation needs to be updated to remove the old FOC layer and add VESC UART commands, brake GPIO, CLIMBING_PAUSED state, VESC fault handling, and E-stop GPIO. The ESP32 firmware needs the wearable BLE audio receive path added.

### What's Blocked on External Work
Two structural calculations need to be run before hardware is finalized — fall factor analysis at bolt 1, and wall mount load analysis. Prompts for both are in this document. A lawyer needs to be engaged before any POC unit is installed at a gym. Intertek should be contacted for a scoping call on Z359.14 classification before the operator manual is finalized.

### What's Not Started Yet
Mechanical CAD (Phase 1), operator manual draft, wearable device hardware, and all Phase 4–5 firmware. None of these are blocking current firmware work.

---

## System Overview

ARIA is a lead climbing auto belay device that combines the mechanical safety of a centrifugal clutch catch system with intelligent slack management and safety monitoring. It mounts at the **base of the wall**, feeding rope upward through the route.

**Climber weight range:** 40–120kg (matching Lead Solo base design)
**Target wall height:** Up to 27.5m (50m rope)
**Target market:** Indoor climbing gyms — recreational to training facilities

### Core Architecture

**Mechanical layer (passive safety):**
- Centrifugal clutch catch (Lead Solo design basis)
- 200mm brake drum
- 600mm rope spool
- 6061-T6 aluminum housing
- Wall + floor dual mount

**Electrical layer (active intelligence):**
- 57mm BLDC planetary gearmotor — slack management with integrated power-off brake
- Makerbase VESC MINI 6.7 — dedicated FOC motor driver
- STM32F411 Black Pill — safety layer (state machine, sensor fusion, brake control, E-stop)
- XIAO ESP32-S3 Sense — intelligence layer (voice, CV, BLE, safety monitoring)
- HX711 + 50kg load cell — rope tension sensing via sheave reaction force
- AS5048A magnetic encoder — rope spool position / payout tracking
- OV2640 camera (built into ESP32-S3 Sense) — ground-level safety monitoring
- SSD1306 OLED + piezo buzzer — alert output
- E-stop mushroom button (40mm, NC, twist-release) — physical emergency stop
- Wearable voice unit — harness-mounted BLE mic for climber voice commands

**Total BOM cost:** ~$240–300 (hardware not yet purchased)

---

## Rope Connection and Operation

### How the Climber Connects
Climbers tie in with a **figure-8 follow-through knot** directly into their harness tie-in points — identical to normal lead climbing. No carabiner, no clip-in loop. The rope end has a stopper knot to prevent it pulling through the system if untied.

This eliminates the clip-in failure mode (the leading cause of auto belay incidents) and requires no new skills from experienced lead climbers.

### Session Flow
1. Climber approaches ARIA, rope end is hanging at ~1.5m (tie-in station height)
2. Climber ties figure-8 into harness, clips wearable voice unit to belay loop
3. Wearable pairs to ARIA via ARIA Climb app BLE handshake
4. Climber unclips rope from ground anchor, begins climbing
5. First climber threads rope through quickdraws as they climb (normal lead style)
6. Climber falls or reaches top → ARIA lowers them to ground
7. Climber unclips all quickdraws on the way down (standard lead lower protocol)
8. Climber unties at base, returns wearable to station
9. ARIA retracts rope to 1.5m tie-in height (rope now free-hanging, no draws clipped)
10. Ready for next climber

### Rope Management
- **Between sessions:** ARIA motor retracts free-hanging rope to ~1.5m tie-in height
- **Retraction load:** Free-hanging rope only — climber must unclip all draws before lowering
- **This is a required protocol** documented in the operator manual — rope left clipped through draws during retraction is a safety hazard and voids warranty

---

## Failsafe Architecture — Power Loss

**Critical safety requirement:** If power fails while a climber is on the wall, they must be able to descend safely without any intervention.

ARIA solves this with a **power-off electromagnetic brake** integrated into the gearmotor. When power is present, the brake coil is energized and releases — the motor drives normally. When power cuts for any reason, the brake spring-engages instantly, decoupling the gearbox from the rope spool. The Lead Solo centrifugal brake underneath then controls descent at a safe rate (~2m/s) entirely passively, with no electronics required.

- Power failure → brake engages within ~50ms → rope spool free to descend under centrifugal brake
- No staff intervention required
- No software required
- No battery backup required

The STM32 also controls the brake deliberately via dedicated GPIO for LOWER, EMERGENCY_STOP, and IDLE states.

**Secondary manual override:** A brake release cable on the ARIA housing allows staff to manually decouple the gearbox if the electromagnetic brake itself fails mechanically.

---

## Physical Emergency Stop

A 40mm industrial mushroom-head E-stop button (red, normally-closed contact, twist-release reset) is mounted on the ARIA housing face.

**Behavior on press:** Brake engages + motor stops. ARIA holds current state — does not reset to IDLE. Climber remains safely held by engaged brake.

**Reset:** Twist-release — deliberate staff action required. Cannot be accidentally re-armed.

**Wiring:** NC contact wired **in series with the brake control circuit** — hardware level, not software level. STM32 lock-up does not prevent E-stop from working. A wiring fault or broken button also cuts brake power (fail-safe by design — never use NO contacts for safety circuits).

**Firmware:** STM32 monitors E-stop GPIO on falling edge → transition to EMERGENCY_STOP state → send VESC coast command → log event with timestamp to Firebase.

**BOM addition:** ~$10–12

---

## Wearable Voice Unit

A small harness-mounted device ships with each ARIA unit, solving the voice command range problem — a base-mounted mic cannot reliably pick up commands from a climber at 20m in a noisy gym.

### Specification

| Item | Detail |
|---|---|
| Function | PDM microphone + BLE transmitter only |
| MCU | Nordic nRF52810 or equivalent low-power BLE SoC |
| Audio | Raw audio streamed over BLE to ESP32-S3 — all wake word inference at base |
| Power | CR2032 coin cell (~20–50 sessions per battery) |
| Attachment | Clips to harness belay loop |
| Ownership | Ships with ARIA, gym-provided to climbers per session |
| Pairing | Bonds exclusively to one ARIA unit at session start via ARIA Climb app — prevents cross-device interference |

### Audio Source Priority (ESP32-S3)
1. **Wearable BLE stream** — primary when wearable is paired and active
2. **Built-in ESP32-S3 mic** — fallback when no wearable paired (staff commands, low-height climbers)

### Operational Protocol
- Battery replacement interval: every 20–50 sessions depending on session length
- Sanitization between climbers: wipe with gym-standard cleaner
- Storage: dedicated holder at ARIA tie-in station
- Spare units: gym should keep 1–2 spares charged

**BOM addition:** ~$8–15 per unit

---

## MCU Responsibility Split

One MCU, one job.

| MCU | Responsibilities | What it does NOT do |
|---|---|---|
| VESC MINI 6.7 (STM32F405 onboard) | FOC motor control, current limiting, motor protection, fault reporting | Safety state machine, sensors |
| STM32F411 Black Pill | Safety state machine, load cell, AS5048A encoder, brake GPIO, E-stop GPIO, VESC fault handler, UART to ESP32, UART to VESC | Motor commutation, FOC |
| XIAO ESP32-S3 Sense | Voice wake words (wearable + built-in mic), camera safety monitoring, BLE app + wearable, UART to STM32 | Motor control, safety state machine |

---

## System States

ARIA operates an 8-state machine on the STM32F411:

| State | Description |
|---|---|
| IDLE | No climber, motor relaxed, brake engaged |
| CLIMBING | Climber ascending, dynamic slack management active |
| CLIPPING | Climber paused to clip, pre-pay slack mode |
| TAKE | Rope pulled tight on request |
| REST | Climber hanging, maintain tension |
| LOWER | Controlled descent, brake partially released, motor pays out |
| WATCH_ME | Slack-free attentive mode |
| CLIMBING_PAUSED | Zone intrusion detected — motor hold, brake engaged, alert active |

**EMERGENCY_STOP** is a transition, not a persistent state — it immediately engages the brake and holds whatever state the system was in.

---

## Sensor Fusion — Slack Management

The core innovation in ARIA is **predictive** (not reactive) slack management. Rather than responding to rope tension after the fact, ARIA reads the biomechanical signature of what the climber is about to do.

### Primary Signals (STM32F411)

**AS5048A encoder (rope spool):**
- Absolute rope payout position — climber height estimate
- Payout velocity — climbing speed
- Payout acceleration — key discriminator between clip reach and fall

**HX711 load cell:**
- Tension magnitude — rest vs. active vs. fall
- Tension rate of change (d/dt) — detects clip reach signature
- Tension pattern — sustained low = resting, spike = clip/fall

### Biomechanical Signatures

**Pre-clip sequence (detected 0.5–2s before clip):**
1. Rope payout slows/stops — climber finding stable position
2. Tension drops as climber weights feet, unloads harness
3. Short sharp rope pull + brief tension spike — reach for draw
→ ARIA pre-pays 25–40cm on step 3 (amount depends on bolt map confidence)

**Fall detection:**
- Encoder acceleration: near-instantaneous max velocity (vs. soft onset for clip reach)
- Load cell: drops to near-zero briefly, then massive spike at clutch engagement
- Camera (secondary): fast downward motion blur in lower wall zone

**The classifier runs entirely on STM32F411** as a threshold-based state machine — no ML required. Feature vector: `[encoder_velocity, encoder_accel, tension, tension_dt, rope_position]`.

### VESC Communication

STM32F411 sends motor commands to VESC MINI via UART (VESC serial protocol). VESC reports motor telemetry (RPM, current, temperature) and fault codes at 50Hz.

**VESC fault handling:** On any VESC fault packet → STM32 immediately engages brake (EMERGENCY_STOP behavior) → logs fault code to Firebase via ESP32. This is a distinct failure mode from power loss and must be explicitly handled.

---

## Brake Control

Power-off brake coil driven by STM32F411 GPIO through IRLZ44N MOSFET + 1N4007 flyback diode.

```
STM32 GPIO → 10kΩ resistor → MOSFET gate
MOSFET drain → brake coil → 24V
MOSFET source → GND
1N4007 flyback diode across coil (cathode to 24V, anode to drain)
E-stop NC contact in series with brake coil circuit
```

| STM32 State | Brake GPIO | Effect |
|---|---|---|
| IDLE | LOW | Brake engaged, rope held |
| CLIMBING | HIGH | Brake released, motor active |
| CLIPPING | HIGH | Brake released, motor active |
| TAKE | HIGH | Brake released, motor pulls tight |
| REST | HIGH | Brake released, motor holds tension |
| LOWER | HIGH→PWM | Brake released, motor pays out at controlled rate |
| WATCH_ME | HIGH | Brake released, motor active |
| CLIMBING_PAUSED | LOW | Brake engaged, motor stopped |
| EMERGENCY_STOP | LOW | Brake engaged instantly |
| VESC FAULT | LOW | Brake engaged instantly |
| POWER FAILURE | LOW (no power) | Brake spring-engages automatically |

---

## Bolt Detection — Route Mapping

Three layered approaches. None required for basic operation — each layer improves precision.

### Layer 1 — Biomechanical Signature (always active)
Primary clip trigger. Pre-pay 25cm conservatively without bolt knowledge.

### Layer 2 — Pattern Learning (builds over sessions)
Clip events logged with encoder position. Clusters form over 5–10 sessions → confirmed bolt map stored in Firebase. Pre-pay upgrades to 40cm at known bolt positions. Route reset auto-detected when <20% of clips match stored map.

### Layer 3 — Magnetic Rope Markers (optional)
8×2mm neodymium magnets crimped into rope at bolt intervals. Hall effect sensor (AH3503) at sheave reads markers as rope pays out. Instant bolt map from session one. ~20g total rope mass addition for 8-bolt route. Optional — not in base BOM ($0.30/marker + $0.50 sensor).

### Pre-Pay by Confidence

| Condition | Pre-Pay |
|---|---|
| No bolt map | 25cm |
| Bolt map match | 40cm |
| Bolt map stale | 25cm |
| Magnetic marker confirmed | 40cm |

---

## Camera — Safety Monitoring

OV2640 at base, dedicated to ground-level safety monitoring (0–3m zone). High-priority FreeRTOS task on ESP32-S3. Full specification in `ARIA_SAFETY_MONITORING.md`.

**Functions:** Fall zone intrusion (10s threshold → CLIMBING_PAUSED), session detection (IDLE → READY), fall confirmation (secondary), climber ID via BLE app (Phase 5).

**Alert output:** SSD1306 OLED + piezo buzzer on ESP32-S3.

---

## UART Protocol

### STM32 ↔ ESP32-S3

| Packet | Example | Description |
|---|---|---|
| Voice command | `V:take:0.92` | Command + confidence |
| Clip event | `C:clip:4.2:1` | Clip detected, height, confidence |
| State sync | `S:CLIMBING:12.4:3.2:45` | State, tension, position, motor |
| Zone intrusion | `W:ZONE_INTRUSION:ALERT` | 10s threshold crossed |
| Zone cleared | `W:ZONE_INTRUSION:0` | Object left zone |
| Fall (camera) | `W:FALL_DETECTED:CAMERA` | Camera-confirmed fall |
| Session start | `S:SESSION_START:0` | Climber at base |
| Climber ID | `I:CLIMBER_ID:profile_hash` | BLE app profile |

### STM32 ↔ VESC MINI
VESC serial protocol over UART2. STM32 sends current setpoint, RPM, coast, or brake commands. VESC sends telemetry + fault codes at 50Hz.

---

## Voice Commands

Processed by Edge Impulse model on ESP32-S3 from wearable BLE audio stream (primary) or built-in mic (fallback):

| Command | State Transition |
|---|---|
| "climbing" | IDLE → CLIMBING, or CLIMBING_PAUSED → CLIMBING (climber override) |
| "take" | Any → TAKE |
| "slack" | Any → CLIMBING |
| "lower" | Any → LOWER |
| "up" | Any → WATCH_ME |
| "watch me" | Any → WATCH_ME |
| "rest" | CLIMBING → REST |

---

## Sensor Integration Principles

All sensors live in the housing structure — nothing added to the rope path.

**Tension:** Load cell between sheave bracket and housing wall — reads sheave reaction force, zero rope contact.
**Payout:** AS5048A magnet on spool shaft end, sensor on housing wall 1–2mm away.
**Sheave spec:** 60–80mm diameter, semicircular groove ~10–11mm wide, sealed ball bearing axle. Sheave wear indicator machined into sheave body (Phase 1 CAD requirement).
**Motor:** Drives spool shaft internally — rope never contacts motor.

Multi-layer spool compensation: rope payout is non-linear with shaft rotation as layers accumulate. Firmware uses geometric model (track cumulative rotations + estimate current layer) for height estimation. ±0.5m accuracy sufficient for slack management.

---

## Rope Specification and Wear Management

### Rope Ownership
Gym-supplied or ARIA-supplied. Either supported. Gyms using their own rope must acknowledge minimum spec requirements in writing at installation.

### Minimum Rope Specification

| Parameter | Requirement |
|---|---|
| Diameter | 9.5mm – 10.5mm |
| Type | Single rope (EN 892) |
| Treatment | Dry-treated required |
| Certification | CE / UIAA EN 892 minimum |
| Breaking strength | ≥ 8kN |
| Length | 50m minimum |

### Retirement Criteria (operator manual)
- Any visible core exposure, flat spots, glazing, or stiffness → retire immediately
- Post-fall inspection after any high-speed clutch engagement
- 5-year time limit from manufacture date regardless of condition

### Rope Life Tracking (Phase 3+)
Cumulative payout logged from AS5048A. Dashboard shows rope health %. Alert at configurable threshold (default 50,000m). No existing auto belay offers this — genuine product differentiator.

---

## Housing Design Requirements

### Mounting
Dual mount: bolts to wall face + floor simultaneously. Creates moment couple resisting overturning force from rope tension. Wall bolts at top of housing back plate (maximize moment arm). Floor bolts resist sliding and compression.

**⚠ STRUCTURAL ANALYSIS REQUIRED — see prompts below.**

### IP Rating
Target IP54 — dust protected, splash resistant. Achieved via: cable entry grommets, foam filter inserts on vents (replaceable, blocks chalk dust), foam gasket on housing lid seam, drip lips over any downward openings. E-stop button is IP65 rated independently.

### Thermal Management
VESC MINI: adhesive aluminum heatsink. Passive convection — cool air in at bottom vents, warm air out at top vents. No fan required at 20–30 climbs/day duty cycle. Vent slots positioned for natural convection path in housing CAD. Foam filter inserts on all vents.

### Tie-In Station
Rope end hangs at ~1.5m off ground when ARIA is idle. Wearable storage clip at this height. Ground anchor point for rope when not in use (climber unclips to start).

---

## Structural Analysis — Required Before Hardware Finalization

### Fall Factor Analysis (Bolt 1 Worst Case)

**Use this prompt with Perplexity or ChatGPT:**

*"I'm designing a lead climbing auto belay device that mounts at the base of the wall. I need to calculate the worst-case fall scenario for certification purposes. Parameters: climber ties in at 1.5m off the ground, first bolt is at 2.5m height, climber weight range 40–120kg, catch mechanism is a centrifugal clutch that engages at a minimum rope payout velocity (unknown — solve for maximum safe engagement threshold), rope is EN 892 single rope with ~8% elongation at 80kg fall, device is at base with rope feeding upward through first quickdraw at 2.5m and back down to climber. Calculate: (1) fall factor for a fall just before clipping bolt 1, (2) fall distance before clutch engages at various engagement speeds, (3) peak impact force on climber at 40kg and 120kg, (4) maximum allowable clutch engagement speed to keep peak force below 6kN (EN 892 limit), (5) whether a ground fall is possible and under what conditions. Show all working. This is for a Z359.14 certification package."*

**Output needed:** Maximum allowable clutch engagement speed, minimum first bolt height requirement for operator manual.

### Wall Mount Structural Analysis

**Use this prompt with Perplexity or ChatGPT:**

*"I'm designing a wall and floor mount for a lead climbing auto belay device. Parameters: device mounts flush against a climbing wall, bolted to both wall face and floor, rope exits vertically upward from top of device, peak rope tension during fall 6kN (EN 892 maximum), device housing 6061-T6 aluminum, approximate dimensions 300mm wide × 400mm tall × 200mm deep, wall substrate either concrete block or plywood-over-steel-stud climbing wall panel, floor substrate concrete. Calculate: (1) overturning moment from 6kN vertical rope load assuming rope exits at top of device, (2) required wall bolt tension to resist overturning, (3) minimum bolt spec for wall fasteners in both concrete and plywood-over-stud substrates, (4) minimum floor bolt spec, (5) whether 6061-T6 housing spanning between wall and floor bolts needs reinforcement at 4mm minimum wall thickness, (6) safety factor at each bolt spec. Show all working. For Z359.14 certification package."*

**Output needed:** Wall bolt spec (M size + grade + embedment), floor bolt spec, housing back plate minimum thickness, minimum wall substrate requirements for operator manual.

---

## Power Architecture

```
AC Mains → Mean Well LRS-350-24 (24V/14.6A) → 24V bus
                                                    │
          ┌─────────────────────┬──────────────────┤
          │                     │                  │
     Gearmotor (via VESC)   Brake coil         VESC MINI logic
                            (via MOSFET)
                                     │
                               5V Buck Converter
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                STM32F411        ESP32-S3        HX711/sensors
```

**Peak power budget:** ~11.5A. LRS-350-24 at 14.6A provides 27% headroom.

---

## Hardware BOM — Optimized

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| Safety MCU | STM32F411 Black Pill ×1 | $5 | Safety layer only |
| Programmer | ST-Link V2 | $8 | Dev only |
| Intelligence MCU | XIAO ESP32-S3 Sense | $15 | Camera + mic built in |
| Motor driver | Makerbase VESC MINI 6.7 | $45–55 | FOC, 50A, UART |
| Gearmotor | 57mm BLDC planetary, 24V, 25–35:1, 150–200W, power-off brake + encoder | $85–120 | ATO / Peaco / DMK Motor |
| Tension sensor | HX711 + 50kg load cell | $8 | Sheave reaction force mount |
| Rope encoder | AS5048A magnetic encoder | $12 | Spool shaft only |
| Power supply | Mean Well LRS-350-24 | $28–35 | |
| 5V buck converter | Mini560 or similar | $4 | |
| Brake control circuit | IRLZ44N + 1N4007 + resistors | $3 | |
| E-stop button | 40mm mushroom head, NC, twist-release, IP65 | $10–12 | |
| VESC heatsink | Adhesive aluminum heatsink | $3–5 | |
| Alert: screen | SSD1306 OLED 128×64 I2C | $4 | |
| Alert: buzzer | Passive piezo buzzer | $2 | |
| IP54 hardware | Grommets + foam gasket + vent filters | $6 | |
| Wearable voice unit | nRF52810 + PDM mic + CR2032 + housing | $8–15 | Ships with device |
| **Total** | | **~$246–309** | |

---

## Key Design Decisions — Resolved

| Decision | Resolution |
|---|---|
| Motor | 57mm BLDC planetary gearmotor — load-rated |
| Failsafe on power loss | Integrated power-off brake — spring-engages automatically |
| FOC responsibility | VESC MINI — STM32F411 removed from motor control |
| MCU count | One STM32F411 (safety only) |
| Power supply | Mean Well LRS-350-24, 24V/14.6A |
| Brake circuit | MOSFET-switched, flyback-protected, E-stop in series |
| AS5048A role | Rope spool position only |
| Rope connection | Figure-8 tie-in — identical to normal lead climbing |
| Rope management | Climber unclips all draws on lower; ARIA retracts free rope to 1.5m |
| Voice range solution | Wearable BLE mic unit clips to harness, ships with device |
| Multi-device interference | Wearable bonds exclusively to one ARIA unit at session start |
| E-stop | 40mm NC twist-release, hardware-level, wired in series with brake coil |
| Thermal | Passive heatsink on VESC, convection venting, no fan |
| IP rating | IP54 — foam filters, grommets, lid gasket |
| Climber weight range | 40–120kg matching Lead Solo |
| VESC fault handling | Brake engage + EMERGENCY_STOP state on any VESC fault |

---

## Repository Structure

```
aria-auto-belay/
├── firmware/
│   ├── stm32/
│   │   └── aria_stm32_complete.cpp
│   └── esp32/
│       └── aria_esp32_firmware.ino
├── tools/
│   ├── aria_simulator.py
│   ├── aria_monitor.py
│   ├── aria_test_harness.py
│   ├── aria_pid_tuner.py
│   └── aria_collect_audio.py
└── docs/
    ├── ARIA_SETUP.md
    ├── ARIA_SAFETY_MONITORING.md
    └── ARIA_APP_SPEC.md
```

---

## Build Phases

| Phase | Description | Status |
|---|---|---|
| 1 | Mechanical — Lead Solo design, housing CAD, sheave, mount | Not started |
| 2 | Motor + VESC + brake — slack management firmware | In progress |
| 3 | Voice — Edge Impulse wake words + wearable BLE | In progress |
| 4 | Camera safety monitoring — zone intrusion, session detection | Planned |
| 5 | Full fusion — BLE app, climber ID, bolt map UI, rope tracking | Planned |

---

## Pending Work

### 🔴 Blocking — Must complete before hardware purchase or POC install
- [ ] Fall factor analysis at bolt 1 — run prompt, determine max clutch engagement speed and min first bolt height
- [ ] Wall mount structural analysis — run prompt, determine bolt specs and back plate thickness
- [ ] Lawyer engaged — installation agreement, climber waiver, product liability insurance before any gym install

### 🟡 Firmware — Active development
- [ ] Update `aria_stm32_complete.cpp` — remove FOC layer, add VESC UART commands, brake GPIO, E-stop GPIO
- [ ] Add CLIMBING_PAUSED state to STM32 state machine
- [ ] Add brake control logic to all state transitions
- [ ] Add VESC fault handler (fault packet → EMERGENCY_STOP)
- [ ] Wiring verification script
- [ ] ESP32: add wearable BLE audio receive path, dual audio source logic

### 🟡 Hardware — Before Phase 1 CAD
- [ ] Motor profiling once hardware arrives (VESC Tool auto-profile)
- [ ] Sheave wear indicator designed into sheave CAD
- [ ] Wearable voice unit hardware design (nRF52810 + PDM mic + CR2032)

### 🟡 Documentation
- [ ] Minimum rope specification finalized and added to operator manual draft
- [ ] Operator manual outline (required for Intertek scoping call)
- [ ] Intertek contact re: Z359.14 device classification

### 🟢 Phase 3+ (not blocking current work)
- [ ] Bolt learning buffer and 1D clustering on STM32
- [ ] Route reset detection logic
- [ ] Safety monitoring FreeRTOS task (`camera_safety_task`)
- [ ] Background subtraction for zone intrusion
- [ ] Rope life tracking (cumulative payout + app dashboard)

### 🟢 Phase 4+ (planned)
- [ ] Hall effect sensor integration for magnetic rope markers
- [ ] Session detection gesture model
- [ ] App bolt map visualization and manual override UI
- [ ] SBIR application (post POC completion)
