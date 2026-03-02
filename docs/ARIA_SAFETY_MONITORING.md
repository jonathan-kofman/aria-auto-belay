# ARIA Safety Monitoring System
## Camera-Based Safety Module Specification

**Document Version:** 0.2  
**Status:** Architecture — Decisions Locked  
**Component:** ESP32-S3 Intelligence Layer — Safety Monitoring Subsystem

---

## 1. Overview

ARIA's camera (OV2640 on XIAO ESP32-S3 Sense) is mounted at the base of the wall as part of the ARIA unit. Because the device sits at floor level looking upward at a 30–60° angle, it cannot reliably track the climber mid-route. Instead, the camera is dedicated to **ground-level safety monitoring** — the zone where most preventable accidents occur.

The camera feeds are **not** part of the primary slack management loop (that is handled by encoder + load cell fusion on STM32). Camera events are secondary signals that trigger state transitions and alerts via the existing UART protocol.

---

## 2. Camera Field of View

**Mount position:** On ARIA housing, base of wall  
**Angle:** Fixed upward tilt, 30–60° from horizontal (adjustable per install)  
**Effective monitoring zone:** 0–3m from base of wall, roughly a 4m wide arc  
**Resolution used:** 320×240 (QVGA) at 10–15fps — sufficient for zone detection, conserves ESP32-S3 processing headroom

This zone covers:
- The ground directly below the route (fall landing zone)
- The area where a climber steps in to tie in and start climbing
- The area where bystanders tend to stand watching

---

## 3. Alert and Notification Hardware

ARIA includes two dedicated alert output devices, both driven by the ESP32-S3:

**Buzzer / Speaker**
- Piezo buzzer or small speaker attached to ARIA housing
- Alert patterns: single tone = zone warning, double tone = zone cleared, continuous = motor paused
- Volume must be audible over typical gym noise (~70–80dB ambient)

**Screen**
- Small display (SSD1306 OLED or similar) on ARIA housing front face
- Shows: current state, zone status, alert reason, resume instructions
- During normal operation: minimal display (state + tension indicator)
- During alert: full-screen warning with clear human-readable message

**Example screen states:**

| Condition | Display |
|---|---|
| Normal climb | `CLIMBING — OK` |
| Zone intrusion warning | `⚠ FALL ZONE OCCUPIED` / `MOTOR PAUSED` |
| Zone cleared, auto-resume | `ZONE CLEAR — RESUMING` |
| Awaiting voice resume | `SAY "CLIMBING" TO RESUME` |

---

## 4. Safety Monitoring Functions

### 4.1 Fall Zone Intrusion Detection (MUST-HAVE)

**What it does:** Detects any object — person, bag, equipment — stationary in the fall zone for 10+ seconds while a climber is on the wall.

**Detection logic:**
- Background subtraction detects any new object entering the monitored zone
- Object must remain present for **10 continuous seconds** before alert triggers
- Objects present for under 10 seconds (someone walking through) are ignored
- No person vs. object distinction — everything is treated identically
- Zone monitoring is only active when STM32 state is CLIMBING, CLIPPING, or REST (load cell confirms climber on wall)

**ARIA response sequence:**

1. Object enters zone → internal timer starts, no action
2. 10 seconds elapsed, object still present → buzzer alert + screen warning
3. Motor immediately pauses — STM32 holds current rope position, does not pay out slack
4. Zone clears OR climber says "climbing" → motor resumes, screen returns to normal, double-tone buzzer

**UART packets:**

```
W:ZONE_INTRUSION:1        // Object detected, timer started
W:ZONE_INTRUSION:ALERT    // 10s threshold crossed, pause + alert triggered
W:ZONE_INTRUSION:0        // Zone cleared
```

**STM32 behavior on ZONE_INTRUSION:ALERT:**
- Motor hold — no payout, no retract
- State does not change (remains CLIMBING/CLIPPING/REST)
- Resume triggers: ZONE_INTRUSION:0 (auto-clear) OR voice command "climbing"
- Fall detection remains fully active during pause — brake engagement is never inhibited

