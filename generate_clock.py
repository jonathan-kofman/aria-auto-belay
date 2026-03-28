"""
generate_clock.py — Generate all skeleton clock parts headless (no browser, no prompts).

Usage:
    python generate_clock.py

Outputs every part as STEP + STL into outputs/cad/step/ and outputs/cad/stl/
Prints a summary table at the end showing pass/fail + BBOX for each part.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aria_os.cadquery_generator import write_cadquery_artifacts
from aria_os.spec_extractor import extract_spec

OUT_STEP = ROOT / "outputs" / "cad" / "step"
OUT_STL  = ROOT / "outputs" / "cad" / "stl"
OUT_STEP.mkdir(parents=True, exist_ok=True)
OUT_STL.mkdir(parents=True, exist_ok=True)

# ── Clock part list ────────────────────────────────────────────────────────────
# (description, part_id, params override)
PARTS = [
    # Gear train — wheels
    ("Barrel wheel 96t",        "clock_barrel_wheel",    {"module_mm":1.5,"n_teeth":96,"face_width_mm":9,"bore_mm":18,"hub_od_mm":36,"spoke_style":"petal","n_spokes":5}),
    ("Center wheel 80t",        "clock_center_wheel",    {"module_mm":1.0,"n_teeth":80,"face_width_mm":6,"bore_mm":10,"hub_od_mm":22,"spoke_style":"petal","n_spokes":5}),
    ("Third wheel 48t",         "clock_third_wheel",     {"module_mm":1.0,"n_teeth":48,"face_width_mm":6,"bore_mm":6, "hub_od_mm":16,"spoke_style":"petal","n_spokes":5}),
    ("Fourth wheel 64t",        "clock_fourth_wheel",    {"module_mm":1.0,"n_teeth":64,"face_width_mm":6,"bore_mm":8, "hub_od_mm":20,"spoke_style":"petal","n_spokes":5}),
    ("Escape wheel 15t",        "clock_escape_wheel",    {"module_mm":0.5,"n_teeth":15,"face_width_mm":4,"bore_mm":3, "hub_od_mm":8, "spoke_style":"minimal","n_spokes":5}),

    # Gear train — pinions (all 8-leaf)
    ("Center pinion p8",        "clock_center_pinion",   {"module_mm":0.5,"n_teeth":8,"face_width_mm":6,"bore_mm":10,"hub_od_mm":16,"spoke_style":"straight"}),
    ("Third pinion p8",         "clock_third_pinion",    {"module_mm":0.5,"n_teeth":8,"face_width_mm":6,"bore_mm":6, "hub_od_mm":12,"spoke_style":"straight"}),
    ("Fourth pinion p8",        "clock_fourth_pinion",   {"module_mm":0.5,"n_teeth":8,"face_width_mm":6,"bore_mm":8, "hub_od_mm":14,"spoke_style":"straight"}),
    ("Escape pinion p8",        "clock_escape_pinion",   {"module_mm":0.5,"n_teeth":8,"face_width_mm":4,"bore_mm":3, "hub_od_mm":8, "spoke_style":"straight"}),

    # Motion works (hour 12:1 reduction)
    ("Cannon pinion 10t",       "clock_cannon_pinion",   {"module_mm":0.5,"n_teeth":10,"face_width_mm":4,"bore_mm":10,"hub_od_mm":16,"spoke_style":"straight"}),
    ("Minute wheel 40t",        "clock_minute_wheel",    {"module_mm":0.5,"n_teeth":40,"face_width_mm":4,"bore_mm":4, "hub_od_mm":10,"spoke_style":"petal","n_spokes":5}),
    ("Minute wheel pinion 10t", "clock_minute_pinion",   {"module_mm":0.5,"n_teeth":10,"face_width_mm":4,"bore_mm":4, "hub_od_mm":10,"spoke_style":"straight"}),
    ("Hour wheel 30t",          "clock_hour_wheel",      {"module_mm":0.5,"n_teeth":30,"face_width_mm":4,"bore_mm":10,"hub_od_mm":18,"spoke_style":"petal","n_spokes":5}),

    # Arbors / shafts
    ("Barrel arbor",            "clock_barrel_arbor",    {"od_mm":18,"length_mm":60,"bore_mm":0}),
    ("Center arbor",            "clock_center_arbor",    {"od_mm":10,"length_mm":80,"bore_mm":0}),
    ("Third arbor",             "clock_third_arbor",     {"od_mm":6, "length_mm":70,"bore_mm":0}),
    ("Fourth arbor",            "clock_fourth_arbor",    {"od_mm":8, "length_mm":70,"bore_mm":0}),
    ("Escape arbor",            "clock_escape_arbor",    {"od_mm":3, "length_mm":50,"bore_mm":0}),

    # Barrel assembly
    ("Barrel drum",             "clock_barrel_drum",     {"od_mm":88,"bore_mm":60,"thickness_mm":11,"wall_mm":4}),
    ("Barrel cap",              "clock_barrel_cap",      {"od_mm":88,"thickness_mm":2,"bore_mm":18}),
    ("Click wheel 16t",         "clock_click_wheel",     {"module_mm":1.0,"n_teeth":16,"face_width_mm":4,"bore_mm":18,"hub_od_mm":28,"spoke_style":"straight"}),

    # Pendulum
    ("Pendulum rod",            "clock_pendulum_rod",    {"od_mm":3,"length_mm":248,"bore_mm":0}),
    ("Pendulum bob",            "clock_pendulum_bob",    {"od_mm":60,"thickness_mm":8,"bore_mm":3}),
    ("Rating nut",              "clock_rating_nut",      {"od_mm":8,"thickness_mm":4,"bore_mm":3}),

    # Dial & hands
    ("Dial ring",               "clock_dial_ring",       {"od_mm":160,"bore_mm":140,"thickness_mm":3}),
    ("Hour hand",               "clock_hour_hand",       {"length_mm":55,"width_mm":4,"thickness_mm":1.5,"bore_mm":5}),
    ("Minute hand",             "clock_minute_hand",     {"length_mm":70,"width_mm":3,"thickness_mm":1.2,"bore_mm":5}),
    ("Seconds hand",            "clock_seconds_hand",    {"length_mm":65,"width_mm":2,"thickness_mm":1.0,"bore_mm":3}),

    # Pillars (4x identical)
    ("Pillar x4",               "clock_pillar",          {"od_mm":12,"bore_mm":4,"height_mm":50}),
]

# ── Template map key resolver ──────────────────────────────────────────────────
from aria_os.cadquery_generator import _CQ_TEMPLATE_MAP

def resolve_template(part_id: str, params: dict) -> str:
    """Map clock part IDs to the right CadQuery template."""
    pid = part_id.lower()
    # Escape wheel → dedicated template (spike teeth, not involute)
    if "escape" in pid and "wheel" in pid:
        return "aria_escape_wheel"
    # Gear parts → aria_gear
    if any(k in pid for k in ("wheel","pinion","cannon")):
        return "aria_gear"
    # Shaft/arbor/rod → aria_shaft
    if any(k in pid for k in ("arbor","rod","shaft")):
        return "aria_shaft"
    # Drum/barrel body → aria_brake_drum (cylindrical shell)
    if "drum" in pid:
        return "aria_brake_drum"
    # Flat disk (cap, bob, nut, dial, cap) → aria_spacer
    if any(k in pid for k in ("cap","bob","nut","dial","ring")):
        return "aria_spacer"
    # Hands → aria_catch_pawl (thin elongated body)
    if "hand" in pid:
        return "aria_catch_pawl"
    # Pillar → aria_spacer
    if "pillar" in pid:
        return "aria_spacer"
    return "aria_spacer"


# ── Generate each part ─────────────────────────────────────────────────────────
results = []

for label, part_id, params in PARTS:
    template_key = resolve_template(part_id, params)
    plan = {"part_id": template_key, "params": params}

    step_path = OUT_STEP / f"{part_id}.step"
    stl_path  = OUT_STL  / f"{part_id}.stl"

    try:
        result = write_cadquery_artifacts(
            plan, label,
            str(step_path), str(stl_path),
            ROOT,
        )
        ok    = not result.get("error")
        bbox  = result.get("bbox", "?")
        err   = result.get("error", "")
    except Exception as e:
        ok, bbox, err = False, "?", str(e)

    status = "OK  " if ok else "FAIL"
    results.append((status, label, part_id, bbox, err))
    print(f"  [{status}] {label:30s}  bbox={bbox}")

# ── Summary ────────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r[0].strip() == "OK")
failed = len(results) - passed

print(f"\n{'='*60}")
print(f"Clock generation complete: {passed}/{len(results)} parts OK")
if failed:
    print(f"\nFailed parts:")
    for status, label, pid, bbox, err in results:
        if status.strip() != "OK":
            print(f"  {label}: {err[:80]}")
print(f"{'='*60}")
print(f"\nSTEP files: {OUT_STEP}")
print(f"STL  files: {OUT_STL}")
