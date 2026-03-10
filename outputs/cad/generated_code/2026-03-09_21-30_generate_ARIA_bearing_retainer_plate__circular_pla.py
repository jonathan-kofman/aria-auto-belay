import cadquery as cq
from cadquery import exporters
import math

# Create base plate
result = (cq.Workplane("XY")
    .cylinder(5, 40))  # 5mm thick, 80mm diameter (40mm radius)

# Add center hole
result = (result
    .faces(">Z").workplane()
    .hole(47.2))

# Add 6x M4 holes on 68mm bolt circle
bolt_circle_radius = 68/2
for i in range(6):
    angle = i * 60  # 360/6 = 60 degrees
    x = bolt_circle_radius * math.cos(math.radians(angle))
    y = bolt_circle_radius * math.sin(math.radians(angle))
    result = (result
        .faces(">Z").workplane()
        .center(x, y)
        .hole(4))

# Fillet outer edge BEFORE adding shoulder
result = result.edges().fillet(1)

# Add shoulder ring on top face
shoulder = (cq.Workplane("XY")
    .cylinder(3, 55/2)  # 3mm tall, 55mm outer diameter
    .faces(">Z").workplane()
    .hole(47.2 + 2*3))  # inner diameter = center hole + 2*wall thickness

result = result.union(shoulder)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)