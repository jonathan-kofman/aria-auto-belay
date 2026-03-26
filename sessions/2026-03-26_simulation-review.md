## Session 2026-03-26T04:01
**Status:** Complete (findings require action)
**Goal:** Full review of ARIA state machine, PID controls, physics model, and simulator scenarios

---

## 1. State Machine Completeness

### Files reviewed
- `aria_models/state_machine.py` (lightweight/stripped version)
- `tools/aria_simulator.py` (full simulator with `ARIAStateMachine`)

### 1a. State inventory

| State | `state_machine.py` | `aria_simulator.py` | Notes |
|---|---|---|---|
| IDLE | Yes | Yes | |
| CLIMBING | Yes | Yes | |
| CLIPPING | Yes | Yes | |
| TAKE | Yes | Yes | |
| REST | Yes | Yes | |
| LOWER | Yes | Yes | |
| WATCH_ME | Yes | Yes | |
| UP | Yes | Yes | |
| ESTOP | Yes | **No** | Missing from simulator |
| FALL_ARREST | **No** | **No** | Neither file has a dedicated state |
| LOCKED | **No** | **No** | Neither file has a dedicated state |
| ERROR | **No** | **No** | Neither file has a dedicated state |

### 1b. Critical findings

**FINDING-SM-1 (HIGH): No ESTOP state in simulator.**
`state_machine.py` has ESTOP as a state, but `aria_simulator.py` does not define it in its `State` enum. There is no e-stop button handling in the simulator at all. If the physical e-stop fires, the simulator has no path to model it. The ESTOP state in `state_machine.py` is also a dead state with no exit -- once entered, the system can never leave ESTOP without a power cycle (no reset transition). This may be intentional for safety, but it should be documented.

**FINDING-SM-2 (HIGH): No dedicated FALL_ARREST state.**
Fall arrest is handled as a safety override in the simulator's `tick()` method (line 205-215) that zeroes the motor and logs, but does NOT transition to any state. The system remains in whatever state it was in (e.g., CLIMBING) while the clutch is engaging. This means:
- After the fall condition clears (speed drops, tension drops), the machine resumes its pre-fall state as if nothing happened. There is no post-fall hold or inspection state.
- The `state_machine.py` version has no fall detection at all -- it relies entirely on the caller.

**FINDING-SM-3 (MEDIUM): CLIPPING state has no timeout in state_machine.py.**
`state_machine.py` line 96 says "handled by caller" for the CLIPPING->CLIMBING timeout. If the caller forgets, the system stays in CLIPPING (paying out rope fast) forever. The simulator handles this correctly with a duration check.

**FINDING-SM-4 (MEDIUM): TAKE two-factor confirmation diverges between implementations.**
- `state_machine.py`: Transitions to TAKE only after BOTH voice + 200N load within 0.5s window. The voice/load check happens while still in CLIMBING state.
- `aria_simulator.py`: Transitions to TAKE immediately on voice command, then checks load cell confirmation inside the TAKE state handler. If the load cell does not confirm within 500ms, it falls back to CLIMBING.
- The simulator approach is riskier: the system briefly enters TAKE (motor retract) before confirmation, potentially surprising the climber.

**FINDING-SM-5 (MEDIUM): Simultaneous input handling.**
Both implementations process voice commands in priority order (checked sequentially). If two voice commands arrive in the same tick (e.g., "take" and "lower" simultaneously), whichever is checked first wins. This is acceptable for voice input (only one command per utterance), but the `state_machine.py` version processes the "take" confirmation window globally (lines 48-73) before any state-specific logic, which could interact with other voice commands in unexpected ways.

**FINDING-SM-6 (LOW): Recursive call in state_machine.py CLIPPING handler.**
Line 100-101: If the user says "take" while in CLIPPING, the state is set to CLIMBING and then `self.step(inp)` is called recursively. This works but could stack overflow if somehow called in a loop, and it bypasses the take confirmation window (the recursive call will process the take voice command in CLIMBING context).

**FINDING-SM-7 (LOW): No CLIMBING->IDLE transition in state_machine.py.**
If the climber steps off the wall (tension drops below 15N), `state_machine.py` stays in CLIMBING forever. The simulator correctly transitions back to IDLE when `load_cell_n < TENSION_GROUND_N and not cv_climber_detected`.

### 1c. Transition map (simulator)

