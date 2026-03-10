# ARIA Firmware Audit — 2026-03-10

Complete audit of tools, firmware, and CEM for firmware connection design.
No code changes made. Analysis only.

---

## Section 1 — aria_constants_sync.py

### What does it currently do? Is it functional or a stub?

**Functional.** It is a complete sync checker that:
1. Reads threshold/constant values from a hardcoded `PYTHON_CONSTANTS` dict (not from `aria_models/state_machine.py` — the docstring says "state_machine.py" but the source of truth is the dict in the script itself)
2. Scans `firmware/stm32/*.cpp` and `*.h` for matching constant definitions via regex
3. Compares values and reports matches, mismatches, and not-found
4. Optionally auto-patches firmware constants to match the Python model (`--patch`)

### What constants does it read and from where?

**Reads from:** The `PYTHON_CONSTANTS` dict defined in the script (lines 36–56):

| name | value | unit | description |
|------|-------|------|--------------|
| TENSION_CLIMB_MIN_N | 15.0 | N | Min tension to enter CLIMBING from IDLE |
| TENSION_TAKE_CONFIRM_N | 200.0 | N | Min tension to confirm TAKE after voice |
| TENSION_LOWER_EXIT_N | 15.0 | N | Tension below which LOWER transitions to IDLE |
| TAKE_CONFIRM_WINDOW_S | 0.5 | s | Window after voice "take" for load confirmation |
| VOICE_CONFIDENCE_MIN | 0.85 | - | Minimum Edge Impulse confidence to act on voice |
| CLIP_DETECT_CONFIDENCE | 0.75 | - | Minimum CV confidence to enter CLIPPING |
| CLIP_PAYOUT_M | 0.65 | m | Rope payout during CLIPPING state |
| TENSION_TARGET_N | 40.0 | N | Target climbing tension |
| TENSION_TIGHT_N | 60.0 | N | Tight tension in WATCH_ME state |
| REST_TIMEOUT_S | 600.0 | s | 10-minute REST auto-exit |
| WATCH_ME_TIMEOUT_S | 180.0 | s | 3-minute WATCH_ME auto-exit |
| ZONE_PAUSE_TIMEOUT_S | 10.0 | s | Zone intrusion pause timeout |
| ESTOP_BRAKE_DELAY_MS | 50.0 | ms | Max delay from ESTOP signal to brake engage |
| WATCHDOG_TIMEOUT_MS | 500.0 | ms | STM32 watchdog timeout |

**Does NOT read from:** `aria_models/state_machine.py`, `aria_cem.py`, or `context/aria_mechanical.md`.

### What does it write and to where?

- **Read-only mode (default):** Nothing. Only reports.
- **`--patch` mode:** Writes directly to firmware `.cpp`/`.h` files, replacing the numeric value in the matched line (e.g. `#define TENSION_TARGET_N 40.0` → `#define TENSION_TARGET_N 45.0`).
- **`--json-out`:** Writes JSON report to specified path (for CI).

### Key functions and signatures

```python
def find_firmware_files(repo_root: Path) -> list[Path]:
    """Find all .cpp and .h files under firmware/stm32/"""

def scan_firmware_for_constant(name: str, fw_files: list[Path]) -> dict:
    """Scan all firmware files for a given constant name. Returns first match."""

def run_sync_check(repo_root: Path, verbose: bool = False, patch: bool = False) -> dict:
    """Main sync check. Returns dict with matches, mismatches, not_found_in_firmware, summary."""

def _patch_firmware_constant(name, new_val, fw_match, fw_files, repo_root) -> bool:
    """Patch a single firmware constant to match the Python model value."""
```

---

## Section 2 — aria_pid_tuner.py

### What plant model does it use?

