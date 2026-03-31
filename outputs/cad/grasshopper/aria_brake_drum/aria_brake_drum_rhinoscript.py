import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import os
import math
import System

# === PART PARAMETERS (tunable) ===
OD_MM        = 200.0
WIDTH_MM     = 40.0
SHAFT_DIA_MM = 20.0
WALL_MM      = 8.0
# === END PARAMETERS ===

# --- Outer cylinder (full solid to start) ---
outer_cyl = rg.Cylinder(rg.Circle(rg.Plane.WorldXY, OD_MM / 2.0),
                        WIDTH_MM).ToBrep(True, True)

# --- Inner void: open at top (z=WIDTH_MM), floor at z=0 ---
inner_plane  = rg.Plane(rg.Point3d(0, 0, WALL_MM), rg.Vector3d(0, 0, 1))
inner_cyl    = rg.Cylinder(
    rg.Circle(inner_plane, OD_MM / 2.0 - WALL_MM),
    WIDTH_MM - WALL_MM + 1.0).ToBrep(True, False)
hollow = rg.Brep.CreateBooleanDifference([outer_cyl], [inner_cyl], 0.001)
if hollow is None or len(hollow) == 0:
    raise RuntimeError('Brake drum: hollow boolean failed')
result = hollow[0]

# --- Shaft bore through closed bottom ---
shaft_plane = rg.Plane(rg.Point3d(0, 0, -1), rg.Vector3d(0, 0, 1))
shaft_cyl   = rg.Cylinder(
    rg.Circle(shaft_plane, SHAFT_DIA_MM / 2.0),
    WALL_MM + 2.0).ToBrep(True, True)
cut = rg.Brep.CreateBooleanDifference([result], [shaft_cyl], 0.001)
if cut is None or len(cut) == 0:
    raise RuntimeError('Brake drum: shaft bore boolean failed')
result = cut[0]

# === BBOX + EXPORT ===
bb = result.GetBoundingBox(True)
xlen = bb.Max.X - bb.Min.X
ylen = bb.Max.Y - bb.Min.Y
zlen = bb.Max.Z - bb.Min.Z
print("BBOX:{:.3f},{:.3f},{:.3f}".format(xlen, ylen, zlen))

STEP_PATH = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_brake_drum.step"
STL_PATH  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_brake_drum.stl"
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

