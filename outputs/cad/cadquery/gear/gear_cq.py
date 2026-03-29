
import cadquery as cq
import math

FACE_W       = 6.0
BORE         = 3.0
HUB_OD       = 9.0
SPOKE_STYLE  = "petal"
N_SPOKES     = 5
KEYWAY_W     = 0.0
STEP_PATH    = r""
STL_PATH     = r""

# Pre-computed involute polygon (195 pts, 15t, m=1.0mm)
# No runtime math — points were calculated at template-generation time.
all_pts = [(5.70966, -2.5421), (6.94677, -1.18842), (7.12448, -1.1919), (7.64876, -1.0964), (8.46679, -0.75061), (5.90572, 6.1133), (8.31425, 1.76725), (7.88165, -3.1827), (8.46679, 0.75061), (7.64876, 1.0964), (7.12448, 1.1919), (6.94677, 1.18842), (5.70966, 2.5421), (6.25, 0.0), (6.82957, 1.73983), (6.99333, 1.80893), (7.43343, 2.10941), (8.0401, 2.75804), (2.90864, 7.98685), (6.87664, 4.99617), (8.49477, 0.29821), (7.4295, 4.12947), (6.54154, 4.11264), (6.02375, 3.98665), (5.86282, 3.91118), (4.18207, 4.64466), (5.70966, 2.5421), (5.53147, 4.36725), (5.65297, 4.49698), (5.9328, 4.9505), (6.2232, 5.7898), (-0.59137, 8.4794), (4.25, 7.36122), (7.63906, 3.72756), (5.10758, 6.79431), (4.30323, 6.41777), (3.88145, 6.09206), (3.76513, 5.95767), (1.93136, 5.9441), (4.18207, 4.64466), (3.27693, 6.23953), (3.33515, 6.40747), (3.40634, 6.93559), (3.33026, 7.82045), (-3.98913, 7.50579), (0.88849, 8.45344), (5.4625, 6.51238), (1.90251, 8.28435), (1.32085, 7.61321), (1.06802, 7.1441), (1.01641, 6.97402), (-0.6533, 6.21576), (1.93136, 5.9441), (0.45578, 7.03294), (0.44066, 7.21004), (0.29088, 7.72146), (-0.13852, 8.49887), (-6.69713, 5.23436), (-2.62664, 8.08398), (2.34141, 8.17116), (-1.63152, 8.34195), (-1.88991, 7.49225), (-1.93009, 6.96087), (-1.90805, 6.78449), (-3.125, 5.41266), (-0.6533, 6.21576), (-2.44418, 6.61029), (-2.53002, 6.76593), (-2.87486, 7.17222), (-3.58335, 7.70776), (-8.24713, 2.05786), (-5.68761, 6.31673), (-1.18452, 8.41706), (-4.88344, 6.95715), (-4.77389, 6.07581), (-4.59446, 5.57403), (-4.50259, 5.42187), (-5.05636, 3.67366), (-3.125, 5.41266), (-4.92152, 5.04466), (-5.06324, 5.15194), (-5.54352, 5.38283), (-6.40858, 5.58391), (-8.37114, -1.47447), (-7.76514, 3.45726), (-4.50564, 7.20758), (-7.29098, 4.3694), (-6.83242, 3.60882), (-6.46441, 3.2234), (-6.31859, 3.12176), (-6.11342, 1.29945), (-5.05636, 3.67366), (-6.54788, 2.60677), (-6.72099, 2.64712), (-7.25366, 2.66271), (-8.12571, 2.49455), (-7.04769, -4.75184), (-8.5, 0.0), (-7.04769, 4.75184), (-8.43783, 1.02614), (-7.70957, 0.51782), (-7.21661, 0.31541), (-7.04206, 0.28186), (-6.11342, -1.29945), (-6.11342, 1.29945), (-7.04206, -0.28186), (-7.21661, -0.31541), (-7.70957, -0.51782), (-8.43783, -1.02614), (-4.50564, -7.20758), (-7.76514, -3.45726), (-8.37114, 1.47447), (-8.12571, -2.49455), (-7.25366, -2.66271), (-6.72099, -2.64712), (-6.54788, -2.60677), (-5.05636, -3.67366), (-6.11342, -1.29945), (-6.31859, -3.12176), (-6.46441, -3.2234), (-6.83242, -3.60882), (-7.29098, -4.3694), (-1.18452, -8.41706), (-5.68761, -6.31673), (-8.24713, -2.05786), (-6.40858, -5.58391), (-5.54352, -5.38283), (-5.06324, -5.15194), (-4.92152, -5.04466), (-3.125, -5.41266), (-5.05636, -3.67366), (-4.50259, -5.42187), (-4.59446, -5.57403), (-4.77389, -6.07581), (-4.88344, -6.95715), (2.34141, -8.17116), (-2.62664, -8.08398), (-6.69713, -5.23436), (-3.58335, -7.70776), (-2.87486, -7.17222), (-2.53002, -6.76593), (-2.44418, -6.61029), (-0.6533, -6.21576), (-3.125, -5.41266), (-1.90805, -6.78449), (-1.93009, -6.96087), (-1.88991, -7.49225), (-1.63152, -8.34195), (5.4625, -6.51238), (0.88849, -8.45344), (-3.98913, -7.50579), (-0.13852, -8.49887), (0.29088, -7.72146), (0.44066, -7.21004), (0.45578, -7.03294), (1.93136, -5.9441), (-0.6533, -6.21576), (1.01641, -6.97402), (1.06802, -7.1441), (1.32085, -7.61321), (1.90251, -8.28435), (7.63906, -3.72756), (4.25, -7.36122), (-0.59137, -8.4794), (3.33026, -7.82045), (3.40634, -6.93559), (3.33515, -6.40747), (3.27693, -6.23953), (4.18207, -4.64466), (1.93136, -5.9441), (3.76513, -5.95767), (3.88145, -6.09206), (4.30323, -6.41777), (5.10758, -6.79431), (8.49477, -0.29821), (6.87664, -4.99617), (2.90864, -7.98685), (6.2232, -5.7898), (5.9328, -4.9505), (5.65297, -4.49698), (5.53147, -4.36725), (5.70966, -2.5421), (4.18207, -4.64466), (5.86282, -3.91118), (6.02375, -3.98665), (6.54154, -4.11264), (7.4295, -4.12947), (7.88165, 3.1827), (8.31425, -1.76725), (5.90572, -6.1133), (8.0401, -2.75804), (7.43343, -2.10941), (6.99333, -1.80893), (6.82957, -1.73983), (6.25, -0.0)]

# ── One extrude with bore as inner wire — zero bore boolean ──────────────────
# CadQuery detects that the circle (bore/2) is inside the outer polygon wire
# and builds an annular face automatically.  OCCT sees a face-with-hole extrude,
# not a boolean subtract — dramatically cheaper on large polygon bodies.
gear = (
    cq.Workplane("XY")
    .polyline(all_pts)
    .close()
    .circle(BORE / 2.0)   # inner wire → bore hole, no boolean needed
    .extrude(FACE_W)
)

# Optional keyway (small rect cut on bore)
if KEYWAY_W > 0:
    kd = KEYWAY_W * 0.6
    kw = (cq.Workplane("XY")
          .rect(KEYWAY_W, kd * 2)
          .extrude(FACE_W + 2)
          .translate((0, BORE / 2 + kd - 1, -1)))
    gear = gear.cut(kw)

# ── Spoke / lightening cutouts — compound-then-single-cut (2 booleans max) ──
RIM_R        = 5.75000
SPOKE_ZONE_R = 5.12500
CUTOUT_H     = 0.25000
ELL_A        = 0.12500
ELL_B        = 2.44730
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
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/gear_preview.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/gear_preview.stl"
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
