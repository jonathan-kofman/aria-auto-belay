import cadquery as cq
D_MM=144.0; H_MM=18.0; BORE_MM=28.8
outer=cq.Workplane("XY").circle(D_MM/2.0).extrude(H_MM)
bore_cyl=(cq.Workplane("XY").workplane(offset=-1.0).circle(BORE_MM/2.0).extrude(H_MM+2.0))
result=outer.cut(bore_cyl)
bb=result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_custom_part_preview.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_custom_part_preview.stl"
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
