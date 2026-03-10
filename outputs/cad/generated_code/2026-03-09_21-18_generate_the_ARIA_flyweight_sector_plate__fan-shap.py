import cadquery as cq
from cadquery import exporters
import math

# Create the fan-shaped sector
outer_radius = 85.0
inner_radius = 25.0
sector_angle = 120.0  # degrees
thickness = 8.0

# Convert angle to radians
angle_rad = math.radians(sector_angle)
half_angle = angle_rad / 2

# Create sector profile using points
points = []
# Start at inner radius, angle/2
points.append((inner_radius * math.cos(half_angle), inner_radius * math.sin(half_angle)))
# Outer radius, angle/2
points.append((outer_radius * math.cos(half_angle), outer_radius * math.sin(half_angle)))
# Outer radius, -angle/2
points.append((outer_radius * math.cos(-half_angle), outer_radius * math.sin(-half_angle)))
# Inner radius, -angle/2
points.append((inner_radius * math.cos(-half_angle), inner_radius * math.sin(-half_angle)))

# Create the sector profile
profile = (cq.Workplane("XY")
    .moveTo(points[0][0], points[0][1])
    .lineTo(points[1][0], points[1][1])
    .threePointArc((outer_radius, 0), (points[2][0], points[2][1]))
    .lineTo(points[3][0], points[3][1])
    .threePointArc((inner_radius, 0), (points[0][0], points[0][1]))
    .close())

# Extrude to create the main solid
result = profile.extrude(thickness)

# Pivot hole at inner arc center (origin)
result = result.faces(">Z").workplane().center(0, 0).hole(10.0)

# Weight pocket on outer face: 40mm x 15mm x 4mm deep at 65mm radius
pocket_x = 65.0  # centered at 65mm radius
pocket_y = 0.0
result = result.faces(">Z").workplane().center(pocket_x, pocket_y).rect(40.0, 15.0).cutBlind(-4.0)

# Mounting hole 6mm diameter at 50mm radius centered in sector
mounting_x = 50.0
mounting_y = 0.0
result = result.faces(">Z").workplane().center(mounting_x, mounting_y).hole(6.0)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)