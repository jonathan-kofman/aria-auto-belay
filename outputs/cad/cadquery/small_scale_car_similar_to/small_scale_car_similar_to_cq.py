import cadquery as cq
import math

# === PART PARAMETERS (tunable) ===
# Overall car body dimensions (Lego-style scale ~3-4x Lego brick)
BODY_LENGTH = 96.0
BODY_WIDTH = 40.0
BODY_HEIGHT = 16.0

# Cabin (upper body)
CABIN_LENGTH = 44.0
CABIN_WIDTH = 36.0
CABIN_HEIGHT = 18.0
CABIN_OFFSET_X = 4.0  # offset from center toward rear

# Wheel dimensions
WHEEL_RADIUS = 10.0
WHEEL_WIDTH = 8.0
WHEEL_AXLE_RADIUS = 2.5

# Wheel positions
WHEEL_BASE = 60.0       # distance between front and rear axles
WHEEL_TRACK = 48.0      # distance between left and right wheels
WHEEL_Z = 10.0          # wheel center height from ground

# Axle dimensions
AXLE_RADIUS = 2.0
AXLE_LENGTH = WHEEL_TRACK + WHEEL_WIDTH * 2 + 4.0

# Bumper
BUMPER_HEIGHT = 6.0
BUMPER_WIDTH = BODY_WIDTH
BUMPER_DEPTH = 4.0
BUMPER_THICKNESS = 3.0

# Stud (Lego-style top studs)
STUD_RADIUS = 3.9
STUD_HEIGHT = 1.8
STUD_ROWS = 3
STUD_COLS = 8
STUD_SPACING = 8.0

# Window cutout
WINDOW_WIDTH = 14.0
WINDOW_HEIGHT = 10.0
WINDOW_DEPTH = 3.0

# Ground clearance
GROUND_CLEARANCE = WHEEL_Z - WHEEL_RADIUS
# === END PARAMETERS ===

# --- Build car body (lower chassis) ---
# Body sits with bottom at Z=0, center at origin
body = cq.Workplane("XY").box(BODY_LENGTH, BODY_WIDTH, BODY_HEIGHT)

# --- Cabin (upper body) ---
cabin = (
    cq.Workplane("XY")
    .box(CABIN_LENGTH, CABIN_WIDTH, CABIN_HEIGHT)
    .translate((CABIN_OFFSET_X, 0, (BODY_HEIGHT + CABIN_HEIGHT) / 2))
)

# --- Combine body and cabin ---
result = body.union(cabin)

# --- Front bumper ---
bumper_front = (
    cq.Workplane("XY")
    .box(BUMPER_DEPTH, BUMPER_WIDTH, BUMPER_HEIGHT)
    .translate((BODY_LENGTH / 2 + BUMPER_DEPTH / 2, 0, (-BODY_HEIGHT + BUMPER_HEIGHT) / 2))
)
result = result.union(bumper_front)

# --- Rear bumper ---
bumper_rear = (
    cq.Workplane("XY")
    .box(BUMPER_DEPTH, BUMPER_WIDTH, BUMPER_HEIGHT)
    .translate((-BODY_LENGTH / 2 - BUMPER_DEPTH / 2, 0, (-BODY_HEIGHT + BUMPER_HEIGHT) / 2))
)
result = result.union(bumper_rear)

# --- Wheels (4 wheels) ---
wheel_positions = [
    ( WHEEL_BASE / 2,  WHEEL_TRACK / 2, 0),
    ( WHEEL_BASE / 2, -WHEEL_TRACK / 2, 0),
    (-WHEEL_BASE / 2,  WHEEL_TRACK / 2, 0),
    (-WHEEL_BASE / 2, -WHEEL_TRACK / 2, 0),
]

for (wx, wy, _) in wheel_positions:
    wz = -BODY_HEIGHT / 2 + GROUND_CLEARANCE + WHEEL_RADIUS
    wheel = (
        cq.Workplane("XZ")
        .center(wx, wz)
        .circle(WHEEL_RADIUS)
        .extrude(WHEEL_WIDTH)
        .translate((0, wy - WHEEL_WIDTH / 2, 0))
    )
    result = result.union(wheel)

