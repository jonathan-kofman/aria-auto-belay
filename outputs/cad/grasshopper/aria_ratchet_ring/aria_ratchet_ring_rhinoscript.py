import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import os
import math
import System

# === PART PARAMETERS (tunable) ===
OD_MM       = 213.0
BORE_MM     = 185.0
THICK_MM    = 21.0
N_TEETH     = 24
R_TIP       = 106.5
TOOTH_H     = 4.0
R_ROOT      = 102.5
DRIVE_Y     = 0.562
BACK_Y      = 6.928
ROOT_W      = 2.078
# === END PARAMETERS ===

# --- Annular ring body ---
outer_circle = rg.Circle(rg.Plane.WorldXY, OD_MM / 2.0)
outer_cyl    = rg.Cylinder(outer_circle, THICK_MM).ToBrep(True, True)
bore_circle  = rg.Circle(rg.Plane.WorldXY, BORE_MM / 2.0)
bore_cyl     = rg.Cylinder(bore_circle, THICK_MM * 1.01).ToBrep(True, True)
ring_body    = rg.Brep.CreateBooleanDifference([outer_cyl], [bore_cyl], 0.001)
result       = ring_body[0] if ring_body else outer_cyl

# --- Asymmetric tooth (drive ~8 deg, back ~60 deg) ---
tooth_pts = [
    rg.Point3d(R_ROOT,           -ROOT_W / 2.0, 0),
    rg.Point3d(R_TIP,            -DRIVE_Y / 2.0, 0),
    rg.Point3d(R_TIP,             DRIVE_Y / 2.0, 0),
    rg.Point3d(R_ROOT,            ROOT_W / 2.0 + BACK_Y, 0),
    rg.Point3d(R_ROOT,           -ROOT_W / 2.0, 0),
]
tooth_profile = rg.PolylineCurve(tooth_pts)
tooth_extr    = rg.Extrusion.Create(tooth_profile, THICK_MM, True)
tooth_brep    = tooth_extr.ToBrep() if tooth_extr else None

# --- Polar array + union ---
if tooth_brep:
    for i in range(N_TEETH):
        angle  = i * 2.0 * math.pi / N_TEETH
        xform  = rg.Transform.Rotation(angle, rg.Vector3d(0, 0, 1), rg.Point3d.Origin)
        t_copy = tooth_brep.DuplicateBrep()
        t_copy.Transform(xform)
        united = rg.Brep.CreateBooleanUnion([result, t_copy], 0.001)
        if united:
            result = united[0]

# === BBOX + EXPORT ===
bb = result.GetBoundingBox(True)
xlen = bb.Max.X - bb.Min.X
ylen = bb.Max.Y - bb.Min.Y
zlen = bb.Max.Z - bb.Min.Z
print("BBOX:{:.3f},{:.3f},{:.3f}".format(xlen, ylen, zlen))

STEP_PATH = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_ratchet_ring.step"
STL_PATH  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_ratchet_ring.stl"
try: os.makedirs(os.path.dirname(STEP_PATH) or '.')
except OSError: pass
try: os.makedirs(os.path.dirname(STL_PATH) or '.')
except OSError: pass
_obj_id = sc.doc.Objects.AddBrep(result)
sc.doc.Objects.Select(_obj_id)
rs.Command('_-Export "' + STEP_PATH + '" _Enter', False)
rs.Command('_-Export "' + STL_PATH  + '" _Enter _Enter', False)
print("STEP: " + STEP_PATH)
print("STL:  " + STL_PATH)

