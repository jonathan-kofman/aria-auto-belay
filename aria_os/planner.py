"""Read goal + context, output operation plan as structured dict with build order (and plain-text for display)."""
from .context_loader import load_context, get_mechanical_constants
from typing import Any


def plan(goal: str, context: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Produce a structured plan. Returns dict with:
      - text: str (plain-English steps for display)
      - part_id: str (e.g. aria_housing, aria_cam_collar)
      - base_shape: dict (type, dimensions)
      - hollow: bool, wall_mm: float | None
      - features: list of dicts (type, face, dimensions, position)
      - build_order: list of step descriptions
      - material, tolerances, export_formats (optional)
    """
    if context is None:
        context = load_context()
    constants = get_mechanical_constants(context)
    goal_lower = goal.lower()

    # ---------- ARIA housing shell ----------
    if "housing" in goal_lower and ("shell" in goal_lower or "box" in goal_lower or "aria housing" in goal_lower):
        w = constants.get("housing_width", 700.0)
        h = constants.get("housing_height", 680.0)
        d = constants.get("housing_depth", 344.0)
        wall = constants.get("wall_thickness", 10.0)
        bore = constants.get("bearing_od", 47.2)
        cx = constants.get("spool_center_x", 350.0)
        cy = constants.get("spool_center_y", 330.0)
        ratchet_dia = constants.get("ratchet_pocket_dia", 213.0)
        ratchet_depth = constants.get("ratchet_pocket_depth", 21.0)
        slot_w = constants.get("rope_slot_width", 30.0)
        slot_l = constants.get("rope_slot_length", 80.0)
        return {
            "text": "\n".join([
                "ARIA housing shell plan:",
                f"1. Create solid outer box {w} x {h} x {d} mm.",
                f"2. Hollow interior with wall thickness {wall} mm (cut inner void).",
                f"3. Front face: bearing bore Ø{bore} mm at ({cx}, {cy}), depth 12 mm.",
                f"4. Back face: bearing bore Ø{bore} mm at ({cx}, {cy}), depth 12 mm.",
                f"5. Back face: ratchet pocket Ø{ratchet_dia} mm, depth {ratchet_depth} mm.",
                f"6. Top face: rope slot {slot_w} x {slot_l} mm, depth 15 mm.",
            ]),
            "part_id": "aria_housing",
            "base_shape": {"type": "box", "width": w, "height": h, "depth": d},
            "hollow": True,
            "wall_mm": wall,
            "features": [
                {"type": "bore", "face": ">Z", "diameter": bore, "depth": 12, "center_x": cx - w / 2, "center_y": cy - h / 2},
                {"type": "bore", "face": "<Z", "diameter": bore, "depth": 12, "center_x": cx - w / 2, "center_y": cy - h / 2},
                {"type": "pocket", "face": "<Z", "diameter": ratchet_dia, "depth": ratchet_depth, "center_x": cx - w / 2, "center_y": cy - h / 2},
                {"type": "slot", "face": ">Y", "width": slot_w, "length": slot_l, "depth": 15, "center_x": 0, "center_y": 0},
            ],
            "build_order": [
                "Create solid box (no annular profile).",
                "Cut interior void as separate boolean cut.",
                "Bearing bore front face.",
                "Bearing bore back face.",
                "Ratchet pocket back face.",
                "Rope slot top face.",
            ],
            "expected_bbox": (w, h, d),
            "material": "6061 Al",
            "export_formats": ["step", "stl"],
        }

    # ---------- ARIA rope spool ----------
    if "spool" in goal_lower:
        dia = constants.get("rope_spool_dia", 600.0)
        for k, v in constants.items():
            if "spool" in k and "dia" in k:
                dia = v
                break
        bore = constants.get("bearing_od", 47.2)
        return {
            "text": "\n".join([
                "ARIA rope spool plan:",
                f"1. Create cylindrical spool outer diameter {dia} mm.",
                "2. Apply 10 mm wall thickness (hollow).",
                f"3. Center bore matching bearing OD ({bore} mm).",
            ]),
            "part_id": "aria_spool",
            "base_shape": {"type": "cylinder", "diameter": dia, "height": 50.0},
            "hollow": True,
            "wall_mm": 10.0,
            "features": [{"type": "bore", "face": ">Z", "diameter": bore, "through": True}],
            "build_order": ["Create outer cylinder.", "Cut inner cylinder (hollow).", "Center bore."],
            "expected_bbox": (dia, dia, 50.0),
            "material": "6061 Al",
            "export_formats": ["step", "stl"],
        }

    # ---------- ARIA Cam Collar ----------
    if "cam collar" in goal_lower or "cam_collar" in goal_lower:
        shoulder_od = constants.get("bearing_shoulder_od", 55.0)
        return {
            "text": "\n".join([
                "ARIA Cam Collar plan:",
                f"1. Cylindrical part OD {shoulder_od} mm, length 40 mm.",
                "2. ID bore 25 mm.",
                "3. Outer helical ramp: 15° ramp, 5 mm rise over 90°.",
            ]),
            "part_id": "aria_cam_collar",
            "base_shape": {"type": "cylinder", "diameter": shoulder_od, "height": 40.0},
            "hollow": True,
            "wall_mm": None,
            "features": [
                {"type": "bore", "face": ">Z", "diameter": 25.0, "through": True},
                {"type": "ramp", "description": "15° helical ramp, 5mm rise over 90°"},
            ],
            "build_order": ["Create solid cylinder.", "Center bore 25 mm.", "Add helical ramp on outer surface (approximate if needed)."],
            "expected_bbox": (shoulder_od, shoulder_od, 40.0),
            "material": "6061 Al",
            "export_formats": ["step", "stl"],
        }

    # ---------- ARIA Rope Guide ----------
    if "rope guide" in goal_lower or "rope_guide" in goal_lower:
        slot_w = constants.get("rope_slot_width", 30.0)
        return {
            "text": "\n".join([
                "ARIA Rope Guide plan:",
                "1. Base plate 80 x 40 x 10 mm.",
                f"2. Centered slot {slot_w} mm wide (rope slot width from aria_mechanical).",
                "3. 4x M6 mounting holes at corners: 6.5 mm dia, 15 mm from edges.",
            ]),
            "part_id": "aria_rope_guide",
            "base_shape": {"type": "box", "width": 80.0, "height": 40.0, "depth": 10.0},
            "hollow": False,
            "wall_mm": None,
            "features": [
                {"type": "slot", "face": ">Z", "width": slot_w, "length": 40.0, "depth": 10.0, "center_x": 0, "center_y": 0},
                {"type": "holes", "face": ">Z", "diameter": 6.5, "positions": [(80/2 - 15, 40/2 - 15), (-(80/2 - 15), 40/2 - 15), (-(80/2 - 15), -(40/2 - 15)), (80/2 - 15, -(40/2 - 15))]},
            ],
            "build_order": ["Create solid base plate.", "Cut centered slot.", "Add 4x M6 holes at corners."],
            "expected_bbox": (80.0, 40.0, 10.0),
            "material": "6061 Al",
            "export_formats": ["step", "stl"],
        }

    # ---------- ARIA Motor Mount Plate ----------
    if "motor mount" in goal_lower or "motor_mount" in goal_lower:
        return {
            "text": "\n".join([
                "ARIA Motor Mount Plate plan:",
                "1. Plate 120 x 120 x 8 mm.",
                "2. 4x M5 motor bolt pattern: 98 mm bolt circle diameter.",
                "3. Center bore 22 mm (motor shaft clearance).",
                "4. 4x M6 wall mount holes at corners: 10 mm from edges (6.5 mm dia).",
            ]),
            "part_id": "aria_motor_mount",
            "base_shape": {"type": "box", "width": 120.0, "height": 120.0, "depth": 8.0},
            "hollow": False,
            "wall_mm": None,
            "features": [
                {"type": "bore", "face": ">Z", "diameter": 22.0, "through": True, "center_x": 0, "center_y": 0},
                {"type": "bolt_circle", "face": ">Z", "diameter": 6.5, "bolt_circle_diameter": 98.0, "count": 4},
                {"type": "holes", "face": ">Z", "diameter": 6.5, "positions": [(120/2 - 10, 120/2 - 10), (-(120/2 - 10), 120/2 - 10), (-(120/2 - 10), -(120/2 - 10)), (120/2 - 10, -(120/2 - 10))]},
            ],
            "build_order": ["Create solid plate.", "Center bore 22 mm.", "4x M5 holes on 98 mm BCD.", "4x M6 corner holes."],
            "expected_bbox": (120.0, 120.0, 8.0),
            "material": "6061 Al",
            "export_formats": ["step", "stl"],
        }

    # ---------- Generic / unknown part: break goal into structure ----------
    return _plan_generic(goal, constants)


def _plan_generic(goal: str, constants: dict[str, float]) -> dict[str, Any]:
    """Parse unknown goal into base_shape, hollow, features, build_order."""
    goal_lower = goal.lower()
    base_shape = {"type": "box", "width": 100.0, "height": 100.0, "depth": 100.0}
    hollow = False
    wall_mm = None
    features = []
    build_order = ["Create main solid from description.", "Apply cuts and bores as specified."]
    part_id = "aria_part"

    # Heuristic: try to infer dimensions from goal text (very simple)
    if "box" in goal_lower or "plate" in goal_lower:
        base_shape["type"] = "box"
    if "cylind" in goal_lower or "round" in goal_lower or "bore" in goal_lower:
        base_shape["type"] = "cylinder"
        base_shape["diameter"] = 50.0
        base_shape["height"] = 30.0

    return {
        "text": goal,
        "part_id": part_id,
        "base_shape": base_shape,
        "hollow": hollow,
        "wall_mm": wall_mm,
        "features": features,
        "build_order": build_order,
        "expected_bbox": None,
        "material": None,
        "export_formats": ["step", "stl"],
    }