**No explicit plant model.** It uses empirical step-response analysis:
- Connects to STM32 over serial
- Sends tension setpoint step (e.g. 40N → 80N)
- Records timestamped tension values from `S:state:tension:rope_pos:motor_mode` packets
- Extracts: process gain K, dead time T_d, time constant T_c, rise time T_r, settling time T_s, overshoot
- Applies Ziegler-Nichols or Cohen-Coon tuning formulas to derive Kp, Ki, Kd

**Transfer function:** Implicit first-order + dead time (FOPDT) assumed by ZN/Cohen-Coon methods. No state-space or explicit transfer function in code.

### Inputs and outputs

**Inputs:**
- Serial port (auto-detect or `--port`)
- Step response: `--initial` (default 40N), `--final` (default 80N), `--duration` (default 15s)
- Tuning method: `--method zn|cc|relay`

**Outputs:**
- Printed Kp, Ki, Kd values
- Optional: save to `aria_pid_gains_YYYYMMDD_HHMMSS.txt`
- Sends `P:kp:ki:kd` to STM32 for live validation

### Does it use physical motor parameters anywhere?

**No.** No inertia, torque constant, back-EMF, or gear ratio. Gains are derived purely from:
- Process gain K = (steady_state - initial) / step_size
- Dead time T_d, time constant T_c from step response curve
- ZN/CC formulas: `Kp = (1.2/K)*(T_c/T_d)`, `Ti = 2*T_d`, `Td = 0.5*T_d`, etc.
- `SAFETY_SCALE = 0.6` or `0.65` applied to all gains

### What would need to change to connect to CEM-derived motor parameters?

1. **Add CEM inputs:** Load `ARIAInputs` / `compute_motor()` output (gearbox ratio, spool radius, target tension, max retract speed).
2. **Feed-forward or model-based tuning:** Use CEM-derived `required_torque_Nm`, `required_speed_rpm` to:
   - Set initial Kp guess from `T ≈ J*omega / T_motor` (if inertia known)
   - Or constrain gain search to physically plausible range
3. **Spool radius for position:** If encoder CPR is known, convert rope position to meters using `SPOOL_R` and `GEAR_RATIO` from CEM.
4. **Tension setpoint validation:** Ensure step targets (40N, 80N) are within CEM `target_tension_N` and `min_hold_force_kN` design range.

### Core simulation/tuning function signatures

```python
def analyze_step_response(history, t_step, initial_n, final_n):
    """Returns dict: K, T_d, T_c, T_r, T_s, overshoot_pct, steady_state_n, n_points"""

def tune_ziegler_nichols(K, T_d, T_c):
    """Returns (Kp, Ki, Kd) or None"""

def tune_cohen_coon(K, T_d, T_c):
    """Returns (Kp, Ki, Kd) or None"""

def run_step_tuning(collector, method="cc", initial_n=40.0, final_n=80.0, record_s=15.0):
    """Main flow: step, analyze, tune, validate, save. Returns Kp,Ki,Kd or None."""
```

---

## Section 3 — STM32 firmware constants audit

For `aria_main.cpp`, `safety.cpp`, `safety.h`, `calibration.cpp`, `wiring_verify.cpp`:

| name | value | units | category | description |
|------|-------|-------|----------|-------------|
| **aria_main.cpp** | | | | |
| PIN_AS5048_CS | PA4 | - | COMMS | Encoder SPI CS |
| PIN_HX711_DOUT | PB0 | - | COMMS | Load cell data |
| PIN_HX711_SCK | PB1 | - | COMMS | Load cell clock |
| PIN_UH, PIN_VH, PIN_WH | PA8, PA9, PA10 | - | COMMS | Motor phases |
| PIN_EN | PB10 | - | COMMS | Driver enable |
| PIN_LED | PC13 | - | COMMS | Status LED |
| PIN_ESTOP | PB12 | - | COMMS | E-stop input |
| PIN_BRAKE | PB13 | - | COMMS | Brake FET |
| HX711_OFFSET | 0 | counts | TUNABLE | Load cell offset (paste from cal) |
| HX711_SCALE | 1/420000 | N/count | TUNABLE | Load cell scale (paste from cal) |
| SUPPLY_V | 24.0 | V | GEOMETRY | Power supply voltage |
| VOLTAGE_LIMIT | 10.0 | V | SAFETY | Motor voltage limit |
| POLE_PAIRS | 7 | - | GEOMETRY | Motor pole pairs (overwritten by alignment) |
| **GEAR_RATIO** | **30.0** | **:1** | **GEOMETRY** | **Planetary gearbox — from physical design** |
| **SPOOL_R** | **0.30** | **m** | **GEOMETRY** | **Spool radius — from physical design (600mm dia → 0.30m)** |
| T_BASELINE | 40.0 | N | TUNABLE | Target climbing tension |
| T_WATCH_ME | 25.0 | N | TUNABLE | WATCH_ME tension |
| T_TAKE | 200.0 | N | TUNABLE | TAKE confirm tension |
| T_FALL | 400.0 | N | SAFETY | Fall detection threshold |
| T_GROUND | 15.0 | N | TUNABLE | Ground/idle tension threshold |
| CLIP_CONF_MIN | 0.75 | - | TUNABLE | CV clip confidence |
| CLIP_SLACK_M | 0.65 | m | TUNABLE | Rope payout during CLIPPING |
| SPD_LOWER | 0.5 | m/s | TUNABLE | Lower speed |
| SPD_RETRACT | 0.8 | m/s | TUNABLE | Retract speed |
| SPD_FALL | 2.0 | m/s | SAFETY | Fall speed threshold |
| TAKE_CONF_MS | 500 | ms | TUNABLE | TAKE confirm window |
| WATCH_MS | 180000 | ms | TUNABLE | WATCH_ME timeout (3 min) |
| REST_MS | 600000 | ms | TUNABLE | REST timeout (10 min) |
| CTRL_HZ | 20 | Hz | COMMS | Control loop rate |
| HX_HZ | 200 | Hz | COMMS | HX711 sample rate |
| tensionPID.kp | 0.08 | - | TUNABLE | PID Kp |
| tensionPID.ki | 1.5 | - | TUNABLE | PID Ki |
| tensionPID.kd | 0.0005 | - | TUNABLE | PID Kd |
| motor.velocity_limit | 200.0 | rad/s | SAFETY | Motor velocity limit |
| **safety.cpp** | | | | |
| v_mag_limit | 9.0 | V | SAFETY | Voltage command magnitude limit |
| v_mag_trip_ms | 50 | ms | TUNABLE | Must exceed for this long |
| encoder_stale_eps | 1e-4 | rad | TUNABLE | Encoder "no change" threshold |
| encoder_stale_ms | 150 | ms | TUNABLE | Stale duration |
| hx711_timeout_ms | 300 | ms | TUNABLE | No HX711 read within this |
| esp32_timeout_ms | 1000 | ms | TUNABLE | No ESP32 packet within this |
| recovery_grace_ms | 250 | ms | TUNABLE | Time to prove recovery |
| IWDG reload | 500 | ticks | SAFETY | Watchdog reload (~1s) |
| **calibration.cpp** | | | | |
| G_STD | 9.80665 | m/s² | - | Gravity |
| MAX_PTS | 12 | - | - | Cal points max |
| TARE_SAMPLES | 200 | - | - | Tare samples |
| POINT_SAMPLES | 80 | - | - | Samples per point |
| READ_TIMEOUT | 30000 | µs | - | HX711 read timeout |
| SUPPLY_VOLTAGE | 24.0 | V | GEOMETRY | Motor supply |
| OPENLOOP_VOLTAGE | 2.0 | V | TUNABLE | Motor alignment voltage |
| MAX_PP | 30 | - | - | Max pole pairs |
| ELEC_SWEEP_REVS | 6 | - | - | Alignment sweep revs |
| SWEEP_STEPS | 180 | - | - | Steps per rev |
| STEP_DELAY_US | 2500 | µs | - | Alignment step delay |
| DIR_TEST_STEPS | 120 | - | - | Direction test steps |
| DIR_TEST_DELAY_US | 3000 | µs | - | Direction test delay |
| MIN_MECH_DELTA | 0.10 | rad | - | Min movement for pass |
| **wiring_verify.cpp** | | | | |
| PHASE_PULSE_PWM | 70 | 0-255 | - | Phase test PWM |
| PHASE_PULSE_MS | 12 | ms | - | Phase pulse duration |
| ESP_BAUD | 115200 | baud | COMMS | UART baud |
| ESP_PING_TMO_MS | 200 | ms | COMMS | Ping timeout |
| HX_TIMEOUT_US | 250000 | µs | - | HX711 timeout |

