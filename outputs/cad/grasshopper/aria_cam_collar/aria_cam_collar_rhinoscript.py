import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import os
import math
import System

# === PART PARAMETERS (tunable) ===
OD_MM            = 80.0
BORE_MM          = 60.0
HEIGHT_MM        = 20.0
RAMP_HEIGHT_MM   = 4.0
SET_SCREW_DIA_MM = 4.0
# === END PARAMETERS ===

# --- Outer cylinder ---
outer_circle = rg.Circle(rg.Plane.WorldXY, OD_MM / 2.0)
outer_cyl    = rg.Cylinder(outer_circle, HEIGHT_MM).ToBrep(True, True)

# --- Bore ---
bore_circle = rg.Circle(rg.Plane.WorldXY, BORE_MM / 2.0)
bore_cyl    = rg.Cylinder(bore_circle, HEIGHT_MM * 1.1).ToBrep(True, True)
hollowed    = rg.Brep.CreateBooleanDifference([outer_cyl], [bore_cyl], 0.001)
result      = hollowed[0] if hollowed else outer_cyl

# --- Helical ramp (90-deg sweep on top face) ---
if RAMP_HEIGHT_MM > 0:
    r_inner = BORE_MM / 2.0 + 1.0
    r_outer = OD_MM  / 2.0
    pts = [
        rg.Point3d(r_inner, 0, HEIGHT_MM - RAMP_HEIGHT_MM),
        rg.Point3d(r_outer, 0, HEIGHT_MM - RAMP_HEIGHT_MM),
        rg.Point3d(r_outer, 0, HEIGHT_MM),
        rg.Point3d(r_inner, 0, HEIGHT_MM),
        rg.Point3d(r_inner, 0, HEIGHT_MM - RAMP_HEIGHT_MM),
    ]
    profile    = rg.PolylineCurve(pts)
    axis       = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, 1))
    rev_srf    = rg.RevSurface.Create(profile, axis, 0, math.pi / 2.0)
    if rev_srf:
        ramp_brep = rg.Brep.CreateFromRevSurface(rev_srf, True, True)
        if ramp_brep:
            cut = rg.Brep.CreateBooleanDifference([result], [ramp_brep], 0.001)
            if cut:
                result = cut[0]

# --- Set screw (radial) ---
if SET_SCREW_DIA_MM > 0:
    ss_origin = rg.Point3d(OD_MM / 2.0, 0, HEIGHT_MM / 2.0)
    ss_plane  = rg.Plane(ss_origin, rg.Vector3d(1, 0, 0))
    ss_circle = rg.Circle(ss_plane, SET_SCREW_DIA_MM / 2.0)
    ss_cyl    = rg.Cylinder(ss_circle, OD_MM * 0.6).ToBrep(True, True)
    cut2 = rg.Brep.CreateBooleanDifference([result], [ss_cyl], 0.001)
    if cut2:
        result = cut2[0]

# === BBOX + EXPORT ===
bb = result.GetBoundingBox(True)
xlen = bb.Max.X - bb.Min.X
ylen = bb.Max.Y - bb.Min.Y
zlen = bb.Max.Z - bb.Min.Z
print("BBOX:{:.3f},{:.3f},{:.3f}".format(xlen, ylen, zlen))

STEP_PATH = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_cam_collar.step"
STL_PATH  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_cam_collar.stl"
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