```
IDLE -----(climber detected + tension > 15N)-----> CLIMBING
CLIMBING --(cv_clip_confidence >= 0.75)----------> CLIPPING
CLIMBING --(voice "take" >= 0.85)----------------> TAKE
CLIMBING --(voice "rest" >= 0.85)----------------> REST
CLIMBING --(voice "lower" >= 0.85)---------------> LOWER
CLIMBING --(voice "watch me" >= 0.85)------------> WATCH_ME
CLIMBING --(voice "up" >= 0.85)------------------> UP
CLIMBING --(tension < 15N + no climber)----------> IDLE
CLIPPING --(clip duration elapsed)---------------> CLIMBING
TAKE ------(voice "climbing")--------------------> CLIMBING
TAKE ------(rope_speed > 0.1 + tension < 200N)--> CLIMBING
TAKE ------(10 min timeout)---------------------> CLIMBING
TAKE ------(confirmation timeout)---------------> CLIMBING
REST ------(voice "climbing")--------------------> CLIMBING
REST ------(rope_speed > 0.1)-------------------> CLIMBING
REST ------(10 min timeout)---------------------> CLIMBING
LOWER -----(tension < 15N)-----------------------> IDLE
LOWER -----(tension > 400N)---------------------> CLIMBING  [safety gate]
WATCH_ME --(voice "take")-----------------------> TAKE
WATCH_ME --(voice "lower")---------------------> LOWER
WATCH_ME --(voice "climbing")-------------------> CLIMBING
WATCH_ME --(3 min timeout)---------------------> CLIMBING
UP ---------(voice "climbing")-------------------> CLIMBING
UP ---------(voice "take")-----------------------> TAKE
```

**Dead states:** ESTOP (in `state_machine.py` only) -- no exit transition. This is intentional.

**Unreachable states:** None (all states are reachable from CLIMBING).

---

## 2. PID Control Analysis

### 2a. Gain set separation

| Parameter | Simulator (`aria_simulator.py`) | Firmware (`aria_constants_sync.py`) |
|---|---|---|
| Kp | 2.5 | 0.022 |
| Ki | 0.8 | 0.413 |
| Kd | 0.1 | 0.0005 |
| Output range | 0 to 100 (normalized %) | 0 to 10V |
| Context | Simulation only | Hardware-validated via `aria_pid_tuner` |

The two gain sets are properly separated:
- Simulator gains in `tools/aria_simulator.py` lines 43-45
- Firmware gains in `tools/aria_constants_sync.py` lines 57-59, marked `NEVER_PATCH`

**FINDING-PID-1 (MEDIUM): Simulator PID output range mismatch.**
The simulator creates the PID controller with `output_min=0, output_max=100` (line 161-162), but the PID formula can produce negative values (when tension exceeds setpoint). Clamping to 0 minimum means the motor can never actively brake -- it can only reduce payout effort to zero. This is physically correct for a payout-only motor, but the `_motor_direction` variable is set independently. The PID output magnitude drives `_motor_output` and the sign is discarded.

**FINDING-PID-2 (MEDIUM): No anti-windup in simulator PID.**
The PID controller (lines 95-125) has output clamping but no integral anti-windup. The integral term accumulates without bound during sustained error conditions (e.g., while in TAKE state at 100% hold, the PID targeting 40N with actual 680N will wind the integral deeply negative). When returning to CLIMBING, the negative integral bias will cause under-compensation until it unwinds. The `reset()` method exists but is only called in `_state_idle()`.

**FINDING-PID-3 (LOW): Wall-clock time dependency.**
The simulator PID uses `time.time()` for dt calculation (line 108). When running scenarios with compressed `time.sleep()`, the dt values become artificially small, which inflates the derivative term and shrinks the integral contribution. This makes scenario outputs unreliable for PID behavior analysis.

### 2b. Firmware gain validation

From `aria_pid_tuner.py`:
- Max error at fall detection: `T_FALL - T_BASELINE = 400 - 40 = 360N`
- Max voltage: `Kp * max_error = 0.022 * 360 = 7.92V` (under 10V limit -- PASS)
- The tuner applies 0.6x safety scaling (ZN) or 0.65x (Cohen-Coon) to calculated gains
- `VOLTAGE_LIMIT = 10.0V` is validated against CEM motor model

### 2c. Stability assessment (firmware gains)