### Flagged constants

- **Spool diameter/circumference:** `SPOOL_R = 0.30` m (radius). Context says rope spool dia 600mm — 600/2/1000 = 0.30 m. **Matches.** But CEM uses `rope_spool_diameter_mm = 120` (hub). Firmware may be using flange or effective radius — **inconsistency.**
- **Encoder CPR:** Not explicitly in STM32 code. AS5048A is 14-bit (16384 CPR). SimpleFOC handles this internally.
- **Motor RPM/torque:** `motor.velocity_limit = 200` rad/s (motor shaft). No explicit RPM constant. Gear ratio 30:1 used in `mpsToRads()`.
- **Load cell calibration:** `HX711_OFFSET`, `HX711_SCALE` — from calibration routine, not CEM.
- **PID gains:** `tensionPID.kp`, `.ki`, `.kd` — from aria_pid_tuner, not CEM.
- **Tension thresholds:** `T_BASELINE`, `T_TAKE`, `T_FALL`, `T_GROUND` — in Newtons. Map to CEM `target_tension_N`, `min_hold_force_kN`.

### Note on safety.cpp

`safety.cpp` line 29 declares `extern float g_tension_n` but `aria_main.cpp` defines `g_tension`. This is a **bug** — the symbol does not exist. Safety layer may not be using tension for fault logic (it uses HX711 timeout, encoder stale, etc.), but the extern is incorrect.

---

## Section 4 — ESP32 firmware constants audit

For `aria_esp32_firmware.ino`:

| name | value | units | category | description |
|------|-------|-------|----------|-------------|
| UART_BAUD | 115200 | baud | COMMS | STM32 UART |
| STM32_UART_TX | 43 | - | COMMS | GPIO |
| STM32_UART_RX | 44 | - | COMMS | GPIO |
| **VOICE_CONF_MIN** | **0.85** | **-** | **TUNABLE** | **Voice confidence threshold** |
| **CLIP_CONF_MIN** | **0.75** | **-** | **TUNABLE** | **CV clip confidence** |
| HEARTBEAT_INTERVAL_MS | 10000 | ms | COMMS | Firebase heartbeat |
| CMD_POLL_INTERVAL_MS | 5000 | ms | COMMS | Firebase command poll |
| **FALL_TENSION_DELTA** | **15.0** | **N** | **TUNABLE** | **Tension delta for fall detection** |
| WALL_H | 15.0 | m | GEOMETRY | Wall height for CV height calc |
| PKT0, PKT1, TYPE_PING, TYPE_ACK | 0xAA, 0x55, 0x01, 0x81 | - | COMMS | Ping/ACK protocol |

### Constants shared between STM32 and ESP32 (must stay in sync)

| Constant | STM32 | ESP32 | Notes |
|----------|-------|-------|-------|
| VOICE_CONF_MIN | (implicit 0.85 in `validVoice`) | VOICE_CONF_MIN 0.85 | Voice confidence |
| CLIP_CONF_MIN | CLIP_CONF_MIN 0.75 | CLIP_CONF_MIN 0.75 | CV clip confidence |
| UART baud | 115200 | 115200 | Must match |
| Ping/ACK protocol | PKT0, PKT1, TYPE_* | Same | Binary protocol |
| State IDs | STATE_IDLE=0, etc. | Parsed from S: | ESP32 receives state from STM32 |
| Tension | T_BASELINE, T_FALL, etc. | FALL_TENSION_DELTA | ESP32 uses delta for fall event; STM32 owns thresholds |

