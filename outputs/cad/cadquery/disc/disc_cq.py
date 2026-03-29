
import cadquery as cq

OD_MM        = 24.0
BORE_MM      = 7.0
THICKNESS_MM = 3.0

result = (
    cq.Workplane("XY")
    .circle(OD_MM / 2.0)
    .circle(BORE_MM / 2.0)
    .extrude(THICKNESS_MM)
)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/steering_wheel.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/steering_wheel.stl"
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