With Kp=0.022, Ki=0.413, Kd=0.0005:
- The Ki/Kp ratio = 18.8, which is a very high integral-to-proportional ratio. This suggests the tuner found a system with significant dead time and slow proportional response, requiring heavy integral action.
- Kd is extremely small (0.0005), providing almost no derivative damping. This is appropriate if the load cell signal is noisy (derivative amplifies noise).
- **Overshoot risk:** The high Ki will cause overshoot on step changes. The 0.6x safety scaling mitigates this. Actual behavior depends on plant dynamics measured during tuning.
- **Recommendation:** Add anti-windup (integral clamping) to the firmware PID, especially since the integral dominates. Without it, transitions between states (different setpoints) will cause windup-induced oscillation.

---

## 3. Physics Model Review

### 3a. Static test model (`aria_models/static_tests.py`)

The model tests 4 failure modes at each load step:
1. **Pawl contact stress** -- flat-on-flat Hertzian approximation, 2-pawl load sharing
2. **Pawl bending stress** -- cantilever beam at root cross-section
3. **Housing wall bearing stress** -- bearing stress at pawl pivot boss
4. **Shaft bending stress** -- simply supported beam, center load

All geometry values match `context/aria_mechanical.md` exactly:
- Pawl: 6mm tip width, 9mm thick, 45mm arm, 22mm body height, 3mm engagement
- Ratchet: 100mm pitch radius, 24 teeth, 20mm face width
- Housing: 10mm wall, 700x680x344mm
- Shaft: 20mm diameter, 344mm span

### 3b. Cross-check against ANSI Z359.14 (`context/aria_test_standards.md`)

| Parameter | Test standard | Static tests code | Match? |
|---|---|---|---|
| Static proof load | 16,000 N | `ansi_static_n=16000.0` | Yes |
| Min safety factor | 2.0 | `min_sf >= 2.0` | Yes |
| Max arrest force | 8,000 N | Not tested | -- |
| Max arrest distance | 813 mm | Not tested | -- |

**FINDING-PHYS-1 (MEDIUM): No dynamic drop test model.**
The test standards define drop test parameters (140kg mass, 80kN/m rope stiffness, 30kN/m absorber spring, 2000 Ns/m damping), but there is no dynamic simulation anywhere in the codebase. `static_tests.py` only does static load checks. There is no energy conservation verification because there is no time-domain fall arrest simulation.

**FINDING-PHYS-2 (LOW): Pawl contact stress model is simplified.**
The "Hertzian-style" contact stress is actually a simple bearing stress (F/A). True Hertzian contact for cylinder-on-flat or flat-on-flat with edge loading would give higher stress values. The current model is non-conservative for the contact check, though the 2.0x safety factor margin likely covers this.

**FINDING-PHYS-3 (LOW): Housing wall stress ignores stress concentrations.**
The bearing stress calculation at the pivot boss (line 99-110) uses gross area only. Stress concentration factors for holes/bosses in thin plates (typically Kt = 2.0-3.0) are not applied. At ANSI proof load (16kN), this could matter.

### 3c. Energy conservation

No dynamic model exists to verify energy conservation. The drop test parameters in `aria_test_standards.md` define:
- Potential energy: `m * g * h = 140 * 9.81 * 0.040 = 54.9 J` (initial drop)
- Absorber: spring k=30kN/m, damping c=2000 Ns/m, max force 4kN
- Rope: stiffness 80kN/m

A time-stepping ODE solver should be implemented to verify that:
1. Peak arrest force stays below 8kN (ANSI limit)
2. Arrest distance stays below 813mm
3. Total energy is conserved (PE = KE + spring PE + damping dissipation)

---

## 4. Simulator Scenario Analysis

### 4a. Normal Climb Scenario

**Result: FAILED -- ended in CLIPPING state instead of IDLE.**

Root cause: The scenario timing is designed for real-time execution, but the first clip gesture (at step 3) does not complete before the second clip gesture arrives (at step 5). Due to the compressed time.sleep, the following sequence occurs:

1. First clip at bolt 1 (`cv_clip_confidence=0.9`) -- transitions to CLIPPING
2. Before the 2.17s clip duration elapses, `cv_clip_confidence` is set to 0.0 and the scenario continues
3. The CLIPPING state eventually times out and returns to CLIMBING
4. Second clip at bolt 2 (`cv_clip_confidence=0.88`) -- transitions to CLIPPING again
5. "take" voice command arrives while still in CLIPPING. The simulator's CLIPPING handler does NOT process voice commands (unlike `state_machine.py` which recursively handles "take" in CLIPPING). The voice is cleared at end of tick.
6. Load cell spikes to 680N but the system is still in CLIPPING, so the take two-factor check never runs
7. "lower" voice command arrives while in CLIPPING -- also ignored
8. Tension drops to 5N -- CLIPPING handler only checks elapsed time, not tension

