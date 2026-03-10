import cadquery as cq
from cadquery import exporters
import math

# Create base ring
result = (cq.Workplane("XY")
    .cylinder(21, 213/2)
    .cut(cq.Workplane("XY").cylinder(21, 120/2))
)

# Create ratchet teeth
tooth_count = 12
angle_per_tooth = 360 / tooth_count
outer_radius = 213/2
inner_radius = outer_radius - 8  # tooth height 8mm

for i in range(tooth_count):
    base_angle = i * angle_per_tooth
    
    # Calculate tooth profile points
    # Drive face at 8 degrees from radial
    # Back face at 60 degrees from radial
    # Tooth tip flat 3mm wide
    
    # Convert tip width to angular width at outer radius
    tip_angle = math.degrees(3 / outer_radius)
    
    # Angles for tooth faces
    drive_angle = base_angle - tip_angle/2 - 8
    back_angle = base_angle + tip_angle/2 + 60
    
    # Create tooth profile points
    p1_angle = drive_angle
    p2_angle = base_angle - tip_angle/2
    p3_angle = base_angle + tip_angle/2
    p4_angle = back_angle
    
    # Convert to cartesian coordinates
    p1 = (inner_radius * math.cos(math.radians(p1_angle)), inner_radius * math.sin(math.radians(p1_angle)))
    p2 = (outer_radius * math.cos(math.radians(p2_angle)), outer_radius * math.sin(math.radians(p2_angle)))
    p3 = (outer_radius * math.cos(math.radians(p3_angle)), outer_radius * math.sin(math.radians(p3_angle)))
    p4 = (inner_radius * math.cos(math.radians(p4_angle)), inner_radius * math.sin(math.radians(p4_angle)))
    
    # Create tooth as extrusion
    tooth = (cq.Workplane("XY")
        .moveTo(p1[0], p1[1])
        .lineTo(p2[0], p2[1])
        .lineTo(p3[0], p3[1])
        .lineTo(p4[0], p4[1])
        .close()
        .extrude(21)
    )
    
    result = result.union(tooth)

# Add root fillets
result = result.edges("|Z").fillet(1.5)

# Add M6 bolt holes on 150mm bolt circle
bolt_circle_radius = 150/2
bolt_hole_count = 6

for i in range(bolt_hole_count):
    angle = i * 360 / bolt_hole_count
    x = bolt_circle_radius * math.cos(math.radians(angle))
    y = bolt_circle_radius * math.sin(math.radians(angle))
    
    result = result.faces(">Z").workplane().center(x, y).hole(6)

# Add M5 bolt holes on 135mm bolt circle
bolt_circle_radius_2 = 135/2
bolt_hole_count_2 = 6

for i in range(bolt_hole_count_2):
    angle = i * 360 / bolt_hole_count_2
    x = bolt_circle_radius_2 * math.cos(math.radians(angle))
    y = bolt_circle_radius_2 * math.sin(math.radians(angle))
    
    result = result.faces(">Z").workplane().center(x, y).hole(5)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)