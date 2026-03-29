
import cadquery as cq

WIDTH_MM     = 80.0
DEPTH_MM     = 60.0
THICKNESS_MM = 15.0
BORE_MM      = 35.0
BOLT_DIA_MM  = 5.0

result = cq.Workplane("XY").box(WIDTH_MM, DEPTH_MM, THICKNESS_MM)
result = result.faces('>Z').workplane().circle(BORE_MM / 2.0).cutThruAll()
result = result.faces('>Z').workplane().pushPoints([(25.0, 25.0), (-25.0, 25.0), (-25.0, -25.0), (25.0, -25.0)]).circle(BOLT_DIA_MM / 2.0).cutThruAll()
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/welding_torch_bracket.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/welding_torch_bracket.stl"
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
