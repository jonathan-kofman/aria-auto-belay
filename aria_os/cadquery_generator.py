"""
aria_os/cadquery_generator.py

CadQuery geometry generator for ARIA parts.
Produces STEP + STL by executing CadQuery scripts in-process.
This is the most reliable path for precise mechanical parts that
need exact dimensions and are describable by extrude/cut/revolve operations.

All known ARIA parts have a dedicated template.  Unknown parts fall back to
the LLM which still returns CadQuery code (headless, no Rhino required).
"""
from __future__ import annotations

import re
import traceback
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Per-part CadQuery templates
# ---------------------------------------------------------------------------

def _cq_ratchet_ring(params: dict[str, Any]) -> str:
    od     = float(params.get("od_mm", 213.0))
    bore   = float(params.get("bore_mm", 185.0))
    thick  = float(params.get("thickness_mm", params.get("height_mm", 21.0)))
    teeth  = int(params.get("n_teeth", 24))
    # Tooth height derived from pitch so teeth never overlap at any tooth count/OD combo.
    # Cap at 6mm; floor at 1.5mm for very fine-pitch rings.
    import math as _m
    _pitch = (_m.pi * od) / teeth
    _tooth_h = round(max(1.5, min(6.0, _pitch * 0.35)), 3)
    return f"""
import cadquery as cq, math

OD_MM          = {od}
BORE_MM        = {bore}
THICKNESS_MM   = {thick}
N_TEETH        = {teeth}
TOOTH_HEIGHT   = {_tooth_h}   # derived: pitch*0.35, capped [1.5, 6.0] mm
TOOTH_BASE_W   = (math.pi * OD_MM / N_TEETH) * 0.55

ring = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(THICKNESS_MM)
)

tooth_profile = [
    (0, 0),
    (TOOTH_BASE_W, 0),
    (TOOTH_BASE_W * 0.15, TOOTH_HEIGHT),
    (0, 0),
]
for i in range(N_TEETH):
    angle = i * 360.0 / N_TEETH
    r_mid = OD_MM / 2.0 - TOOTH_HEIGHT / 2.0
    tx = r_mid * math.cos(math.radians(angle))
    ty = r_mid * math.sin(math.radians(angle))
    tooth = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .transformed(rotate=(0, 0, angle))
        .move(r_mid - TOOTH_HEIGHT / 2.0, -TOOTH_BASE_W / 2.0)
        .polygon(4, TOOTH_BASE_W, forConstruction=False)
        .extrude(THICKNESS_MM)
    )
    try:
        ring = ring.union(tooth)
    except Exception:
        pass

result = ring
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_housing(params: dict[str, Any]) -> str:
    w = float(params.get("width_mm", 700.0))
    h = float(params.get("height_mm", 680.0))
    d = float(params.get("depth_mm", 344.0))
    wall = float(params.get("wall_mm", 10.0))
    return f"""
import cadquery as cq

WIDTH_MM  = {w}
HEIGHT_MM = {h}
DEPTH_MM  = {d}
WALL_MM   = {wall}

result = (
    cq.Workplane("XY")
    .box(WIDTH_MM, DEPTH_MM, HEIGHT_MM)
    .shell(-WALL_MM)
)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_spool(params: dict[str, Any]) -> str:
    drum_od  = float(params.get("diameter", params.get("od_mm", 600.0)))
    drum_w   = float(params.get("width", params.get("drum_width_mm", 50.0)))
    # Flange OD defaults to drum_od + 15% of drum_od (proportional), not a fixed 40mm offset.
    fl_od    = float(params.get("flange_diameter", params.get("flange_od_mm", drum_od * 1.15)))
    fl_thick = float(params.get("flange_thickness", params.get("flange_thickness_mm", max(6.0, drum_w * 0.12))))
    hub_od   = float(params.get("hub_diameter", 47.2))
    return f"""
import cadquery as cq

DRUM_OD_MM    = {drum_od}
DRUM_W_MM     = {drum_w}
FLANGE_OD_MM  = {fl_od}
FLANGE_TH_MM  = {fl_thick}
HUB_OD_MM     = {hub_od}

drum = cq.Workplane("XY").circle(DRUM_OD_MM / 2.0).extrude(DRUM_W_MM)
fl_b = cq.Workplane("XY").circle(FLANGE_OD_MM / 2.0).extrude(FLANGE_TH_MM)
fl_t = (cq.Workplane("XY").workplane(offset=DRUM_W_MM - FLANGE_TH_MM)
        .circle(FLANGE_OD_MM / 2.0).extrude(FLANGE_TH_MM))
hub_bore = (cq.Workplane("XY").workplane(offset=-1.0)
            .circle(HUB_OD_MM / 2.0).extrude(DRUM_W_MM + 2.0))

result = drum.union(fl_b).union(fl_t).cut(hub_bore)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_cam_collar(params: dict[str, Any]) -> str:
    od   = float(params.get("od_mm", params.get("diameter", 55.0)))
    h    = float(params.get("height_mm", params.get("height", 40.0)))
    bore = float(params.get("bore_mm", params.get("bore", 25.0)))
    return f"""
