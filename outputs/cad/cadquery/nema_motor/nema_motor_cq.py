
import cadquery as cq, math
FRAME   = 42.3
LENGTH  = 40.0
SHAFT_D = 5.0
SHAFT_L = 24.0
BOSS_D  = 22.0
BOSS_H  = 2.0
BOLT_D  = 3.0
FLAT_D  = 0.5

# Body — square prism
body = cq.Workplane("XY").box(FRAME, FRAME, LENGTH)

# Mounting holes from front face (4x on bolt circle)
body = (body.faces(">Z").workplane()
    .pushPoints([(10.9602, 10.9602), (-10.9602, 10.9602), (-10.9602, -10.9602), (10.9602, -10.9602)])
    .circle(BOLT_D / 2).cutThruAll()
)

# Front boss
boss = cq.Workplane("XY").workplane(offset=LENGTH/2).circle(BOSS_D/2).extrude(BOSS_H)
result = body.union(boss)

# Shaft
shaft = cq.Workplane("XY").workplane(offset=LENGTH/2 + BOSS_H).circle(SHAFT_D/2).extrude(SHAFT_L)
result = result.union(shaft)

# D-flat: box positioned so its -Y face is at flat_d from shaft centre
flat_edge = SHAFT_D / 2 - FLAT_D
cut = (cq.Workplane("XY")
    .workplane(offset=LENGTH/2 + BOSS_H)
    .center(0, flat_edge + SHAFT_D)
    .rect(SHAFT_D * 4, SHAFT_D * 2)
    .extrude(SHAFT_L)
)
result = result.cut(cut)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/nema17.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/components/cache/nema17.stl"
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
