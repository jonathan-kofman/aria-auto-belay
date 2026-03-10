# ARIA Firmware Sync Pipeline — 2026-03-10

Complete implementation of 6-phase firmware sync connecting CEM physics to firmware constants.

---

## 1. SPOOL_R fix: confirmed effective_rope_radius_m = 0.30 m

**Changes in aria_cem.py:**
- `ARIAInputs`: split `rope_spool_diameter_mm` into `rope_spool_hub_diameter_mm` (120 mm) and `rope_spool_od_mm` (600 mm)
- `RopeSpoolGeom`: added `effective_rope_radius_m`
- `compute_rope_spool()`: `effective_rope_radius_m = rope_spool_od_mm / 2 / 1000` = 0.30 m
- `MotorSpec`: added `velocity_limit_rad_s` = motor_speed_rpm × 2π / 60 ≈ 314 rad/s

**Verification:**
```
effective_rope_radius_m: 0.3
velocity_limit_rad_s: 314.1592653589793
gearbox_ratio: 50.0
```

---

## 2. Safety bug: g_tension_n references fixed

**Location:** `firmware/stm32/safety.cpp` line 29

**Fix:** Changed `extern float g_tension_n` to `extern float g_tension` to match `aria_main.cpp` declaration.

**Count:** 1 reference to `g_tension_n` in safety.cpp (the extern declaration only).

---

## 3. CEM export: full JSON output

**Function:** `export_sync_constants(geom, inp, out_path)` in aria_cem.py

**Full JSON (outputs/cem_constants.json):**
```json
{
  "SPOOL_R": 0.3,
  "GEAR_RATIO": 50.0,
  "MOTOR_VELOCITY_LIMIT": 314.1592653589793,
  "MOTOR_TORQUE_NM": 0.5,
  "T_BASELINE": 40.0,
  "T_RETRACT": 60.0,
  "SPD_RETRACT": 1.5,
  "SPD_FALL": 1.275,
  "VOICE_CONF_MIN": 0.85,
  "CLIP_CONF_MIN": 0.75,
  "CLIP_SLACK_M": 0.65,
  "T_TAKE": 200.0,
  "T_FALL": 400.0,
  "T_GROUND": 15.0
}
```

---

## 4. Sync check results: --from-cem --verbose

**Command:** `python tools/aria_constants_sync.py --from-cem --verbose`

**Output (after patch):**
```
============================================================
ARIA CONSTANTS SYNC CHECK
  2026-03-10T01:12:18.962821
============================================================

Firmware files scanned: 6
  aria_main.cpp, calibration.cpp, safety.cpp, safety.h, wiring_verify.cpp, wiring_verify.h

[OK] MATCHES (10)
  SPOOL_R                             = 0.3  (firmware\stm32\aria_main.cpp:52)
  GEAR_RATIO                          = 50.0  (firmware\stm32\aria_main.cpp:51)
  T_BASELINE                          = 40.0  (firmware\stm32\aria_main.cpp:55)
  SPD_RETRACT                         = 1.5  (firmware\stm32\aria_main.cpp:63)
  SPD_FALL                            = 1.275  (firmware\stm32\aria_main.cpp:64)
  CLIP_CONF_MIN                       = 0.75  (firmware\stm32\aria_main.cpp:60)
  CLIP_SLACK_M                        = 0.65  (firmware\stm32\aria_main.cpp:61)
  T_TAKE                              = 200.0  (firmware\stm32\aria_main.cpp:57)
  T_FALL                              = 400.0  (firmware\stm32\aria_main.cpp:58)
  T_GROUND                            = 15.0  (firmware\stm32\aria_main.cpp:59)

[!] NOT FOUND IN FIRMWARE (17)
  TENSION_CLIMB_MIN_N, TENSION_TAKE_CONFIRM_N, ... (Python model names; firmware uses T_*)

------------------------------------------------------------
[OK] ALL CLEAR - 10 constants match, 17 not found in firmware
   Python model and firmware are in sync.
============================================================
```

---

## 5. Constants: matched, mismatched, patched

