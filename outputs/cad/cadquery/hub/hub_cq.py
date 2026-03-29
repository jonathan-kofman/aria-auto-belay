
import cadquery as cq

OD_MM        = 42.0
BORE_MM      = 22.0
HEIGHT_MM    = 65.0
BOLT_R_MM    = 32.0
BOLT_DIA_MM  = 3.0

result = cq.Workplane("XY").circle(OD_MM / 2.0).extrude(HEIGHT_MM)
result = result.faces(">Z").workplane().circle(BORE_MM / 2.0).cutThruAll()
result = result.faces(">Z").workplane().pushPoints([(32.0, 0.0), (0.0, 32.0), (-32.0, 0.0), (-0.0, -32.0)]).circle(BOLT_DIA_MM / 2.0).cutThruAll()
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/rear_upright_r.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/rear_upright_r.stl"
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