---

## Section 5 — aria_cem.py outputs

### compute_motor() — exact function signature and fields

```python
def compute_motor(inp: ARIAInputs, spool: RopeSpoolGeom) -> MotorSpec:
```

**MotorSpec dataclass fields:**

| field | type | example value | units | maps to firmware? |
|-------|------|---------------|-------|-------------------|
| required_torque_Nm | float | ~0.72 | Nm | No direct mapping |
| required_speed_rpm | float | ~239 | rpm | No direct mapping |
| gearbox_ratio | float | 30.0 | :1 | **GEAR_RATIO** |
| motor_torque_Nm | float | 0.5 | Nm | No |
| motor_speed_rpm | float | 3000.0 | rpm | motor.velocity_limit (rad/s) |
| back_drive_torque_Nm | float | ~0.03 | Nm | No |
| recommendation | str | "T-Motor GB54-2..." | - | No |

**Note:** `motor_peak_Nm` and `motor_peak_RPM` are hardcoded inside `compute_motor()` (0.5 Nm, 3000 RPM), not from inputs.

### compute_brake_drum() — exact function signature and fields

```python
def compute_brake_drum(inp: ARIAInputs) -> BrakeDrumGeom:
```

**BrakeDrumGeom fields:**

| field | type | units | maps to firmware? |
|-------|------|-------|-------------------|
| diameter_mm | float | mm | No (clutch mechanical) |
| width_mm | float | mm | No |
| wall_thickness_mm | float | mm | No |
| mass_kg | float | kg | No |
| hoop_stress_MPa | float | MPa | No |
| safety_factor | float | - | No |

**Firmware does not use brake drum dimensions directly.** Clutch is mechanical; STM32 controls motor and brake GPIO.

### compute_rope_spool() — fields

```python
def compute_rope_spool(inp: ARIAInputs) -> RopeSpoolGeom:
```

| field | type | units | maps to firmware? |
|-------|------|-------|-------------------|
| hub_diameter_mm | float | mm | **SPOOL_R** = hub_diameter_mm/2/1000 (m) |
| flange_diameter_mm | float | mm | No |
| width_mm | float | mm | No |
| layers | int | - | No |
| capacity_m | float | m | No |
| moment_of_inertia_kg_m2 | float | kg·m² | No |

### compute_centrifugal_clutch() — fields

```python
def compute_centrifugal_clutch(inp: ARIAInputs, drum: BrakeDrumGeom) -> CentrifugalClutchGeom:
```

| field | type | units | maps to firmware? |
|-------|------|-------|-------------------|
| n_flyweights | int | - | No |
| flyweight_mass_g | float | g | No |
| flyweight_radius_mm | float | mm | No |
| spring_preload_N | float | N | No |
| engagement_rpm | float | rpm | No (clutch is mechanical) |
| engagement_v_m_s | float | m/s | **SPD_FALL** (fall detection speed) — conceptual link |
| safety_margin | float | - | No |

**CEM `engagement_v_m_s`** ≈ rope speed at which clutch engages. Firmware `SPD_FALL = 2.0` m/s is a separate threshold for "motor hold, clutch handles arrest" — related but not synced.

### CEM → firmware mapping summary

| CEM field | Firmware constant | Status |
|-----------|-------------------|--------|
| motor.gearbox_ratio | GEAR_RATIO | Could sync (both 30) |
| spool.hub_diameter_mm | SPOOL_R | **Mismatch:** CEM 120mm hub → 0.06m; firmware 0.30m (300mm) |
| inp.target_tension_N | T_BASELINE | Could sync (both 40) |
| clutch.engagement_v_m_s | SPD_FALL | Could sync (CEM ~1.3 m/s; firmware 2.0) |
| inp.min_hold_force_kN*1000 | T_FALL, T_TAKE | Partial (T_TAKE 200N, T_FALL 400N vs 8kN hold) |

