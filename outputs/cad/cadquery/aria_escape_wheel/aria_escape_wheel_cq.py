
import cadquery as cq
import math

FACE_W      = 3.0
BORE        = 2.0
ROOT_R      = 5.76000
SPOKE_INNER = 1.4000
SPOKE_R     = 3.5800
SPOKE_LEN   = 4.0600
SPOKE_W     = 0.7200
N_SPOKES    = 3
STEP_PATH   = r""
STL_PATH    = r""

# ── Body: clean annular disk (bore to root circle) ───────────────────────────
# A simple circle-to-circle extrude gives OCCT a clean cylindrical body with
# flat smooth top/bottom faces — no non-convex polygon triangulation issues.
wheel = (
    cq.Workplane("XY")
    .circle(ROOT_R)
    .circle(BORE / 2.0)
    .extrude(FACE_W)
)

# ── Teeth: individual triangle prisms, union-compounded onto the rim ─────────
# Each tooth is a 3-point polygon (root_trail → tip → root_lead).
# OCCT can triangulate a flat triangle perfectly — no mesh artifacts.
# Union the 15 teeth into one compound first, then one union with the body.
tooth_pts_list = [[(5.75649, -0.20102), (7.2, 0.0), (5.6239, 1.24473)], [(5.34058, 2.15773), (6.57753, 2.9285), (4.63141, 3.42456)], [(4.00123, 4.1434), (4.81774, 5.35064), (2.83811, 5.01226)], [(1.97004, 5.41263), (2.22492, 6.84761), (0.55407, 5.73329)], [(-0.4018, 5.74597), (-0.7526, 7.16056), (-1.82577, 5.46298)], [(-2.70416, 5.08578), (-3.6, 6.23538), (-3.88992, 4.24808)], [(-4.53894, 3.54621), (-5.82492, 4.23205), (-5.28146, 2.29864)], [(-5.5889, 1.39347), (-7.04266, 1.49696), (-5.7598, -0.04825)], [(-5.67249, -1.00021), (-7.04266, -1.49696), (-5.24221, -2.3868)], [(-4.77526, -3.22095), (-5.82492, -4.23205), (-3.8182, -4.31265)], [(-3.05233, -4.88476), (-3.6, -6.23538), (-1.73398, -5.4928)], [(-0.80164, -5.70394), (-0.7526, -7.16056), (0.65005, -5.7232)], [(1.58767, -5.53687), (2.22492, -6.84761), (2.92169, -4.964)], [(3.70246, -4.41242), (4.81774, -5.35064), (4.68814, -3.34649)], [(5.17705, -2.52502), (6.57753, -2.9285), (5.64397, -1.15033)]]

tooth_cmp = None
for pts in tooth_pts_list:
    t = cq.Workplane("XY").polyline(pts).close().extrude(FACE_W)
    tooth_cmp = t if tooth_cmp is None else tooth_cmp.union(t)
if tooth_cmp is not None:
    wheel = wheel.union(tooth_cmp)

# ── Spoke slots (skeleton look) ──────────────────────────────────────────────
if SPOKE_LEN > 0.4:
    sp_cmp = None
    for i in range(N_SPOKES):
        ang = i * 2.0 * math.pi / N_SPOKES
        cx  = SPOKE_R * math.cos(ang)
        cy  = SPOKE_R * math.sin(ang)
        c = (cq.Workplane("XY")
             .transformed(rotate=cq.Vector(0, 0, math.degrees(ang)))
             .rect(SPOKE_LEN, SPOKE_W)
             .extrude(FACE_W + 2)
             .translate((cx, cy, -1)))
        sp_cmp = c if sp_cmp is None else sp_cmp.union(c)
    if sp_cmp is not None:
        wheel = wheel.cut(sp_cmp)

result = wheel

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
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/escape_wheel_15t.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/escape_wheel_15t.stl"
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
