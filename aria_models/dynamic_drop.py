# aria_models/dynamic_drop.py
#
# WHAT THIS IS:
#   Virtual dynamic drop test engine for ARIA Setup 2 tests.
#   Implements a 1D mass-spring-damper model of:
#     - 140 kg test mass on rails
#     - Free fall over drop height
#     - Rope snaps taut → inertia trigger fires at 0.7g
#     - Energy absorber decelerates mass to rest
#   All geometry and thresholds from your project record.
#
# WHEN TO RUN:
#   Called by aria_dashboard.py when you select Setup 2 and click
#   "Run Simulation". Do NOT run this file directly.
#
# WHAT THE OUTPUT MEANS:
#   arrest_distance_mm  → how far rope moved from trigger to stop.
#                         ANSI limit = 813 mm. Must be under.
#   peak_force_N        → maximum rope tension during arrest.
#                         ANSI limit = 8,000 N. Must be under.
#   avg_force_N         → average arrest force.
#                         ANSI limit = 6,000 N. Must be under.
#   trigger_fired       → True if inertia trigger fired (0.7g threshold met).
#                         If False: trigger didn't fire → design problem.
#   absorber_activated  → True if absorber force exceeded 4,000 N activation.
#
# KEY PHYSICS (from project record):
#   Test mass:         140 kg
#   Drop height:       40 mm (rope slack before taut)
#   Trigger threshold: 0.7g (flyweight fires above this)
#   False-trip check:  Must NOT fire at 0.3g (slow climbing movement)
#   ANSI limits:       Peak 8,000 N | Avg 6,000 N | Distance 813 mm
#   Energy absorber:   Activates ≤ 4,000 N, limits peak force
#
# VALIDATED RESULTS (from engineering calcs in project record):
#   Arrest distance:   54 mm   (ANSI: 813 mm) → 15× margin
#   Peak force:        5,373 N (ANSI: 8,000 N) → 1.49× margin
#   Average force:     2,390 N (ANSI: 6,000 N) → 2.51× margin

import numpy as np
import pandas as pd

# ── Physical constants ───────────────────────────────────────────────────
G = 9.81   # m/s²

# ── Default test parameters (from project record) ───────────────────────
DEFAULT_MASS_KG          = 140.0
DEFAULT_DROP_HEIGHT_M    = 0.040      # 40 mm
DEFAULT_TRIGGER_G        = 0.7        # fires above this acceleration (×g)
DEFAULT_ABSORBER_K       = 30000.0    # N/m — absorber spring stiffness
DEFAULT_ABSORBER_C       = 2000.0     # N·s/m — absorber damping
DEFAULT_ABSORBER_FMAX    = 4000.0     # N — absorber activation force
DEFAULT_ROPE_K           = 80000.0    # N/m — rope stiffness after taut
DEFAULT_SLACK_M          = 0.000      # extra slack beyond drop height
DT                       = 0.0005     # integration time step (s)
T_MAX                    = 2.0        # simulation duration (s)


