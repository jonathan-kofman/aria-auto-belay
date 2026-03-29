
import cadquery as cq
OD    = 19.0
BORE  = 10.0
WIDTH = 5.0
WALL  = 1.5

# Outer ring
outer = (cq.Workplane("XY")
    .circle(OD / 2).circle(OD / 2 - WALL)
    .extrude(WIDTH)
)

# Inner ring
inner = (cq.Workplane("XY")
    .circle(BORE / 2 + WALL).circle(BORE / 2)
    .extrude(WIDTH)
)

# Retainer ring (thin disk between rings)
mid_r = (OD / 2 - WALL + BORE / 2 + WALL) / 2
ret_w = mid_r - BORE / 2 - WALL
retainer = (cq.Workplane("XY")
    .workplane(offset=WIDTH * 0.4)
    .circle(OD / 2 - WALL).circle(BORE / 2 + WALL)
    .extrude(WIDTH * 0.2)
)

result = outer.union(inner).union(retainer)
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/bearing_6800.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/bearing_6800.stl"
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