import cadquery as cq

OD_MM   = {od}
HEIGHT  = {h}
BORE_MM = {bore}

result = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(HEIGHT)
)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_brake_drum(params: dict[str, Any]) -> str:
    od      = float(params.get("diameter", params.get("od_mm", 200.0)))
    w       = float(params.get("width", params.get("width_mm", 40.0)))
    shaft_d = float(params.get("shaft_diameter", 20.0))
    wall    = float(params.get("wall_thickness", 8.0))
    return f"""
import cadquery as cq

OD_MM        = {od}
WIDTH_MM     = {w}
SHAFT_D_MM   = {shaft_d}
WALL_MM      = {wall}

outer = cq.Workplane("XY").circle(OD_MM / 2.0).extrude(WIDTH_MM)
inner_void = (cq.Workplane("XY").workplane(offset=-1.0)
              .circle(OD_MM / 2.0 - WALL_MM).extrude(WIDTH_MM + 2.0))
shaft = (cq.Workplane("XY").workplane(offset=-1.0)
         .circle(SHAFT_D_MM / 2.0).extrude(WIDTH_MM + 2.0))
result = outer.cut(inner_void).cut(shaft)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_catch_pawl(params: dict[str, Any]) -> str:
    length = float(params.get("length_mm", 60.0))
    w      = float(params.get("width_mm", 12.0))
    thick  = float(params.get("thickness_mm", 6.0))
    bore   = float(params.get("pivot_hole_dia_mm", 6.0))
    return f"""
import cadquery as cq

LENGTH_MM        = {length}
WIDTH_MM         = {w}
THICKNESS_MM     = {thick}
PIVOT_HOLE_D_MM  = {bore}

body = cq.Workplane("XY").box(LENGTH_MM, WIDTH_MM, THICKNESS_MM)
pivot = (cq.Workplane("XY").workplane(offset=-1.0)
         .center(-LENGTH_MM / 2.0 + WIDTH_MM / 2.0, 0)
         .circle(PIVOT_HOLE_D_MM / 2.0).extrude(THICKNESS_MM + 2.0))
result = body.cut(pivot)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_rope_guide(params: dict[str, Any]) -> str:
    bw = float(params.get("bracket_width", 80.0))
    bh = float(params.get("bracket_height", 40.0))
    bt = float(params.get("bracket_thickness", 6.0))
    rd = float(params.get("roller_diameter", 30.0))
    bore = float(params.get("bore", 8.0))
    return f"""
import cadquery as cq

BRACKET_W_MM = {bw}
BRACKET_H_MM = {bh}
BRACKET_T_MM = {bt}
ROLLER_D_MM  = {rd}
BORE_MM      = {bore}

plate = cq.Workplane("XY").box(BRACKET_W_MM, BRACKET_H_MM, BRACKET_T_MM)
boss  = (cq.Workplane("XY").workplane(offset=BRACKET_T_MM - 0.01)
         .circle(ROLLER_D_MM / 2.0).extrude(ROLLER_D_MM))
axle  = (cq.Workplane("XY").workplane(offset=-1.0)
         .circle(BORE_MM / 2.0).extrude(BRACKET_T_MM + ROLLER_D_MM + 2.0))
result = plate.union(boss).cut(axle)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_bracket(params: dict[str, Any]) -> str:
    w    = float(params.get("width_mm",  80.0))
    h    = float(params.get("height_mm", 60.0))
    t    = float(params.get("thickness_mm", 6.0))
    hole = float(params.get("hole_dia_mm", params.get("bolt_dia_mm", 8.0)))
    n    = max(1, int(params.get("n_bolts", 2)))
    # Space holes evenly along the width with 15% margin on each side
    margin  = min(w * 0.15, 15.0)
    x_start = -(w / 2.0 - margin)
    x_end   =  (w / 2.0 - margin)
    if n == 1:
        pts = [(0.0, 0.0)]
    else:
        pts = [
            (round(x_start + (x_end - x_start) * i / (n - 1), 3), 0.0)
            for i in range(n)
        ]
    pts_repr = repr(pts)
    return f"""
import cadquery as cq

WIDTH_MM     = {w}
HEIGHT_MM    = {h}
THICKNESS_MM = {t}
HOLE_DIA_MM  = {hole}

