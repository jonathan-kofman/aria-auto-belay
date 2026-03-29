
import cadquery as cq

OD_MM        = 48.0
WIDTH_MM     = 6.0
SHAFT_D_MM   = 33.0
WALL_MM      = 3.0

outer = cq.Workplane("XY").circle(OD_MM / 2.0).extrude(WIDTH_MM)
inner_void = (cq.Workplane("XY").workplane(offset=-1.0)
              .circle(OD_MM / 2.0 - WALL_MM).extrude(WIDTH_MM + 2.0))
shaft = (cq.Workplane("XY").workplane(offset=-1.0)
         .circle(SHAFT_D_MM / 2.0).extrude(WIDTH_MM + 2.0))
result = outer.cut(inner_void).cut(shaft)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/barrel_drum.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/barrel_drum.stl"
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
