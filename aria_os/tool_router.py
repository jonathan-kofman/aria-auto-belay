"""
aria_os/tool_router.py
Decides which CAD tool handles each part based on geometry type.
"""
from typing import Any

FUSION_KEYWORDS = [
    "lattice", "volumetric", "gyroid", "octet", "infill", "cellular",
    "honeycomb", "gradient density", "assembly", "cam toolpath", "nesting",
    "additive setup", "lightweight fill", "energy absorber",
]

GRASSHOPPER_KEYWORDS = [
    "helical", "helix", "sweep", "loft", "ruled surface", "freeform",
    "spline", "cam ramp", "spiral", "twisted", "variable pitch",
    "surface", "nurbs",
]

BLENDER_KEYWORDS = [
    "mesh repair", "cleanup", "decimate", "remesh", "organic",
    "sculpt", "soft", "irregular",
]

FUSION_PART_IDS = {
    "aria_energy_absorber", "aria_lattice_housing", "aria_assembly",
}

GRASSHOPPER_PART_IDS = {
    "aria_cam_collar",
    "aria_spool",
    "aria_housing",
    "aria_ratchet_ring",
    "aria_brake_drum",
    "aria_rope_guide",
}

# LRE / nozzle parts always route to CadQuery headless (no Grasshopper)
CADQUERY_KEYWORDS = [
    "nozzle", "rocket", "lre", "liquid rocket", "turbopump", "injector",
]


def select_cad_tool(goal: str, plan: dict[str, Any]) -> str:
    """
    Return one of: 'cadquery', 'fusion', 'grasshopper', 'blender'
    """
    goal_lower = (goal or "").lower()
    part_id = str(plan.get("part_id", ""))
    features = plan.get("features", []) or []

    # LRE / nozzle always → cadquery headless (overrides GRASSHOPPER_PART_IDS)
    if any(kw in goal_lower for kw in CADQUERY_KEYWORDS):
        return "cadquery"

    if part_id in GRASSHOPPER_PART_IDS:
        return "grasshopper"
    if part_id in FUSION_PART_IDS:
        return "fusion"

    for f in features:
        if not isinstance(f, dict):
            continue
        if f.get("type") == "ramp" or "helical" in str(f.get("description", "")).lower():
            return "grasshopper"
        if f.get("type") == "lattice":
            return "fusion"

    if any(kw in goal_lower for kw in GRASSHOPPER_KEYWORDS):
        return "grasshopper"
    if any(kw in goal_lower for kw in FUSION_KEYWORDS):
        return "fusion"
    if any(kw in goal_lower for kw in BLENDER_KEYWORDS):
        return "blender"

    return "cadquery"


def get_output_formats(tool: str) -> list[str]:
    """Return expected output file extensions for each tool."""
    return {
        "cadquery": ["step", "stl"],
        "fusion": ["stl", "step"],
        "grasshopper": ["step", "stl"],
        "blender": ["stl"],
    }.get(tool, ["stl"])