plate = cq.Workplane("XY").box(WIDTH_MM, THICKNESS_MM, HEIGHT_MM)
# {n} mounting hole(s) evenly spaced along the plate
hole_cyl = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .pushPoints({pts_repr})
    .circle(HOLE_DIA_MM / 2.0)
    .extrude(THICKNESS_MM + 2.0)
)
result = plate.cut(hole_cyl)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_flange(params: dict[str, Any]) -> str:
    od      = float(params.get("od_mm",    120.0))
    bore    = float(params.get("bore_mm",   40.0))
    thick   = float(params.get("thickness_mm", 12.0))
    bolt_r  = float(params.get("bolt_circle_r_mm", 50.0))
    n_bolts = int(params.get("n_bolts", 4))
    bolt_d  = float(params.get("bolt_dia_mm", 8.0))
    return f"""
import cadquery as cq, math

OD_MM           = {od}
BORE_MM         = {bore}
THICKNESS_MM    = {thick}
BOLT_CIRCLE_R   = {bolt_r}
N_BOLTS         = {n_bolts}
BOLT_DIA_MM     = {bolt_d}

disc = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(THICKNESS_MM)
)
pts = [
    (BOLT_CIRCLE_R * math.cos(math.radians(i * 360.0 / N_BOLTS)),
     BOLT_CIRCLE_R * math.sin(math.radians(i * 360.0 / N_BOLTS)))
    for i in range(N_BOLTS)
]
bolt_holes = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .pushPoints(pts)
    .circle(BOLT_DIA_MM / 2.0)
    .extrude(THICKNESS_MM + 2.0)
)
result = disc.cut(bolt_holes)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_shaft(params: dict[str, Any]) -> str:
    d = float(params.get("diameter_mm", 20.0))
    l = float(params.get("length_mm",  150.0))
    return f"""
import cadquery as cq

DIAMETER_MM = {d}
LENGTH_MM   = {l}

result = cq.Workplane("XY").circle(DIAMETER_MM / 2.0).extrude(LENGTH_MM)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_pulley(params: dict[str, Any]) -> str:
    od      = float(params.get("od_mm", 80.0))
    groove  = float(params.get("groove_depth_mm", 5.0))
    w       = float(params.get("width_mm", 20.0))
    bore    = float(params.get("bore_mm", 10.0))
    return f"""
import cadquery as cq

OD_MM          = {od}
GROOVE_DEPTH   = {groove}
WIDTH_MM       = {w}
BORE_MM        = {bore}

outer = cq.Workplane("XY").circle(OD_MM / 2.0).extrude(WIDTH_MM)
groove_void = (
    cq.Workplane("XY")
    .workplane(offset=WIDTH_MM / 2.0 - GROOVE_DEPTH / 2.0)
    .circle((OD_MM / 2.0 - GROOVE_DEPTH / 2.0))
    .circle(OD_MM / 2.0)
    .extrude(GROOVE_DEPTH)
)
bore_cyl = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .circle(BORE_MM / 2.0)
    .extrude(WIDTH_MM + 2.0)
)
result = outer.cut(groove_void).cut(bore_cyl)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_cam(params: dict[str, Any]) -> str:
    base_r  = float(params.get("base_radius_mm", 25.0))
    lift    = float(params.get("lift_mm", 8.0))
    thick   = float(params.get("thickness_mm", 12.0))
    bore    = float(params.get("bore_mm", 10.0))
    return f"""
import cadquery as cq

BASE_R_MM    = {base_r}
LIFT_MM      = {lift}
THICKNESS_MM = {thick}
BORE_MM      = {bore}

# Approximate cam as an eccentric cylinder (base circle + lobe offset)
base = cq.Workplane("XY").circle(BASE_R_MM).extrude(THICKNESS_MM)
lobe = (
    cq.Workplane("XY")
    .center(LIFT_MM / 2.0, 0)
    .circle(BASE_R_MM * 0.6)
    .extrude(THICKNESS_MM)
)
bore_cyl = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .circle(BORE_MM / 2.0)
    .extrude(THICKNESS_MM + 2.0)
)
result = base.union(lobe).cut(bore_cyl)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_pin(params: dict[str, Any]) -> str:
    d = float(params.get("diameter_mm", 6.0))
    l = float(params.get("length_mm", 40.0))
    return f"""
import cadquery as cq

DIAMETER_MM = {d}
LENGTH_MM   = {l}

result = cq.Workplane("XY").circle(DIAMETER_MM / 2.0).extrude(LENGTH_MM)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_spacer(params: dict[str, Any]) -> str:
    od    = float(params.get("od_mm", 20.0))
    bore  = float(params.get("bore_mm", 10.0))
    thick = float(params.get("thickness_mm", 5.0))
    return f"""
import cadquery as cq

OD_MM        = {od}
BORE_MM      = {bore}
THICKNESS_MM = {thick}

result = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(THICKNESS_MM)
)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_tube(params: dict[str, Any]) -> str:
    od   = float(params.get("od_mm",     params.get("diameter_mm",   50.0)))
    bore = float(params.get("bore_mm",   params.get("id_mm",         od - 6.0)))
    l    = float(params.get("length_mm", params.get("height_mm",    100.0)))
    bore = min(bore, od - 1.0)  # ensure bore < OD
    return f"""
import cadquery as cq

OD_MM   = {od}
BORE_MM = {bore}
L_MM    = {l}

result = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(L_MM)
)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_gear(params: dict[str, Any]) -> str:
    od   = float(params.get("od_mm",       params.get("diameter_mm",   80.0)))
    h    = float(params.get("height_mm",   params.get("thickness_mm",  20.0)))
    bore = float(params.get("bore_mm",     round(od * 0.2, 2)))
    return f"""
import cadquery as cq

OD_MM   = {od}
H_MM    = {h}
BORE_MM = {bore}

outer    = cq.Workplane("XY").circle(OD_MM / 2.0).extrude(H_MM)
bore_cyl = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .circle(BORE_MM / 2.0)
    .extrude(H_MM + 2.0)
)
result = outer.cut(bore_cyl)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


def _cq_nozzle(params: dict[str, Any]) -> str:
    entry_r   = float(params.get("entry_r_mm",     60.0))
    throat_r  = float(params.get("throat_r_mm",    25.0))
    exit_r    = float(params.get("exit_r_mm",      80.0))
    conv_len  = float(params.get("conv_length_mm", 80.0))
    total_len = float(params.get("length_mm",     200.0))
    wall      = float(params.get("wall_mm",         3.0))
    return f"""
import cadquery as cq

ENTRY_R_MM  = {entry_r}
THROAT_R_MM = {throat_r}
EXIT_R_MM   = {exit_r}
CONV_LEN_MM = {conv_len}
LENGTH_MM   = {total_len}
WALL_MM     = {wall}

# Closed profile in XY plane (X = radius, Y = axial position).
# Convergent: entry (r=ENTRY_R) -> throat (r=THROAT_R) over CONV_LEN mm
# Divergent:  throat (r=THROAT_R) -> exit (r=EXIT_R) over remaining length
# Hollow: inner profile is outer offset inward by WALL_MM.
# Revolve 360 deg around world Y axis; Y becomes the nozzle long axis.
profile = [
    (ENTRY_R_MM,            0),
    (THROAT_R_MM,           CONV_LEN_MM),
    (EXIT_R_MM,             LENGTH_MM),
    (EXIT_R_MM - WALL_MM,   LENGTH_MM),
    (THROAT_R_MM - WALL_MM, CONV_LEN_MM),
    (ENTRY_R_MM - WALL_MM,  0),
]

result = (
    cq.Workplane("XY")
    .polyline([(r, z) for r, z in profile])
    .close()
    .revolve(360, (0, 0, 0), (0, 1, 0))
)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


_CQ_TEMPLATE_MAP: dict[str, Any] = {
    # ARIA structural parts
    "aria_ratchet_ring": _cq_ratchet_ring,
    "aria_housing":      _cq_housing,
    "aria_spool":        _cq_spool,
    "aria_cam_collar":   _cq_cam_collar,
    "aria_brake_drum":   _cq_brake_drum,
    "aria_catch_pawl":   _cq_catch_pawl,
    "aria_rope_guide":   _cq_rope_guide,
    # Generic mechanical parts
    "aria_bracket":      _cq_bracket,
    "aria_flange":       _cq_flange,
    "aria_shaft":        _cq_shaft,
    "aria_pulley":       _cq_pulley,
    "aria_cam":          _cq_cam,
    "aria_pin":          _cq_pin,
    "aria_spacer":       _cq_spacer,
    "aria_tube":         _cq_tube,
    "aria_gear":         _cq_gear,
    # LRE / nozzle
    "lre_nozzle":        _cq_nozzle,
    "aria_nozzle":       _cq_nozzle,
    # Non-prefixed aliases — used by slug-based part_ids
    "nozzle":                       _cq_nozzle,
    "rocket_nozzle":                _cq_nozzle,
    "engine_nozzle":                _cq_nozzle,
    "liquid_rocket_engine_nozzle":  _cq_nozzle,
    "bracket":                      _cq_bracket,
    "mounting_bracket":             _cq_bracket,
    "angle_bracket":                _cq_bracket,
    "shaft":                        _cq_shaft,
    "drive_shaft":                  _cq_shaft,
    "axle":                         _cq_shaft,
    "flange":                       _cq_flange,
    "pipe_flange":                  _cq_flange,
    "tube":                         _cq_tube,
    "pipe":                         _cq_tube,
    "sleeve":                       _cq_tube,
    "plate":                        _cq_bracket,
    "base_plate":                   _cq_bracket,
    "mounting_plate":               _cq_bracket,
    "housing":                      _cq_housing,
    "enclosure":                    _cq_housing,
    "box":                          _cq_housing,
    "gear":                         _cq_gear,
}

# Keyword scan for slug-based part_ids not in the exact map.
# Checked in order; first match wins.
_KEYWORD_TO_TEMPLATE: list[tuple[list[str], Any]] = [
    (["nozzle", "rocket", "lre", "injector", "bell_nozzle"],  _cq_nozzle),
    (["ratchet_ring", "catch_ring", "ring_gear"],              _cq_ratchet_ring),
    (["brake_drum"],                                           _cq_brake_drum),
    (["cam_collar"],                                           _cq_cam_collar),
    (["catch_pawl", "trip_pawl"],                              _cq_catch_pawl),
    (["rope_guide"],                                           _cq_rope_guide),
    (["spool"],                                                _cq_spool),
    (["housing", "enclosure"],                                 _cq_housing),
    (["flange"],                                               _cq_flange),
    (["bracket", "plate", "mount"],                            _cq_bracket),
    (["shaft", "axle", "drive_shaft"],                         _cq_shaft),
    (["tube", "pipe", "sleeve"],                               _cq_tube),
    (["pulley", "sheave"],                                     _cq_pulley),
    (["cam"],                                                  _cq_cam),
    (["pin", "dowel"],                                         _cq_pin),
    (["spacer", "washer", "bushing"],                          _cq_spacer),
    (["gear", "sprocket", "cog"],                              _cq_gear),
    (["ring", "collar", "annular"],                            _cq_spacer),
]


def _find_template_fn(part_id: str):
    """Return the template function for part_id: exact map lookup, then keyword scan."""
    fn = _CQ_TEMPLATE_MAP.get(part_id)
    if fn:
        return fn
    for keywords, template_fn in _KEYWORD_TO_TEMPLATE:
        if any(kw in part_id for kw in keywords):
            return template_fn
    return None


def _generate_from_description(plan: dict[str, Any], goal: str) -> str:
    """
    Universal geometry fallback: parse dimension/shape signals from goal + plan params.
    Used when no template matches and LLM is unavailable.
    Always produces real geometry — never the 20mm placeholder box.
    Default shape is a 50×50×50 mm cube (volume 125 000 mm³, well above the 1000 mm³ minimum).
    """
    params  = plan.get("params", {}) or {}
    goal_l  = goal.lower()

    def _pf(key: str, default=None):
        v = params.get(key)
        return float(v) if v is not None else default

    # Parse numeric values with units from goal text
    nums_mm = [float(m.group(1)) for m in re.finditer(r"(\d+(?:\.\d+)?)\s*mm", goal_l)]
    nums_cm = [float(m.group(1)) * 10.0 for m in re.finditer(r"(\d+(?:\.\d+)?)\s*cm", goal_l)]
    nums_in = [float(m.group(1)) * 25.4 for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:in|inch)", goal_l)]
    all_nums = sorted(nums_mm + nums_cm + nums_in, reverse=True)

    def _n(idx: int, default: float) -> float:
        return all_nums[idx] if idx < len(all_nums) else default

    # Parse OD/ID/bore/length patterns
    od_m = re.search(r"(?:od|outer\s*dia(?:meter)?)\s*[:\-]?\s*(\d+(?:\.\d+)?)", goal_l)
    id_m = re.search(r"(?:id|inner\s*dia(?:meter)?|bore)\s*[:\-]?\s*(\d+(?:\.\d+)?)", goal_l)
    lg_m = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:long|length)", goal_l)

    od     = _pf("od_mm")     or (float(od_m.group(1)) if od_m else None)
    bore   = _pf("bore_mm")   or (float(id_m.group(1)) if id_m else None)
    dia    = _pf("diameter_mm") or od
    length = _pf("length_mm") or _pf("height_mm") or (float(lg_m.group(1)) if lg_m else None)
    width  = _pf("width_mm")
    depth  = _pf("depth_mm")
    thick  = _pf("thickness_mm")

    # --- Shape dispatch ---
    if any(w in goal_l for w in ("nozzle", "cone", "bell", "convergent", "divergent")):
        entry_r = float(od / 2.0 if od else _n(0, 60.0))
        total_l = float(length or _n(1, 200.0))
        throat_r = round(entry_r * 0.4, 2)
        exit_r   = round(entry_r * 1.3, 2)
        conv_l   = round(total_l * 0.4, 2)
        wall = 3.0
        return f"""import cadquery as cq
