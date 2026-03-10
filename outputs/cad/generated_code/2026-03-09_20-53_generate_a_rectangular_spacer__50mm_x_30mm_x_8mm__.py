import cadquery as cq
from cadquery import exporters

result = (cq.Workplane("XY")
    .box(50, 30, 8)
    .faces(">Z")
    .workplane()
    .hole(10)
)

bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")
exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
exporters.export(result, STL_PATH, exporters.ExportTypes.STL)