**The system never reached TAKE, never reached LOWER, and never reached IDLE.** The climber is on the ground with 5N tension and the system is still paying out rope at 80% motor.

**FINDING-SIM-1 (CRITICAL): Simulator CLIPPING state ignores all voice commands.**
The `_state_clipping()` handler (lines 314-333) only checks elapsed time. Unlike `state_machine.py` which handles "take" during CLIPPING (line 98-101), the simulator has no voice exit from CLIPPING. This is a safety concern: if the climber falls while the system is pre-feeding clip slack, there is no way to command TAKE or LOWER.

**FINDING-SIM-2 (MEDIUM): Scenario timing assumes real-time execution.**
The scenario `time.sleep()` values (1.0s, 2.0s, etc.) assume the tick loop runs at wall-clock time. The 2.17s clip duration (`CLIP_SLACK_M / ROPE_SPEED_CLIMB_MS = 0.65 / 0.3`) means the clip phase cannot complete in compressed time without adjusting the sleep values.

### 4b. Fall Scenario

**Result: PARTIAL PASS -- fall detected correctly, but final state is LOWER instead of IDLE.**

Sequence:
1. Climber climbing at 6m -- transitions to CLIMBING (correct)
2. Fall: 900N + 3.5 m/s -- fall safety override fires, motor zeroed, "FALL DETECTED" logged (correct)
3. Deceleration: 450N + 1.8 m/s -- below thresholds, normal state logic resumes in CLIMBING (correct, but no post-fall hold)
4. Hanging: 680N, 0 m/s -- PID running in CLIMBING state (correct)
5. "lower" voice command -- transitions to LOWER (correct)
6. Tension drops to 5N -- LOWER should transition to IDLE (tension < 15N check at line 418), but the final state shows LOWER

The LOWER->IDLE transition likely did not fire because the tick loop processed the final sensor update and the state check happened in the same cycle. With compressed timing, the tick may not have run between the last sensor injection and the status print.

**FINDING-SIM-3 (MEDIUM): No post-fall recovery state.**
After fall detection clears, the system silently resumes CLIMBING. A real system should hold position and require explicit acknowledgment before resuming. The climber could be injured and unable to give voice commands.

---

## 5. Summary of Findings

### Critical
| ID | Finding |
|---|---|
| SIM-1 | Simulator CLIPPING state ignores all voice commands (safety gap) |

### High
| ID | Finding |
|---|---|
| SM-1 | No ESTOP state in simulator; ESTOP has no exit in state_machine.py |
| SM-2 | No dedicated FALL_ARREST state; fall handling is a transient override |

### Medium
| ID | Finding |
|---|---|
| SM-3 | CLIPPING timeout delegated to caller in state_machine.py |
| SM-4 | TAKE two-factor confirmation logic diverges between implementations |
| SM-7 | No CLIMBING->IDLE transition in state_machine.py |
| PID-1 | Simulator PID clamped to non-negative output only |
| PID-2 | No anti-windup in simulator or firmware PID |
| PHYS-1 | No dynamic drop test simulation (energy conservation unverifiable) |
| SIM-2 | Scenario timing assumes real-time execution |
| SIM-3 | No post-fall recovery state or acknowledgment requirement |

### Low
| ID | Finding |
|---|---|
| SM-5 | Simultaneous input priority is implicit |
| SM-6 | Recursive step() call in state_machine.py CLIPPING handler |
| PID-3 | Wall-clock time dependency in simulator PID |
| PHYS-2 | Pawl contact stress model is non-conservative |
| PHYS-3 | Housing stress ignores stress concentration factors |

---

## 6. Recommendations

1. **Add FALL_ARREST and ESTOP states to the simulator** with explicit entry/exit conditions
2. **Add voice command handling to simulator CLIPPING state** (at minimum: "take" and emergency transitions)
3. **Implement integral anti-windup** in both simulator and firmware PID (clamp integral term when output is saturated)
4. **Build a dynamic drop test ODE solver** using the parameters in `aria_test_standards.md` to verify ANSI peak force and arrest distance compliance
5. **Add PID reset on state transitions** (not just IDLE entry) to prevent integral windup carryover
6. **Reconcile the two state machine implementations** -- the divergences in TAKE confirmation and CLIPPING handling will cause "works in model, fails on hardware" bugs
7. **Add a post-fall hold state** requiring explicit "climbing" or "lower" voice command before resuming motor control