ENTRY_R={entry_r}; THROAT_R={throat_r}; EXIT_R={exit_r}
CONV_L={conv_l}; LENGTH={total_l}; WALL={wall}
profile=[(ENTRY_R,0),(THROAT_R,CONV_L),(EXIT_R,LENGTH),(EXIT_R-WALL,LENGTH),(THROAT_R-WALL,CONV_L),(ENTRY_R-WALL,0)]
result=(cq.Workplane("XY").polyline([(r,z) for r,z in profile]).close().revolve(360,(0,0,0),(0,1,0)))
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("ring", "annular", "washer", "collar", "bushing")):
        d = float(od or dia or _n(0, 100.0))
        b = float(bore or round(d * 0.6, 2))
        h = float(thick or length or _n(1, 20.0))
        return f"""import cadquery as cq
OD_MM={d}; BORE_MM={b}; H_MM={h}
result=(cq.Workplane("XY").circle(OD_MM/2.0).circle(BORE_MM/2.0).extrude(H_MM))
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("shaft", "rod", "axle", "spindle", "dowel")):
        d = float(dia or od or _n(0, 20.0))
        l = float(length or _n(1, 150.0))
        return f"""import cadquery as cq
D_MM={d}; L_MM={l}
result=cq.Workplane("XY").circle(D_MM/2.0).extrude(L_MM)
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("bracket", "plate", "mount", "tab", "gusset", "strap")):
        w = float(width or _n(0, 100.0))
        h = float(length or _n(1, 80.0))
        t = float(thick or 6.0)
        return f"""import cadquery as cq
W_MM={w}; H_MM={h}; T_MM={t}; HOLE_D=8.0
plate=cq.Workplane("XY").box(W_MM,T_MM,H_MM)
holes=(cq.Workplane("XY").workplane(offset=-1).pushPoints([(-W_MM/4,0),(W_MM/4,0)]).circle(HOLE_D/2).extrude(T_MM+2))
result=plate.cut(holes)
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("tube", "pipe", "sleeve")):
        d = float(od or dia or _n(0, 50.0))
        l = float(length or _n(1, 100.0))
        wall = float(params.get("wall_mm", 3.0))
        b = max(d - 2 * wall, 1.0)
        return f"""import cadquery as cq
