
import cadquery as cq
import math

FACE_W       = 3.0
BORE         = 10.0
HUB_OD       = 16.0
SPOKE_STYLE  = "straight"
N_SPOKES     = 5
KEYWAY_W     = 0.0
STEP_PATH    = r""
STL_PATH     = r""

# Pre-computed involute polygon (208 pts, 16t, m=0.8mm)
# No runtime math — points were calculated at template-generation time.
all_pts = [(5.08134, -2.10476), (5.91413, -1.09163), (6.05861, -1.09686), (6.48662, -1.02832), (7.15926, -0.76485), (5.12617, 5.05593), (7.06165, 1.40465), (6.67078, -2.70937), (7.15926, 0.76485), (6.48662, 1.02832), (6.05861, 1.09686), (5.91413, 1.09163), (5.08134, 2.10476), (5.5, 0.0), (5.88169, 1.25471), (6.01718, 1.30516), (6.38638, 1.53228), (6.90699, 2.03311), (2.80114, 6.63277), (5.98658, 4.00011), (7.19983, 0.04967), (6.3216, 3.44636), (5.59933, 3.43237), (5.17767, 3.3319), (5.0462, 3.27177), (3.88909, 3.88909), (5.08134, 2.10476), (4.95382, 3.41003), (5.05968, 3.50848), (5.31386, 3.8596), (5.60319, 4.52153), (0.04967, 7.19983), (4.00011, 5.98658), (6.63277, 2.80114), (4.52153, 5.60319), (3.8596, 5.31386), (3.50848, 5.05968), (3.41003, 4.95382), (2.10476, 5.08134), (3.88909, 3.88909), (3.27177, 5.0462), (3.3319, 5.17767), (3.43237, 5.59933), (3.44636, 6.3216), (-2.70937, 6.67078), (1.40465, 7.06165), (5.05593, 5.12617), (2.03311, 6.90699), (1.53228, 6.38638), (1.30516, 6.01718), (1.25471, 5.88169), (0.0, 5.5), (2.10476, 5.08134), (1.09163, 5.91413), (1.09686, 6.05861), (1.02832, 6.48662), (0.76485, 7.15926), (-5.05593, 5.12617), (-1.40465, 7.06165), (2.70937, 6.67078), (-0.76485, 7.15926), (-1.02832, 6.48662), (-1.09686, 6.05861), (-1.09163, 5.91413), (-2.10476, 5.08134), (0.0, 5.5), (-1.25471, 5.88169), (-1.30516, 6.01718), (-1.53228, 6.38638), (-2.03311, 6.90699), (-6.63277, 2.80114), (-4.00011, 5.98658), (-0.04967, 7.19983), (-3.44636, 6.3216), (-3.43237, 5.59933), (-3.3319, 5.17767), (-3.27177, 5.0462), (-3.88909, 3.88909), (-2.10476, 5.08134), (-3.41003, 4.95382), (-3.50848, 5.05968), (-3.8596, 5.31386), (-4.52153, 5.60319), (-7.19983, 0.04967), (-5.98658, 4.00011), (-2.80114, 6.63277), (-5.60319, 4.52153), (-5.31386, 3.8596), (-5.05968, 3.50848), (-4.95382, 3.41003), (-5.08134, 2.10476), (-3.88909, 3.88909), (-5.0462, 3.27177), (-5.17767, 3.3319), (-5.59933, 3.43237), (-6.3216, 3.44636), (-6.67078, -2.70937), (-7.06165, 1.40465), (-5.12617, 5.05593), (-6.90699, 2.03311), (-6.38638, 1.53228), (-6.01718, 1.30516), (-5.88169, 1.25471), (-5.5, 0.0), (-5.08134, 2.10476), (-5.91413, 1.09163), (-6.05861, 1.09686), (-6.48662, 1.02832), (-7.15926, 0.76485), (-5.12617, -5.05593), (-7.06165, -1.40465), (-6.67078, 2.70937), (-7.15926, -0.76485), (-6.48662, -1.02832), (-6.05861, -1.09686), (-5.91413, -1.09163), (-5.08134, -2.10476), (-5.5, 0.0), (-5.88169, -1.25471), (-6.01718, -1.30516), (-6.38638, -1.53228), (-6.90699, -2.03311), (-2.80114, -6.63277), (-5.98658, -4.00011), (-7.19983, -0.04967), (-6.3216, -3.44636), (-5.59933, -3.43237), (-5.17767, -3.3319), (-5.0462, -3.27177), (-3.88909, -3.88909), (-5.08134, -2.10476), (-4.95382, -3.41003), (-5.05968, -3.50848), (-5.31386, -3.8596), (-5.60319, -4.52153), (-0.04967, -7.19983), (-4.00011, -5.98658), (-6.63277, -2.80114), (-4.52153, -5.60319), (-3.8596, -5.31386), (-3.50848, -5.05968), (-3.41003, -4.95382), (-2.10476, -5.08134), (-3.88909, -3.88909), (-3.27177, -5.0462), (-3.3319, -5.17767), (-3.43237, -5.59933), (-3.44636, -6.3216), (2.70937, -6.67078), (-1.40465, -7.06165), (-5.05593, -5.12617), (-2.03311, -6.90699), (-1.53228, -6.38638), (-1.30516, -6.01718), (-1.25471, -5.88169), (-0.0, -5.5), (-2.10476, -5.08134), (-1.09163, -5.91413), (-1.09686, -6.05861), (-1.02832, -6.48662), (-0.76485, -7.15926), (5.05593, -5.12617), (1.40465, -7.06165), (-2.70937, -6.67078), (0.76485, -7.15926), (1.02832, -6.48662), (1.09686, -6.05861), (1.09163, -5.91413), (2.10476, -5.08134), (0.0, -5.5), (1.25471, -5.88169), (1.30516, -6.01718), (1.53228, -6.38638), (2.03311, -6.90699), (6.63277, -2.80114), (4.00011, -5.98658), (0.04967, -7.19983), (3.44636, -6.3216), (3.43237, -5.59933), (3.3319, -5.17767), (3.27177, -5.0462), (3.88909, -3.88909), (2.10476, -5.08134), (3.41003, -4.95382), (3.50848, -5.05968), (3.8596, -5.31386), (4.52153, -5.60319), (7.19983, -0.04967), (5.98658, -4.00011), (2.80114, -6.63277), (5.60319, -4.52153), (5.31386, -3.8596), (5.05968, -3.50848), (4.95382, -3.41003), (5.08134, -2.10476), (3.88909, -3.88909), (5.0462, -3.27177), (5.17767, -3.3319), (5.59933, -3.43237), (6.3216, -3.44636), (6.67078, 2.70937), (7.06165, -1.40465), (5.12617, -5.05593), (6.90699, -2.03311), (6.38638, -1.53228), (6.01718, -1.30516), (5.88169, -1.25471), (5.5, -0.0)]