**False positive mitigation:**
- 10-second threshold eliminates walkers-through and brief equipment drops
- Zone is only hot when load cell confirms active climb
- Background model re-calibrates during IDLE state between climbs

---

### 4.2 Climber Session Detection (MUST-HAVE)

**What it does:** Detects when a new climber steps up to the wall and interacts with the rope, triggering ARIA wake-up from IDLE. Provides a second confirmation signal alongside rope tension to reduce false wake-ups.

**Detection approach:**
- Person detection in the immediate base zone (0–1.5m from wall)
- Upward arm reach gesture toward rope end
- Both signals required: camera detects person + encoder detects rope movement

**ARIA response:**
- ESP32 sends: `S:SESSION_START:0` (no climber ID in base config)
- STM32 transitions IDLE → CLIMBING_READY
- Motor pre-tensions rope to standby tension
- Screen shows: `CLIMBER DETECTED — READY`

**Session end detection:**
- Climber returns to base zone after lowering
- Rope tension drops to zero AND camera detects person at base
- ESP32 sends: `S:SESSION_END:0`
- STM32 transitions → IDLE, motor relaxes

---

### 4.3 Climber ID via Bluetooth App (NICE-TO-HAVE, Phase 5)

**What it does:** Identifies the climber via a gym app Bluetooth handshake at session start, enabling per-climber profiles.

**How it works:**
- Gym app on climber's phone connects to ARIA via BLE as they approach the wall
- App sends climber profile hash to ARIA
- ARIA loads profile parameters: preferred tension sensitivity, slack aggressiveness, session history
- Session data (height reached, falls, clips) written back to app at session end

**Why BLE over QR/NFC:**
- No physical interaction required — passive handshake as climber approaches
- Profiles live in the app, not on-device — easier to update, gym manages accounts
- BLE already available on ESP32-S3 — no additional hardware

**UART packet:**
```
I:CLIMBER_ID:profile_hash    // Profile loaded, STM32 applies parameters
```

ARIA functions fully without a connected app. Bluetooth ID is additive, not required. Unknown climbers use default profile.

---

### 4.4 Fall Confirmation (Secondary Redundant Signal)

**What it does:** Provides a camera-based secondary confirmation of a fall event to supplement the primary encoder + load cell detection.

**Detection approach:**
- Fast downward motion in the lower wall zone (1–4m height)
- Falling climber generates rapid vertical motion blur detectable from base
- Onset is near-instantaneous vs. the soft onset of a voluntary movement

**Role in fall detection:**
- Camera alone does **NOT** engage the brake — encoder + load cell is the primary path
- Camera sends `W:FALL_DETECTED:CAMERA` as a cross-check
- STM32 logs camera confirmation alongside sensor data for post-event analysis
- Future use: if encoder fails, camera + load cell may be sufficient for fall trigger (requires validation testing before enabling)

---

## 5. What the Camera Does NOT Do

Explicitly out of scope:

| Function | Reason |
|---|---|
| Mid-route climber position tracking | Perspective compression, overhang occlusion from base |
| Clip detection | Too far from bolt stations to see hand/draw interaction |
| Full-body pose estimation | Insufficient resolution and angle |
| Primary fall trigger | Encoder + load cell are faster and more reliable |
| Face recognition | Unreliable at 320×240 in variable gym lighting — BLE app used instead |

---

## 6. Processing Architecture

All camera processing runs on the **ESP32-S3**. The STM32 safety layer receives only event packets via UART — it never processes raw image data.

```
OV2640 (320x240 @ 10fps)
         │
         ▼
ESP32-S3 — FreeRTOS Task: camera_safety_task (Priority 2 — highest)
         │
    ┌────┴──────────────────────────────┐
    │                                   │
    ▼                                   ▼
Background subtraction            Session / ID detection
+ 10s stationary timer            + BLE app handshake
(zone intrusion, fall blur)       (rope grab gesture)
    │                                   │
    └──────────────┬────────────────────┘
                   │
                   ▼
           UART event packets → STM32
           BLE profile data → ESP32 internal
           Screen + buzzer → ESP32 GPIO direct
```

