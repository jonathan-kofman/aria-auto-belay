import cadquery as cq
from cadquery import exporters
import math

# Create main circular plate
result = cq.Workplane("XY").cylinder(5, 40)

# Cut center hole for bearing OD clearance
result = result.faces(">Z").workplane().hole(47.2)

# Create shoulder ring on top face
shoulder_ring = (cq.Workplane("XY")
    .cylinder(3, 55/2)
    .faces(">Z").workplane()
    .hole(47.2))

result = result.union(shoulder_ring)

# Create 6x M4 holes on 68mm bolt circle
bolt_circle_radius = 34  # 68mm diameter / 2
for i in range(6):
    angle = i * 60 * math.pi / 180  # 60 degrees between holes
    x = bolt_circle_radius * math.cos(angle)
    y = bolt_circle_radius * math.sin(angle)
    result = result.faces(">Z").workplane().center(x, y).hole(4)

# Fillet outer edge - select edges at Z=0 and Z=5 with radius ~40mm
result = result.edges("|Z").filter(lambda e: abs(e.radius() - 40) < 1).fillet(1)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)