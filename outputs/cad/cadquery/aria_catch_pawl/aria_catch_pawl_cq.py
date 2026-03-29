
import cadquery as cq

LENGTH_MM        = 36.0
WIDTH_MM         = 1.5
THICKNESS_MM     = 1.0
PIVOT_HOLE_D_MM  = 2.0

body = cq.Workplane("XY").box(LENGTH_MM, WIDTH_MM, THICKNESS_MM)
pivot = (cq.Workplane("XY").workplane(offset=-1.0)
         .center(-LENGTH_MM / 2.0 + WIDTH_MM / 2.0, 0)
         .circle(PIVOT_HOLE_D_MM / 2.0).extrude(THICKNESS_MM + 2.0))
result = body.cut(pivot)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/seconds_hand.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/seconds_hand.stl"
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
