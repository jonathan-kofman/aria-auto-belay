
import cadquery as cq

WIDTH_MM     = 100.0
HEIGHT_MM    = 8.0
THICKNESS_MM = 8.0
HOLE_DIA_MM  = 6.0

plate = cq.Workplane("XY").box(WIDTH_MM, THICKNESS_MM, HEIGHT_MM)
# 2 mounting hole(s) evenly spaced along the plate
hole_cyl = (
    cq.Workplane("XY")
    .workplane(offset=-1.0)
    .pushPoints([(-35.0, 0.0), (35.0, 0.0)])
    .circle(HOLE_DIA_MM / 2.0)
    .extrude(THICKNESS_MM + 2.0)
)
result = plate.cut(hole_cyl)
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
