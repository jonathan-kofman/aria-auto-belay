import cadquery as cq
import math

# === PART PARAMETERS (tunable) ===
BRACKET_LENGTH = 80.0    # total length of bracket (X)
BRACKET_WIDTH  = 20.0    # width of bracket (Y)
BRACKET_HEIGHT = 10.0    # thickness of base plate (Z)

# Vertical wall
WALL_HEIGHT    = 40.0    # height of vertical wall
WALL_THICKNESS = 10.0    # thickness of vertical wall

# Mounting holes
HOLE_DIA       = 6.0     # diameter of mounting holes
HOLE_INSET     = 10.0    # inset from ends for holes
# === END PARAMETERS ===

# 1. Build horizontal base plate
base = cq.Workplane("XY").box(BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_HEIGHT)

# 2. Build vertical wall (along one long edge, centered in Y at back)
# Wall sits on top of base at the back edge
wall = (cq.Workplane("XY")
        .box(WALL_THICKNESS, BRACKET_WIDTH, WALL_HEIGHT)
        .translate((-(BRACKET_LENGTH / 2 - WALL_THICKNESS / 2), 0, (BRACKET_HEIGHT / 2 + WALL_HEIGHT / 2)))
        )

# 3. Union base and wall
result = base.union(wall)

# 4. Cut mounting holes through base plate (vertical, through Z)
result = (result
          .faces(">Z")
          .workplane()
          .pushPoints([
              (BRACKET_LENGTH / 2 - HOLE_INSET, 0),
              (-(BRACKET_LENGTH / 2 - HOLE_INSET), 0),
          ])
          .circle(HOLE_DIA / 2)
          .cutThruAll()
          )

# 5. Cut mounting holes through vertical wall (horizontal, through X)
result = (result
          .faces(">X")
          .workplane()
          .pushPoints([
              (0, WALL_HEIGHT / 4),
              (0, -WALL_HEIGHT / 4),
          ])
          .circle(HOLE_DIA / 2)
          .cutThruAll()
          )

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "outputs/cad/step/llm_simple_bracket.step"
_stl  = "outputs/cad/stl/llm_simple_bracket.stl"
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
