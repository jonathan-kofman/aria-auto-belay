# aria_models/design_suggestions.py
#
# Returns actionable design suggestions to help the ARIA design pass all tests.
# Used by the dashboard after running physics-based tests.

from __future__ import annotations


def get_static_suggestions(df) -> list[str]:
    """Suggestions for Setup 1 static load tests (pawl, housing, shaft)."""
    suggestions = []
    if df is None or df.empty:
        return suggestions
    if not df["passed"].all():
        failed = df[~df["passed"]]
        min_sf = failed["min_sf"].min()
        # Which component is limiting (lowest SF among the four)
        row = failed.loc[failed["min_sf"].idxmin()]
        if row["sf_contact"] == row["min_sf"] and row["min_sf"] < 2.0:
            suggestions.append("**Pawl contact:** Increase pawl tip contact area (tip width × engagement depth) or use higher yield material (e.g. A2 tool steel 58 HRC).")
        if row["sf_bending"] == row["min_sf"] and row["min_sf"] < 2.0:
            suggestions.append("**Pawl bending:** Increase pawl cross-section (body height or thickness) or moment arm, or use higher strength material.")
        if row["sf_housing"] == row["min_sf"] and row["min_sf"] < 2.0:
            suggestions.append("**Housing:** Increase wall thickness at pawl pivot boss or use higher yield material (e.g. 6061-T6).")
        if row["sf_shaft"] == row["min_sf"] and row["min_sf"] < 2.0:
            suggestions.append("**Shaft:** Increase shaft diameter or reduce bearing span, or use higher strength material (e.g. 4140 HT).")
        if not suggestions:
            suggestions.append("**General:** Ensure minimum safety factor ≥ 2.0 at all load steps (ANSI). Increase section sizes or upgrade materials.")
    return suggestions


def get_drop_suggestions(summary: dict) -> list[str]:
    """Suggestions for Setup 2 drop test (2B) based on pass/fail and limits."""
    suggestions = []
    if not summary:
        return suggestions
    passed = summary.get("passed", False)
    if passed:
        return suggestions
    limit_dist = summary.get("ansi_distance_limit_mm", 813)
    limit_peak = summary.get("ansi_peak_limit_N", 8000)
    limit_avg = summary.get("ansi_avg_limit_N", 6000)
    dist = summary.get("arrest_distance_mm", 0)
    peak = summary.get("peak_force_N", 0)
    avg = summary.get("avg_force_N", 0)
    trigger_fired = summary.get("trigger_fired", False)

    if not trigger_fired:
        suggestions.append("**Trigger did not fire:** Lower the inertia trigger threshold (e.g. from 0.7g to 0.6g), or increase drop height / rope stiffness so deceleration reaches threshold.")
    if dist >= limit_dist:
        suggestions.append("**Arrest distance too high:** Increase absorber stiffness (k) or damping (c) to stop the mass in a shorter stroke. Check that absorber is activating.")
    if peak >= limit_peak:
        suggestions.append("**Peak force too high:** Reduce absorber stiffness (k) or increase damping (c) to spread the load; or increase absorber stroke so peak is capped.")
    if avg >= limit_avg:
        suggestions.append("**Average force too high:** Increase energy absorber capacity (softer spring or more damping) to reduce mean arrest force.")
    return suggestions


def get_false_trip_suggestions(result: dict) -> list[str]:
    """Suggestions for Setup 2A false trip check (must NOT fire at 0.3g)."""
    suggestions = []
    if not result:
        return suggestions
    if result.get("passed", True):
        return suggestions
    suggestions.append("**False trip (trigger fired at slow movement):** Raise the trigger threshold (e.g. from 0.3g to 0.5g or 0.6g) so normal climbing does not trip the inertia mechanism. Ensure 0.7g drop test still fires.")
    return suggestions


def get_state_machine_suggestions(df, n_cycles: int) -> list[str]:
    """Suggestions for Setup 3 functional / state machine tests."""
    suggestions = []
    if df is None or df.empty:
        return suggestions
    states = df["state"].tolist()
    expected_cycle = ["IDLE", "CLIMBING", "TAKE", "LOWER", "IDLE"]
    # Check we see expected transitions
    if "IDLE" not in states or "CLIMBING" not in states:
        suggestions.append("**State machine:** Climber not detected or tension too low — ensure tension > 15 N and cv_climber_detected for IDLE → CLIMBING.")
    if "TAKE" not in states and "CLIMBING" in states:
        suggestions.append("**TAKE confirmation:** Voice 'take' plus load > 200 N within 500 ms required. Check load cell calibration and timing.")
    if "LOWER" not in states and "TAKE" in states:
        suggestions.append("**LOWER:** Voice 'lower' from TAKE state. Check command recognition.")
    return suggestions
