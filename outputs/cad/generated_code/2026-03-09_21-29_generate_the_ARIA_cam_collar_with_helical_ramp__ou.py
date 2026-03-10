import cadquery as cq
from cadquery import exporters
import math

# Main collar cylinder
result = (cq.Workplane("XY")
    .cylinder(40, 55/2))

# Inner bore
result = (result.faces(">Z").workplane()
    .hole(25))

# Create helical ramp
# Ramp rises 5mm over 90 degrees, width 8mm, 2mm proud
ramp_points = []
n_points = 91  # 0 to 90 degrees
for i in range(n_points):
    angle = math.radians(i)
    z = (i / 90) * 5  # Rise 5mm over 90 degrees
    x = (55/2 + 1) * math.cos(angle)  # 1mm out from surface center
    y = (55/2 + 1) * math.sin(angle)
    ramp_points.append((x, y, z))

# Create ramp profile - rectangular cross section
ramp_profile = (cq.Workplane("YZ")
    .rect(8, 2)  # width 8mm, height 2mm
    .extrude(1))

# Create helical ramp by sweeping profile along path
ramp_path = cq.Workplane("XY").spline(ramp_points)
helical_ramp = (cq.Workplane("XY")
    .rect(8, 2)
    .sweep(ramp_path))

# Alternative approach - create ramp as series of small blocks
ramp_solid = cq.Workplane("XY")
for i in range(90):
    angle = math.radians(i)
    z = (i / 90) * 5
    x = (55/2 + 1) * math.cos(angle)
    y = (55/2 + 1) * math.sin(angle)
    
    block = (cq.Workplane("XY")
        .transformed(offset=(x, y, z), rotate=(0, 0, math.degrees(angle)))
        .box(2, 8, 1))
    
    if i == 0:
        ramp_solid = block
    else:
        ramp_solid = ramp_solid.union(block)

# Union ramp to collar
result = result.union(ramp_solid)

# M4 set screw holes at z=20mm, 180 degrees apart
result = (result.faces(">Z").workplane(offset=-20)
    .center(55/2, 0)
    .hole(4)
    .center(-55/2, 0)
    .hole(4))

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)