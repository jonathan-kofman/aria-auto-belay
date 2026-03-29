
import cadquery as cq

WIDTH_MM     = 200.0
DEPTH_MM     = 200.0
THICKNESS_MM = 15.0
BORE_MM      = 120.0
BOLT_DIA_MM  = 8.0

result = cq.Workplane("XY").box(WIDTH_MM, DEPTH_MM, THICKNESS_MM)

# Center bore
bore_cyl = cq.Workplane("XY").workplane(offset=-1.0).circle(BORE_MM / 2.0).extrude(THICKNESS_MM + 2.0)
result = result.cut(bore_cyl)

# 4x bolt holes Ø8.0mm
bolt_cyl = (cq.Workplane("XY").workplane(offset=-1.0)
            .pushPoints([(80.0,80.0),(-80.0,80.0),(-80.0,-80.0),(80.0,-80.0)])
            .circle(BOLT_DIA_MM / 2.0).extrude(THICKNESS_MM + 2.0))
result = result.cut(bolt_cyl)
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
