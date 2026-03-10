import cadquery as cq
from cadquery import exporters

# Create main solid
result = (cq.Workplane("XY")
    .box(120, 15, 10))

# Add holes BEFORE chamfers and fillets
result = (result
    .faces(">Z").workplane()
    .center(-40, 0).hole(5)  # M5 hole at 20mm from left end
    .center(40, 0).hole(5)   # M5 hole at 20mm from right end
    .center(0, 0).hole(4.2)) # M4 hole at center

# Apply chamfers to end faces
result = (result
    .faces(">X").chamfer(3)  # chamfer +X end
    .faces("<X").chamfer(3)) # chamfer -X end

# Apply fillet to vertical edges only
result = result.edges("|Z").fillet(0.5)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)