---

## Section 6 — Sync architecture recommendation

### A) Does the firmware currently #include any generated header files?

**No.** All constants are hardcoded in `.cpp`/`.ino` files. No `#include "aria_constants.h"` or similar.

### B) Does aria_constants_sync.py currently write to firmware files?

**Yes, when `--patch` is used.** It patches `#define` and `constexpr` values directly in the source files via regex replace.

### C) Which sync approach will work with least risk?

**Recommendation: Option B — aria_constants_sync.py patches #define values directly**

**Reasoning:**
1. **Option A (generate aria_constants.h):** Would require adding `#include "aria_constants.h"` to every firmware file that uses constants, and removing existing definitions. Higher risk of breaking builds; more files to touch.
2. **Option B (patch in place):** Already implemented. `aria_constants_sync.py` has `_patch_firmware_constant()`. Extend `PYTHON_CONSTANTS` to include CEM-derived values and run with `--patch`. Minimal structural change.
3. **Option C (JSON file):** Firmware would need a JSON parser (not standard on embedded). More complexity.
4. **Option D:** Custom build step that generates `.h` from JSON — adds build complexity.

**Concrete recommendation:** Extend `aria_constants_sync.py` to:
1. Accept CEM output (from `aria_cem.py` or a JSON export) as input
2. Merge CEM-derived constants (SPOOL_R, GEAR_RATIO, T_BASELINE, T_TAKE, T_FALL, SPD_FALL) into the sync set
3. Keep existing `--patch` behavior for firmware
4. Add a new mode: `--from-cem` or `--cem-json path` to load CEM results and use those as source of truth for geometry-derived constants

**Risk:** Regex patching can fail if formatting changes. Mitigation: keep patterns in `FIRMWARE_PATTERNS` and add tests.

---

## Section 7 — Gap analysis

### 7a) Constants the firmware needs that CEM computes

| firmware_constant | cem_field | notes |
|-------------------|-----------|-------|
| GEAR_RATIO | motor.gearbox_ratio | Both 30 |
| SPOOL_R | spool.hub_diameter_mm / 2 / 1000 | **Units mismatch:** CEM hub 120mm → 0.06m; firmware 0.30m. Context says 600mm spool — clarify which radius (hub vs effective) |
| T_BASELINE | inp.target_tension_N | Both 40 |
| T_TAKE, T_FALL | inp.min_hold_force_kN * 1000 | CEM 8kN; firmware uses 200N (TAKE), 400N (FALL) for different purposes |
| SPD_FALL | clutch.engagement_v_m_s | CEM ~1.3 m/s; firmware 2.0 m/s |
| SPD_RETRACT | inp.max_retract_speed_m_s | Both ~1.5 m/s |
| CLIP_SLACK_M | (CLIP_PAYOUT_M in sync) | 0.65 m |

### 7b) Constants the firmware needs that CEM does NOT compute (gaps)

| constant | what it is | how to derive | physical inputs needed |
|----------|------------|---------------|-------------------------|
| **Encoder CPR / resolution** | Counts per revolution for rope position | AS5048A is 14-bit (16384 CPR). Position = (shaft_angle/2π) * (spool_circumference) / gear_ratio | Encoder datasheet, SPOOL_R, GEAR_RATIO |
| **HX711_OFFSET, HX711_SCALE** | Load cell calibration | From calibration routine with known weights | Physical calibration |
| **PID gains (Kp, Ki, Kd)** | Tension loop tuning | From aria_pid_tuner or model-based tuning | Step response or plant model (inertia, torque constant) |
| **motor.velocity_limit** | Max motor rad/s | From motor RPM / gear ratio; motor shaft rad/s | motor_speed_rpm from CEM, GEAR_RATIO |
| **VOLTAGE_LIMIT** | Motor voltage limit | From motor specs; 10V typical for 24V supply | Motor datasheet |
| **v_mag_limit (safety)** | Overcurrent proxy | From motor current limit and driver gain | Motor + driver specs |