# --- Axles ---
axle_positions = [WHEEL_BASE / 2, -WHEEL_BASE / 2]
for ax in axle_positions:
    wz = -BODY_HEIGHT / 2 + GROUND_CLEARANCE + WHEEL_RADIUS
    axle = (
        cq.Workplane("XZ")
        .center(ax, wz)
        .circle(AXLE_RADIUS)
        .extrude(AXLE_LENGTH)
        .translate((0, -AXLE_LENGTH / 2, 0))
    )
    result = result.union(axle)

# --- Lego-style studs on top of body ---
stud_x_start = -(STUD_COLS - 1) * STUD_SPACING / 2
stud_y_start = -(STUD_ROWS - 1) * STUD_SPACING / 2
top_z = BODY_HEIGHT / 2

for row in range(STUD_ROWS):
    for col in range(STUD_COLS):
        sx = stud_x_start + col * STUD_SPACING
        sy = stud_y_start + row * STUD_SPACING
        stud = (
            cq.Workplane("XY")
            .center(sx, sy)
            .circle(STUD_RADIUS)
            .extrude(STUD_HEIGHT)
            .translate((0, 0, top_z))
        )
        result = result.union(stud)

# --- Studs on top of cabin ---
cabin_top_z = BODY_HEIGHT / 2 + CABIN_HEIGHT
cabin_stud_rows = 2
cabin_stud_cols = 4
cs_x_start = CABIN_OFFSET_X - (cabin_stud_cols - 1) * STUD_SPACING / 2
cs_y_start = -(cabin_stud_rows - 1) * STUD_SPACING / 2

for row in range(cabin_stud_rows):
    for col in range(cabin_stud_cols):
        sx = cs_x_start + col * STUD_SPACING
        sy = cs_y_start + row * STUD_SPACING
        stud = (
            cq.Workplane("XY")
            .center(sx, sy)
            .circle(STUD_RADIUS)
            .extrude(STUD_HEIGHT)
            .translate((0, 0, cabin_top_z))
        )
        result = result.union(stud)

# --- Window cutouts on cabin sides ---
# Left window
win_left = (
    cq.Workplane("XZ")
    .center(CABIN_OFFSET_X, BODY_HEIGHT / 2 + CABIN_HEIGHT / 2)
    .rect(WINDOW_WIDTH, WINDOW_HEIGHT)
    .extrude(WINDOW_DEPTH)
    .translate((0, CABIN_WIDTH / 2 - WINDOW_DEPTH, 0))
)
result = result.cut(win_left)

# Right window
win_right = (
    cq.Workplane("XZ")
    .center(CABIN_OFFSET_X, BODY_HEIGHT / 2 + CABIN_HEIGHT / 2)
    .rect(WINDOW_WIDTH, WINDOW_HEIGHT)
    .extrude(WINDOW_DEPTH)
    .translate((0, -CABIN_WIDTH / 2, 0))
)
result = result.cut(win_right)

# --- Windshield cutout (front of cabin) ---
windshield = (
    cq.Workplane("YZ")
    .center(0, BODY_HEIGHT / 2 + CABIN_HEIGHT / 2)
    .rect(WINDOW_WIDTH, WINDOW_HEIGHT)
    .extrude(WINDOW_DEPTH)
    .translate((CABIN_OFFSET_X + CABIN_LENGTH / 2 - WINDOW_DEPTH, 0, 0))
)
result = result.cut(windshield)

# --- Rear window cutout ---
rear_window = (
    cq.Workplane("YZ")
    .center(0, BODY_HEIGHT / 2 + CABIN_HEIGHT / 2)
    .rect(WINDOW_WIDTH, WINDOW_HEIGHT)
    .extrude(WINDOW_DEPTH)
    .translate((CABIN_OFFSET_X - CABIN_LENGTH / 2, 0, 0))
)
result = result.cut(rear_window)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/llm_small_scale_car_similar_to.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/llm_small_scale_car_similar_to.stl"
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
