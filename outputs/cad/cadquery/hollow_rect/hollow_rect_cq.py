
import cadquery as cq

WIDTH_MM  = 120.0
DEPTH_MM  = 70.0
LENGTH_MM = 100.0
WALL_MM   = 5.0
INNER_W   = 110.0
INNER_D   = 60.0

outer = cq.Workplane("XY").box(WIDTH_MM, DEPTH_MM, LENGTH_MM)
inner = cq.Workplane("XY").box(INNER_W, INNER_D, LENGTH_MM + 2.0)
result = outer.cut(inner)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/gearbox_case.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/gearbox_case.stl"
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