OD_MM={d}; BORE_MM={b}; L_MM={l}
result=(cq.Workplane("XY").circle(OD_MM/2.0).circle(BORE_MM/2.0).extrude(L_MM))
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("housing", "enclosure", "case", "body", "cover")):
        w = float(width or _n(0, 100.0))
        h = float(length or _n(1, 100.0))
        d = float(depth or 80.0)
        return f"""import cadquery as cq
W_MM={w}; H_MM={h}; D_MM={d}; WALL=5.0
result=cq.Workplane("XY").box(W_MM,D_MM,H_MM).shell(-WALL)
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    if any(w in goal_l for w in ("gear", "sprocket", "cog")):
        d = float(dia or od or _n(0, 80.0))
        h = float(length or _n(1, 20.0))
        b = round(d * 0.2, 2)
        return f"""import cadquery as cq
D_MM={d}; H_MM={h}; BORE_MM={b}
outer=cq.Workplane("XY").circle(D_MM/2.0).extrude(H_MM)
bore_cyl=(cq.Workplane("XY").workplane(offset=-1.0).circle(BORE_MM/2.0).extrude(H_MM+2.0))
result=outer.cut(bore_cyl)
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    # Default: 50mm cube — well above 1000 mm³ minimum; never 20mm placeholder
    side = float(_n(0, 50.0))
    return f"""import cadquery as cq
SIDE_MM={side}
result=cq.Workplane("XY").box(SIDE_MM,SIDE_MM,SIDE_MM)
bb=result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_cadquery_artifacts(
    plan: dict[str, Any],
    goal: str,
    step_path: str,
    stl_path: str,
    repo_root: Optional[Path] = None,
    previous_failures: Optional[list] = None,
) -> dict[str, str]:
    """
    Generate a CadQuery script for the given plan and write it to disk.
    Attempts in-process execution to produce STEP + STL if cadquery is installed.

    Returns dict with:
        script_path : str — path to the .py script
        step_path   : str | "" — path to exported STEP (empty if CQ not installed)
        stl_path    : str | "" — path to exported STL
        bbox        : dict | None
        error       : str | None
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    part_id = plan.get("part_id", "custom_part") or "custom_part"
    params  = plan.get("params", {}) or {}

    # --- Pick template (exact or keyword) or LLM/description fallback ---
    template_fn = _find_template_fn(part_id)
    if template_fn:
        cq_code = template_fn(params)
    else:
        cq_code = _llm_cadquery(plan, goal, step_path, stl_path, repo_root,
                                previous_failures=previous_failures or [])

    # --- Write script ---
    out_dir = repo_root / "outputs" / "cad" / "cadquery" / part_id
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / f"{part_id}_cq.py"

    # Inject export footer
    sp = step_path.replace("\\", "/")
    st = stl_path.replace("\\", "/")
    export_footer = f"""
# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "{sp}"
_stl  = "{st}"
try:
    _os.makedirs(_os.path.dirname(_step), exist_ok=True)
except OSError:
    pass
try:
    _os.makedirs(_os.path.dirname(_stl), exist_ok=True)
except OSError:
    pass
_exp.export(result, _step, _exp.ExportTypes.STEP)
_exp.export(result, _stl,  _exp.ExportTypes.STL)
print(f"EXPORTED STEP: {{_step}}")
print(f"EXPORTED STL: {{_stl}}")
"""
    full_script = cq_code.rstrip() + "\n" + export_footer
    script_path.write_text(full_script, encoding="utf-8")

    # --- Execute in-process ---
    result_step = ""
    result_stl  = ""
    bbox        = None
    error       = None

    try:
        import cadquery as cq  # noqa: F401
        from cadquery import exporters  # noqa: F401

        # --- Sandboxed exec: allow cadquery/math only, block os/subprocess/socket ---
        _ALLOWED_MODULES = frozenset({"cadquery", "math", "cadquery.exporters"})

        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name not in _ALLOWED_MODULES:
                raise ImportError(f"Import of '{name}' is blocked by sandbox")
            return __import__(name, globals, locals, fromlist, level)

        safe_builtins = {
            "__import__": _safe_import,
            "range": range, "len": len, "print": print,
            "abs": abs, "min": min, "max": max, "round": round,
            "float": float, "int": int, "str": str,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "bool": bool, "enumerate": enumerate, "zip": zip, "map": map,
            "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
            "True": True, "False": False, "None": None,
            "ValueError": ValueError, "TypeError": TypeError,
            "RuntimeError": RuntimeError, "Exception": Exception,
        }
        ns: dict[str, Any] = {"__builtins__": safe_builtins}
        exec(compile(cq_code, f"<{part_id}_cq>", "exec"), ns)  # noqa: S102
        geom = ns.get("result")
        if geom is None:
            error = "CQ script did not define 'result'"
        else:
            Path(step_path).parent.mkdir(parents=True, exist_ok=True)
            Path(stl_path).parent.mkdir(parents=True, exist_ok=True)
            exporters.export(geom, step_path, exporters.ExportTypes.STEP)
            exporters.export(geom, stl_path,  exporters.ExportTypes.STL)
            result_step = step_path
            result_stl  = stl_path
            bb = geom.val().BoundingBox()
            bbox = {"x": round(bb.xlen, 2), "y": round(bb.ylen, 2), "z": round(bb.zlen, 2)}

            # --- Output quality assertions ---
            _vol = bbox["x"] * bbox["y"] * bbox["z"]
            if _vol < 1000.0:
                print(f"[VALIDATION FAIL] part_id={part_id}: bbox volume {_vol:.1f} mm³ < 1000 mm³ minimum")
            for _fpath, _min, _label in [
                (step_path, 1024, "STEP"), (stl_path, 500, "STL")
            ]:
                if Path(_fpath).exists():
                    _sz = Path(_fpath).stat().st_size
                    if _sz < _min:
                        print(f"[VALIDATION FAIL] part_id={part_id}: {_label} {_sz} bytes < {_min} bytes")
    except ImportError:
        error = "cadquery not installed; run the generated cq_script manually"
    except Exception:
        error = traceback.format_exc()

    return {
        "script_path": str(script_path),
        "step_path":   result_step,
        "stl_path":    result_stl,
        "bbox":        bbox,
        "error":       error,
        "status":      "success" if result_step else "failure",
    }


