import cadquery as cq
from cadquery import exporters
import math

# Create main cylindrical body
result = cq.Workplane("XY").cylinder(20, 40)

# Cut center bore
result = result.faces(">Z").workplane().hole(42)

# Create bolt holes on 65mm bolt circle
bolt_circle_radius = 65 / 2
for i in range(4):
    angle = i * 90 * math.pi / 180
    x = bolt_circle_radius * math.cos(angle)
    y = bolt_circle_radius * math.sin(angle)
    result = result.faces(">Z").workplane().center(x, y).hole(5.5)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)