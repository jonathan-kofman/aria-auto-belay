import cadquery as cq
from cadquery import exporters

# Create the main rectangular plate
result = cq.Workplane("XY").box(60, 12, 6)

# Add pivot hole 8mm from one end (centered at x=-22, y=0)
result = result.faces(">Z").workplane().center(-22, 0).hole(6)

# Create rounded nose at the other end
# Create a cylinder at the nose position and union it to round the tip
nose_center_x = 30 - 6  # 6mm from the end
nose_cylinder = cq.Workplane("XY").center(nose_center_x, 0).cylinder(6, 6)
result = result.union(nose_cylinder)

# Fillet edges selectively to avoid the issue
# Fillet vertical edges only
result = result.edges("|Z").fillet(0.5)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)