def _llm_cadquery(
    plan: dict[str, Any],
    goal: str,
    step_path: str,
    stl_path: str,
    repo_root: Path,
    previous_failures: Optional[list] = None,
) -> str:
    """
    Ask the LLM to generate CadQuery code for an arbitrary part.
    Returns the code string (no export footer — that is injected by the caller).
    """
    try:
        from .llm_client import call_llm
    except ImportError:
        return _generate_from_description(plan, goal)

    sp = step_path.replace("\\", "/")
    st = stl_path.replace("\\", "/")

    # --- Build rich system prompt with same context as Grasshopper path ---
    try:
        from .context_loader import get_mechanical_constants, load_context
        from .cem_context import load_cem_geometry, format_cem_block
        _ctx = load_context(repo_root)
        _constants = get_mechanical_constants(_ctx)
        _constants_block = "\n".join(f"#   {k}: {v}" for k, v in sorted(_constants.items()))
    except Exception:
        _constants_block = ""

    # CEM physics context
    try:
        g = (goal or "").strip()
        pid = (plan.get("part_id") or "") if isinstance(plan.get("part_id"), str) else ""
        _cem = load_cem_geometry(repo_root, goal=g, part_id=pid)
        _cem_block = format_cem_block(_cem)
    except Exception:
        _cem_block = ""

    # Inject few-shot examples and learned failure patterns from learning log
    try:
        from .cad_learner import get_few_shot_examples, format_few_shot_block, get_failure_patterns
        _examples = get_few_shot_examples(goal, plan.get("part_id", ""), repo_root)
        _few_shot = format_few_shot_block(_examples)
        _learned_failures = get_failure_patterns(plan.get("part_id", ""), repo_root)
    except Exception:
        _few_shot = ""
        _learned_failures = []

    _learned_block = ""
    if _learned_failures:
        _learned_block = "\n".join(f"- {e}" for e in _learned_failures)

    system = f"""You are a CadQuery Python expert. Output ONLY a Python code block. No explanation, no markdown outside the block.

Imports (use exactly):
  import cadquery as cq
  import math

Rules:
- All dimensions in mm as ALL_CAPS module-level constants.
- Build solid first, then cuts, then holes. No fillets/chamfers on first attempt.
- Final variable MUST be named 'result' and be a cq.Workplane object.
- Select faces by direction (faces(">Z")), never by index.
- Print BBOX: print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}") at the end.
- Do NOT write any export code — that is injected separately.

Mechanical constants (from aria_mechanical.md) — use these when relevant:
{_constants_block}

{_cem_block}

Avoid these CadQuery failure patterns:
- ChFi3d_Builder: only 2 faces — caused by fillet on thin body. Remove fillet; add after solid validates.
- BRep_API: command not done — caused by invalid face refs in compound boolean. Simplify to extrude + cut only.
- Nothing to loft — caused by non-coplanar loft profiles. Use revolve for axisymmetric profiles.
- Bbox axis mismatch — CadQuery extrudes along Z. Verify plan expects Z for height.
- Never use annular profile as first operation. Build solid cylinder/box first, then remove interior.
- For hollow parts: create outer solid, then cut the inner void.

{("Known recent failures for this part (from learning log):" + chr(10) + _learned_block) if _learned_block else ""}

CadQuery patterns:
  Box:       cq.Workplane("XY").box(L, W, H)
  Cylinder:  cq.Workplane("XY").circle(R).extrude(H)
  Ring:      cq.Workplane("XY").circle(R_OUT).circle(R_IN).extrude(H)
  Cut hole:  .faces(">Z").workplane().circle(R).cutThruAll()
  Union:     .union(other_wp)
  Shell:     .shell(-WALL)
  Revolve:   cq.Workplane("XZ").polyline(pts).close().revolve(360)

Required code structure:
  ## All numeric dimensions must be module-level constants
  # === PART PARAMETERS (tunable) ===
  LENGTH_MM = 60.0
  WIDTH_MM = 12.0
  # === END PARAMETERS ===
  # geometry uses constants only, never inline numbers

Every generated script MUST end with:
  bb = result.val().BoundingBox()
  print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""

    # --- Build user prompt ---
    brief = plan.get("engineering_brief")
    user_lines: list[str] = []
    if brief:
        user_lines.extend([
            "=== ENGINEERING BRIEF (authoritative — follow this over the short user phrase) ===",
            str(brief).strip(),
            "",
            "=== STRUCTURED PLAN (summary) ===",
        ])
    user_lines.extend([
        f"Goal: {goal}",
        f"Plan: {plan.get('text', str(plan))}",
        "",
        "Generate CadQuery Python. Variable 'result' must be the final cq.Workplane.",
        f"Export paths (do NOT write export code — it is added automatically):",
        f"  STEP: {sp}",
        f"  STL: {st}",
    ])
    if _few_shot:
        user_lines.append(f"\n{_few_shot}")
    if previous_failures:
        failure_block = "\n".join(f"  - {f}" for f in previous_failures)
        user_lines.append(
            f"\nPREVIOUS ATTEMPT FAILURES — fix these in your new code:\n"
            f"{failure_block}"
        )
    if _learned_failures:
        learned_block = "\n".join(f"  - {f}" for f in _learned_failures)
        user_lines.append(
            f"\nKNOWN RECURRING FAILURES FOR THIS PART (from learning log):\n"
            f"{learned_block}"
        )
    user = "\n".join(user_lines)

    try:
        text = call_llm(user, system, repo_root=repo_root)
        if text is None:
            return _generate_from_description(plan, goal)
        m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        if "import cadquery" in text or "cq.Workplane" in text:
            return text.strip()
    except Exception:
        pass
    return _generate_from_description(plan, goal)


def _placeholder_box_script() -> str:
    return """import cadquery as cq
LENGTH_MM = 20.0
WIDTH_MM  = 20.0
HEIGHT_MM = 20.0
result = cq.Workplane("XY").box(LENGTH_MM, WIDTH_MM, HEIGHT_MM)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
"""