| Constant    | Before patch | After patch | Status   |
|-------------|--------------|-------------|----------|
| SPOOL_R     | 0.30         | 0.30        | MATCH    |
| GEAR_RATIO  | 30.0         | 50.0        | PATCHED  |
| T_BASELINE  | 40.0         | 40.0        | MATCH    |
| SPD_RETRACT | 0.8          | 1.5         | PATCHED  |
| SPD_FALL    | 2.0          | 1.275       | PATCHED  |
| CLIP_CONF_MIN | 0.75       | 0.75        | MATCH    |
| CLIP_SLACK_M  | 0.65       | 0.65        | MATCH    |
| T_TAKE      | 200.0        | 200.0       | MATCH (not patched — safety) |
| T_FALL      | 400.0        | 400.0       | MATCH (not patched — safety) |
| T_GROUND    | 15.0         | 15.0        | MATCH    |

**Patched:** GEAR_RATIO, SPD_RETRACT, SPD_FALL (3 constants). T_TAKE and T_FALL were excluded from auto-patch per spec.

---

## 6. PID tuner CEM validation: voltage at fall detection

**Formula:** max_voltage = Kp × (T_FALL − T_BASELINE) = Kp × 360 N

**For Kp = 0.08:**
- max_voltage = 0.08 × 360 = **28.8 V**
- VOLTAGE_LIMIT = 10.0 V
- **Result: WARN** — Kp would produce 28.8 V at fall detection, exceeding 10 V limit.

**Recommendation:** Scale Kp down to ≤ 10/360 ≈ 0.028 for CEM-validated operation, or accept WARN for aggressive response.

---

## 7. Honest assessment: is firmware driven by physics?

**Yes, for geometry and tension/speed constants.** After this pipeline:

- **CEM-driven:** SPOOL_R, GEAR_RATIO, T_BASELINE, SPD_RETRACT, SPD_FALL, T_GROUND, CLIP_CONF_MIN, CLIP_SLACK_M
- **Design-driven (in CEM export):** T_TAKE, T_FALL (ANSI/design requirements)
- **Still hardcoded in firmware:** VOLTAGE_LIMIT, HX711_SCALE, encoder CPR, PID gains, timing (REST_MS, WATCH_MS), safety v_mag_limit

**Workflow:** Run `export_sync_constants()` → `aria_constants_sync.py --from-cem` → `--patch` for safe constants. Firmware geometry and tension/speed targets now trace to CEM.

**Gaps:** Motor voltage limit, encoder scaling, PID gains, and timing constants remain manual. PID tuner `--from-cem` validates gains against CEM but does not auto-tune.

---

## 8. What's left for Direction A (catch mechanism optimization)?

From the audit, Direction A focuses on **centrifugal clutch and arrest performance**:

1. **Clutch engagement tuning:** `clutch.engagement_v_m_s` (1.275 m/s) is now synced to SPD_FALL. Further optimization: flyweight mass, spring preload, detection margin vs. false triggers.
2. **Arrest distance/force:** CEM predicts `predicted_arrest_distance_m`, `predicted_peak_force_kN`. Firmware does not use these; clutch handles mechanical arrest. Optional: add firmware limits derived from CEM arrest predictions.
3. **SPD_FALL vs. design:** CEM gives 1.275 m/s (0.85 × fall_detection_v_m_s). Firmware was 2.0 m/s. Now synced to CEM. Design choice: conservative (lower SPD_FALL) vs. fewer false triggers (higher).
4. **Ratchet/pawl:** CEM computes tooth load, safety factor. No firmware constant; mechanical only.
5. **Brake drum:** CEM computes hoop stress, wall thickness. No firmware constant; mechanical only.

**Next steps for Direction A:** Validate clutch engagement on hardware with SPD_FALL=1.275; consider adding CEM arrest predictions to firmware as sanity checks or limits.

---

## Appendix: sync_report.json (Phase 6 Step 5)

```json
{
  "timestamp": "2026-03-10T01:12:22.294072",
  "firmware_files_found": 6,
  "matches": [
    {"name": "SPOOL_R", "value": 0.3, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 52},
    {"name": "GEAR_RATIO", "value": 50.0, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 51},
    {"name": "T_BASELINE", "value": 40.0, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 55},
    {"name": "SPD_RETRACT", "value": 1.5, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 63},
    {"name": "SPD_FALL", "value": 1.275, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 64},
    {"name": "CLIP_CONF_MIN", "value": 0.75, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 60},
    {"name": "CLIP_SLACK_M", "value": 0.65, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 61},
    {"name": "T_TAKE", "value": 200.0, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 57},
    {"name": "T_FALL", "value": 400.0, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 58},
    {"name": "T_GROUND", "value": 15.0, "fw_file": "firmware\\stm32\\aria_main.cpp", "fw_line": 59}
  ],
  "mismatches": [],
  "patches_applied": []
}
```
