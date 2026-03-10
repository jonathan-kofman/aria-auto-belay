import cadquery as cq
from cadquery import exporters

# Create main rectangular bar
result = cq.Workplane("XY").box(120, 15, 10)

# Add M5 through holes at 20mm from each end (centers at -40 and +40 from center)
result = result.faces(">Z").workplane().center(-40, 0).hole(5.0)
result = result.faces(">Z").workplane().center(40, 0).hole(5.0)

# Add M4 tapped hole (4.2mm drill dia) centered on top face at midpoint
result = result.faces(">Z").workplane().center(0, 0).hole(4.2)

# Chamfer both ends at 45 degrees, 3mm deep
result = result.faces(">X").chamfer(3)
result = result.faces("<X").chamfer(3)

# Fillet remaining edges 0.5mm (vertical edges not on chamfered faces)
result = result.edges("|Z").fillet(0.5)
result = result.edges("|Y").fillet(0.5)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)