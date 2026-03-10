import cadquery as cq
from cadquery import exporters

# ARIA rope spool dimensions
outer_dia = 120.0
inner_bore = 47.2
flange_dia = 160.0
flange_thickness = 8.0
barrel_length = 80.0
total_length = 96.0
bolt_hole_dia = 6.0
bolt_circle_dia = 90.0
keyway_width = 14.0
keyway_depth = 5.0

# Create main barrel cylinder
result = (cq.Workplane("XY")
    .cylinder(barrel_length, outer_dia/2))

# Add flanges on both ends
flange = (cq.Workplane("XY")
    .cylinder(flange_thickness, flange_dia/2))

# Position flanges
left_flange = flange.translate((0, 0, -barrel_length/2 - flange_thickness/2))
right_flange = flange.translate((0, 0, barrel_length/2 + flange_thickness/2))

# Union barrel with flanges
result = result.union(left_flange).union(right_flange)

# Cut center bore
result = (result.faces(">Z").workplane()
    .hole(inner_bore))

# Cut M6 bolt holes on bolt circle through flanges
result = (result.faces(">Z").workplane()
    .polarArray(bolt_circle_dia/2, 0, 360, 4)
    .hole(bolt_hole_dia))

# Cut keyway - create rectangular slot through full length
keyway_slot = (cq.Workplane("XZ")
    .center(inner_bore/2 - keyway_depth/2, 0)
    .rect(keyway_depth, total_length + 1)
    .extrude(keyway_width))

result = result.cut(keyway_slot)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)