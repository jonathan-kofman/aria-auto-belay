import cadquery as cq
import math

# === PART PARAMETERS (tunable) ===
CASE_LENGTH = 54.0       # X dimension
CASE_WIDTH  = 45.0       # Y dimension
CASE_HEIGHT = 21.0       # Z dimension
WALL_T      = 1.5        # shell wall thickness

# Hinge cutout (rear, centered on back face)
HINGE_W     = 12.0       # width of hinge cutout
HINGE_H     = 6.0        # height of hinge cutout
HINGE_D     = 3.0        # depth into case

# Lightning port (bottom face, centered)
LIGHTNING_W = 8.0        # width of lightning port slot
LIGHTNING_H = 3.5        # height of lightning port slot
LIGHTNING_D = WALL_T + 1.0  # cut depth (through wall)

# Lid split line groove
LID_SPLIT_Z = 14.0       # Z height of split line from bottom
LID_GROOVE_W = 0.8
LID_GROOVE_D = 0.8
# === END PARAMETERS ===

# 1. Build outer solid box
outer = cq.Workplane("XY").box(CASE_LENGTH, CASE_WIDTH, CASE_HEIGHT)

# 2. Shell it (hollow interior)
shell = outer.shell(-WALL_T)

# 3. Hinge cutout on back face (max Y face), centered, near top
hinge_cut = (
    cq.Workplane("XY")
    .box(HINGE_W, HINGE_D, HINGE_H)
    .translate((0, (CASE_WIDTH / 2) - (HINGE_D / 2), (CASE_HEIGHT / 2) - (HINGE_H / 2)))
)
result = shell.cut(hinge_cut)

# 4. Lightning port on bottom face (min Z), centered in X, centered in Y
lightning_cut = (
    cq.Workplane("XY")
    .box(LIGHTNING_W, LIGHTNING_D, LIGHTNING_H)
    .translate((0, 0, -(CASE_HEIGHT / 2) + (LIGHTNING_H / 2)))
)
result = result.cut(lightning_cut)

# 5. Lid split line groove on front face (min Y face)
groove_cut_front = (
    cq.Workplane("XY")
    .box(CASE_LENGTH, LID_GROOVE_D, LID_GROOVE_W)
    .translate((0, -(CASE_WIDTH / 2) + (LID_GROOVE_D / 2), -(CASE_HEIGHT / 2) + LID_SPLIT_Z))
)
result = result.cut(groove_cut_front)

# 6. Lid split line groove on left face (min X face)
groove_cut_left = (
    cq.Workplane("XY")
    .box(LID_GROOVE_D, CASE_WIDTH, LID_GROOVE_W)
    .translate((-(CASE_LENGTH / 2) + (LID_GROOVE_D / 2), 0, -(CASE_HEIGHT / 2) + LID_SPLIT_Z))
)
result = result.cut(groove_cut_left)

# 7. Lid split line groove on right face (max X face)
groove_cut_right = (
    cq.Workplane("XY")
    .box(LID_GROOVE_D, CASE_WIDTH, LID_GROOVE_W)
    .translate(((CASE_LENGTH / 2) - (LID_GROOVE_D / 2), 0, -(CASE_HEIGHT / 2) + LID_SPLIT_Z))
)
result = result.cut(groove_cut_right)

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