# ── Extrude gear polygon then boolean-cut bore ───────────────────────────────
# Falls back to annular cylinder when polygon is degenerate (undercut small pinion).
TIP_R = 7.20000
try:
    gear = cq.Workplane("XY").polyline(all_pts).close().extrude(FACE_W)
    bore_cyl = cq.Workplane("XY").circle(BORE / 2.0).extrude(FACE_W + 2).translate((0, 0, -1))
    gear = gear.cut(bore_cyl)
except Exception:
    # Polygon degenerate (undercut pinion) — fall back to annular cylinder
    gear = cq.Workplane("XY").circle(TIP_R).circle(BORE / 2.0).extrude(FACE_W)

# Optional keyway (small rect cut on bore)
if KEYWAY_W > 0:
    kd = KEYWAY_W * 0.6
    kw = (cq.Workplane("XY")
          .rect(KEYWAY_W, kd * 2)
          .extrude(FACE_W + 2)
          .translate((0, BORE / 2 + kd - 1, -1)))
    gear = gear.cut(kw)

# ── Spoke / lightening cutouts — compound-then-single-cut (2 booleans max) ──
RIM_R        = 5.10000
SPOKE_ZONE_R = 6.55000
CUTOUT_H     = -3.70000
ELL_A        = -1.85000
ELL_B        = 3.12777
SPOKE_W      = 1.00000

if SPOKE_STYLE == "petal" and CUTOUT_H > 2.0:
    compound = None
    for i in range(N_SPOKES):
        ang = i * 2.0 * math.pi / N_SPOKES + math.pi / N_SPOKES
        cx  = SPOKE_ZONE_R * math.cos(ang)
        cy  = SPOKE_ZONE_R * math.sin(ang)
        c = (cq.Workplane("XY")
             .transformed(rotate=cq.Vector(0, 0, math.degrees(ang)))
             .ellipse(ELL_A, ELL_B)
             .extrude(FACE_W + 2)
             .translate((cx, cy, -1)))
        compound = c if compound is None else compound.union(c)
    if compound is not None:
        gear = gear.cut(compound)

elif SPOKE_STYLE == "minimal" and CUTOUT_H > 2.0:
    compound = None
    for i in range(N_SPOKES):
        ang = i * 2.0 * math.pi / N_SPOKES
        cx  = SPOKE_ZONE_R * math.cos(ang)
        cy  = SPOKE_ZONE_R * math.sin(ang)
        c = (cq.Workplane("XY")
             .transformed(rotate=cq.Vector(0, 0, math.degrees(ang)))
             .rect(CUTOUT_H, SPOKE_W)
             .extrude(FACE_W + 2)
             .translate((cx, cy, -1)))
        compound = c if compound is None else compound.union(c)
    if compound is not None:
        gear = gear.cut(compound)
# SPOKE_STYLE == "straight": solid disk — zero booleans

result = gear

if STEP_PATH:
    import cadquery as _cq_exp
    _cq_exp.exporters.export(result, STEP_PATH)
if STL_PATH:
    import cadquery as _cq_exp2
    _cq_exp2.exporters.export(result, STL_PATH)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/click_wheel_16t.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/click_wheel_16t.stl"
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
print(f"EXPORTED STEP: {_step}")
print(f"EXPORTED STL: {_stl}")
