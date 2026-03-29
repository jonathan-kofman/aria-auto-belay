
import cadquery as cq, math
WIDTH  = 25.0
HEIGHT = 16.0
LENGTH = 1000.0
HOLE_D = 5.5
HOLE_SPACING = 40.0
N_HOLES = 24
FIRST_HOLE = 40.0
SLOT_W = 12.5
SLOT_D = 7.2

# Rail body
result = cq.Workplane("XZ").box(WIDTH, HEIGHT, LENGTH)

# Mounting holes through base (along length)
hole_xs = [-(LENGTH/2) + FIRST_HOLE + i * HOLE_SPACING for i in range(N_HOLES)]
result = (result
    .faces(">Y")
    .workplane()
    .pushPoints([(x, 0) for x in hole_xs])
    .circle(HOLE_D / 2)
    .cutThruAll()
)

# Top T-slot channel (simplified: rectangular groove cut from top face)
slot_cutter = (cq.Workplane("XY")
    .box(SLOT_W, LENGTH, SLOT_D + 1.0)
    .translate((0, 0, HEIGHT / 2 - SLOT_D / 2 + 0.5))
)
result = result.cut(slot_cutter)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/mgn25_1000.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/mgn25_1000.stl"
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
