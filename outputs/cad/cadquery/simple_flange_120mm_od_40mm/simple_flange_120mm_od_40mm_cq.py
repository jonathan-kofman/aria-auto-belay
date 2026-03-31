
import cadquery as cq, math

OD_MM           = 120.0
BORE_MM         = 40.0
THICKNESS_MM    = 12.0
BOLT_CIRCLE_R   = 50.0
N_BOLTS         = 4
BOLT_DIA_MM     = 8.0

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
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/llm_part.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/llm_part.stl"
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