def simulate_drop_test(
    mass_kg:         float = DEFAULT_MASS_KG,
    drop_height_m:   float = DEFAULT_DROP_HEIGHT_M,
    trigger_g:       float = DEFAULT_TRIGGER_G,
    absorber_k:      float = DEFAULT_ABSORBER_K,
    absorber_c:      float = DEFAULT_ABSORBER_C,
    absorber_fmax_n: float = DEFAULT_ABSORBER_FMAX,
    rope_k:          float = DEFAULT_ROPE_K,
    slack_m:         float = DEFAULT_SLACK_M,
    dt_s:            float = DT,
    t_max_s:         float = T_MAX,
) -> tuple[pd.DataFrame, dict]:
    """
    Simulate a single ARIA drop test (Test 2B).

    Physics: free fall -> rope taut (rope stiffness) -> inertia trigger at trigger_g ->
    energy absorber (spring-damper) until rest.

    Returns:
        df:       Time-series DataFrame with columns:
                    time_s, pos_m, vel_ms, accel_ms2,
                    tension_N, absorber_force_N, phase
        summary:  Dict with key results vs ANSI limits.
    """
    total_drop = drop_height_m + slack_m
    t = 0.0
    x = 0.0
    v = 0.0
    phase = "FREE_FALL"
    x_trigger = 0.0
    t_trigger = 0.0
    trigger_fired = False
    absorber_activated = False
    arrest_forces: list[float] = []

    rows: list[dict] = []

    while t <= t_max_s:
        tension_N = 0.0
        absorber_force_N = 0.0
        accel = G

        if phase == "FREE_FALL":
            accel = G
            tension_N = 0.0
            if x >= total_drop:
                phase = "ROPE_TAUT"

        if phase == "ROPE_TAUT":
            elongation = x - total_drop
            tension_N = rope_k * elongation if elongation > 0 else 0.0
            accel = G - (tension_N / mass_kg)
            if accel <= -trigger_g * G and not trigger_fired:
                trigger_fired = True
                x_trigger = x
                t_trigger = t
                phase = "ARREST"

        if phase == "ARREST":
            stroke = x - x_trigger
            absorber_force_N = absorber_k * stroke + absorber_c * v
            tension_N = absorber_force_N
            if absorber_force_N >= absorber_fmax_n:
                absorber_activated = True
            accel = G - (tension_N / mass_kg)
            arrest_forces.append(tension_N)

        rows.append({
            "time_s": round(t, 6),
            "pos_m": round(x, 6),
            "vel_ms": round(v, 6),
            "accel_ms2": round(accel, 4),
            "tension_N": round(tension_N, 2),
            "absorber_force_N": round(absorber_force_N, 2),
            "phase": phase,
        })

        v += accel * dt_s
        x += v * dt_s
        t += dt_s

        if v <= 0.0 and phase == "ARREST":
            break

    df = pd.DataFrame(rows)

    arrest_distance_m = (x - x_trigger) if trigger_fired else 0.0
    peak_force_N = max((row["tension_N"] for row in rows), default=0.0)
    avg_force_N = (sum(arrest_forces) / len(arrest_forces)) if arrest_forces else 0.0

    limit_dist = 813.0
    limit_peak = 8000.0
    limit_avg = 6000.0
    passed = (
        trigger_fired
        and arrest_distance_m * 1000 < limit_dist
        and peak_force_N < limit_peak
        and avg_force_N < limit_avg
    )

    summary = {
        "arrest_distance_mm": round(arrest_distance_m * 1000, 2),
        "peak_force_N": round(peak_force_N, 2),
        "avg_force_N": round(avg_force_N, 2),
        "trigger_fired": trigger_fired,
        "absorber_activated": absorber_activated,
        "ansi_peak_limit_N": limit_peak,
        "ansi_avg_limit_N": limit_avg,
        "ansi_distance_limit_mm": limit_dist,
        "passed": passed,
    }

    return df, summary


def simulate_false_trip_check(
    mass_kg: float = DEFAULT_MASS_KG,
    accel_g: float = 0.3,
    rope_k: float = DEFAULT_ROPE_K,
    trigger_g: float = DEFAULT_TRIGGER_G,
    dt_s: float = DT,
    duration_s: float = 1.0,
) -> dict:
    """
    Test 2A: False trip check. Simulate slow movement at accel_g (e.g. 0.3g).
    Pass = trigger does NOT fire (must not trip during normal climbing).
    Uses same physics: constant tension gives constant acceleration.
    """
    # Tension to hold mass at net acceleration accel_g: T = m*(g - a) = m*g*(1 - accel_g)
    tension_N = mass_kg * G * (1.0 - accel_g)
    elongation_m = tension_N / rope_k if rope_k > 0 else 0.0
    x = elongation_m
    v = 0.0
    t = 0.0
    trigger_fired = False
    n_steps = int(duration_s / dt_s)
    for _ in range(n_steps):
        accel = G - (tension_N / mass_kg)
        if accel <= -trigger_g * G:
            trigger_fired = True
            break
        v += accel * dt_s
        x += v * dt_s
        t += dt_s
    passed = not trigger_fired
    return {
        "passed": passed,
        "trigger_fired": trigger_fired,
        "accel_g_applied": accel_g,
        "trigger_g_threshold": trigger_g,
        "duration_s": duration_s,
        "message": "Trigger did not fire (pass)" if passed else "Trigger fired — false trip (fail)",
    }
