
import cadquery as cq
import math

FACE_W      = 4.0
BORE        = 3.0
ROOT_R      = 3.60000
SPOKE_INNER = 1.9000
SPOKE_R     = 2.7500
SPOKE_LEN   = 1.4000
SPOKE_W     = 0.5000
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
tooth_pts_list = [[(3.59781, -0.12564), (4.5, 0.0), (3.51494, 0.77796)], [(3.33786, 1.34858), (4.11095, 1.83031), (2.89463, 2.14035)], [(2.50077, 2.58962), (3.01109, 3.34415), (1.77382, 3.13266)], [(1.23127, 3.38289), (1.39058, 4.27975), (0.3463, 3.58331)], [(-0.25112, 3.59123), (-0.47038, 4.47535), (-1.1411, 3.41436)], [(-1.6901, 3.17861), (-2.25, 3.89711), (-2.4312, 2.65505)], [(-2.83684, 2.21638), (-3.64058, 2.64503), (-3.30091, 1.43665)], [(-3.49306, 0.87092), (-4.40166, 0.9356), (-3.59987, -0.03016)], [(-3.54531, -0.62513), (-4.40166, -0.9356), (-3.27638, -1.49175)], [(-2.98454, -2.01309), (-3.64058, -2.64503), (-2.38637, -2.69541)], [(-1.90771, -3.05297), (-2.25, -3.89711), (-1.08374, -3.433)], [(-0.50102, -3.56497), (-0.47038, -4.47535), (0.40628, -3.577)], [(0.99229, -3.46054), (1.39058, -4.27975), (1.82606, -3.1025)], [(2.31404, -2.75776), (3.01109, -3.34415), (2.93009, -2.09155)], [(3.23566, -1.57814), (4.11095, -1.83031), (3.52748, -0.71896)]]

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
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/escape_wheel_preview.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/escape_wheel_preview.stl"
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