### 7c) Minimum viable sync for Phase 2-3

Constants needed for:
- **Motor PID to work correctly:** `SPOOL_R`, `GEAR_RATIO`, `T_BASELINE`, `motor.velocity_limit` (from CEM motor_speed_rpm)
- **Encoder position accurate:** `SPOOL_R`, `GEAR_RATIO` (encoder CPR is fixed by hardware)
- **Load cell thresholds physically meaningful:** `T_BASELINE`, `T_TAKE`, `T_FALL`, `T_GROUND` — from CEM `target_tension_N` and design requirements
- **Rope tension targets match physical design:** `T_BASELINE` = `inp.target_tension_N`; `T_TAKE` = fraction of `min_hold_force_kN` for hold confirmation

**Minimum set:**
1. `SPOOL_R` ← from CEM spool or context (clarify which radius)
2. `GEAR_RATIO` ← from CEM motor.gearbox_ratio
3. `T_BASELINE` ← from CEM inp.target_tension_N
4. `T_TAKE` ← from design (e.g. 200N for "take" confirmation)
5. `T_FALL` ← from design (e.g. 400N for fall detection; clutch handles arrest)
6. `SPD_RETRACT` ← from CEM inp.max_retract_speed_m_s
7. `SPD_FALL` ← from CEM clutch.engagement_v_m_s (or design requirement)

### 7d) What's missing from aria_cem.py before sync is complete?

1. **Spool radius for rope kinematics:** CEM uses `rope_spool_diameter_mm = 120` (hub). Context says `Rope spool dia 600mm`. Firmware `SPOOL_R = 0.30` suggests 600mm diameter. **Add `effective_rope_radius_m` or `rope_wrap_radius_m`** to `RopeSpoolGeom` — effective radius where rope wraps (hub + layers/2).
2. **Encoder-to-position conversion:** CEM does not output encoder CPR or position scaling. **Add** `encoder_cpr` and `position_scale_m_per_count` if encoder is fixed.
3. **Explicit tension thresholds:** CEM has `target_tension_N`, `min_hold_force_kN`. **Add** `tension_take_confirm_N`, `tension_fall_detect_N` to `ARIAInputs` or derived output for firmware sync.
4. **Fall detection speed:** `clutch.engagement_v_m_s` exists. **Add** `fall_detection_speed_m_s` to outputs for `SPD_FALL` sync.
5. **Export format:** CEM exports CSV via `_export_csv`. **Add** JSON or structured format for `aria_constants_sync.py` to consume.

---

## Summary

- **aria_constants_sync.py:** Functional, reads from internal dict, patches firmware. Does not use CEM or state_machine.
- **aria_pid_tuner.py:** No plant model; empirical ZN/CC from step response. No CEM parameters.
- **STM32:** Key geometry constants `SPOOL_R`, `GEAR_RATIO`; tension `T_*`; PID gains; safety thresholds. No generated headers.
- **ESP32:** `VOICE_CONF_MIN`, `CLIP_CONF_MIN`, `FALL_TENSION_DELTA` shared with STM32.
- **CEM:** `compute_motor`, `compute_brake_drum`, `compute_rope_spool`, `compute_centrifugal_clutch` produce geometry. **SPOOL_R mismatch** (CEM 120mm hub vs firmware 300mm radius). Sync via `aria_constants_sync.py` extension + CEM export.
- **Minimal sync:** SPOOL_R, GEAR_RATIO, T_BASELINE, T_TAKE, T_FALL, SPD_RETRACT, SPD_FALL. Resolve spool radius first.