### FreeRTOS Task Priority

```cpp
xTaskCreate(safetyMonitorTask, "safety", 4096, NULL, 2, NULL);  // Highest — camera safety
xTaskCreate(voiceTask,         "voice",  4096, NULL, 1, NULL);  // Voice commands
xTaskCreate(cvTask,            "cv",     8192, NULL, 1, NULL);  // Climber CV
```

Safety monitor runs at higher priority than voice and CV tasks because zone intrusion events must not be delayed by inference workloads.

---

## 7. Complete UART Protocol — Safety Extensions

All new packets follow existing format: `TYPE:FIELD:VALUE\n`

| Packet | Example | Trigger |
|---|---|---|
| Zone intrusion start | `W:ZONE_INTRUSION:1` | Object enters zone |
| Zone intrusion alert | `W:ZONE_INTRUSION:ALERT` | 10s threshold crossed |
| Zone cleared | `W:ZONE_INTRUSION:0` | Object leaves zone |
| Fall camera | `W:FALL_DETECTED:CAMERA` | Motion blur detected |
| Session start | `S:SESSION_START:0` | Climber at base |
| Session end | `S:SESSION_END:0` | Climber left base post-lower |
| Climber ID | `I:CLIMBER_ID:profile_hash` | BLE app handshake complete |

---

## 8. STM32 State Machine — Zone Intrusion Additions

New transition rules added to existing state machine:

```
CLIMBING / CLIPPING / REST
    + W:ZONE_INTRUSION:ALERT
    → CLIMBING_PAUSED (new sub-state)
        Motor: hold position
        Brake: NOT engaged (fall detection still fully active)
        Screen: "FALL ZONE OCCUPIED / MOTOR PAUSED"
        Buzzer: continuous tone
        Resume on: W:ZONE_INTRUSION:0  OR  voice "climbing"

CLIMBING_PAUSED
    + W:ZONE_INTRUSION:0
    → resume previous state, motor re-engages
    → Screen: "ZONE CLEAR — RESUMING"
    → Buzzer: double tone

CLIMBING_PAUSED
    + voice "climbing"
    → CLIMBING, motor re-engages
    (climber override — even if zone still occupied)
```

The climber voice override is intentional — ARIA warns, it does not permanently lock out. If a climber judges the situation safe and wants to continue, they can.

---

## 9. Hardware Requirements

No additional hardware beyond existing ARIA spec, except:

**Screen:** SSD1306 OLED (128×64, I2C) — ~$3–5, I2C to ESP32-S3  
**Buzzer/Speaker:** Passive piezo buzzer — ~$1–2, GPIO direct drive  
**Camera:** OV2640 already included on XIAO ESP32-S3 Sense

**Housing consideration:** ARIA front face needs a small angled cutout for the camera aimed at the base zone, plus screen cutout and buzzer port. Incorporate into Phase 2 mechanical design iteration.

**Updated BOM delta:** +$4–7

---

## 10. Development Phases

| Phase | Safety Monitoring Deliverable |
|---|---|
| 2 | No camera work — encoder + load cell only |
| 3 | Session detection — IDLE→READY transition, rope grab gesture |
| 4 | Zone intrusion — background subtraction, 10s timer, motor pause, screen + buzzer |
| 5 | BLE app climber ID, redundant fall confirmation, session data writeback |

Phase 4 zone intrusion is achievable without any ML model using background subtraction and blob detection. No Edge Impulse training required.

---

## 11. Resolved Design Decisions

| Question | Decision |
|---|---|
| Alert hardware | SSD1306 OLED screen + piezo buzzer/speaker on ARIA housing |
| Zone intrusion threshold | 10+ seconds stationary |
| Person vs. object distinction | None — all objects treated identically |
| Motor behavior during intrusion | Pause (hold position) + alert |
| Climber ID method | BLE gym app handshake |
| Motor resume trigger | Auto-clear when zone empty OR voice command "climbing" |
| Camera as primary fall trigger | No — secondary confirmation only |
