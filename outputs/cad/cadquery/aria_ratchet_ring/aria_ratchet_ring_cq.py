
import cadquery as cq, math

# === ARIA Ratchet Ring — external teeth, asymmetric profile ===
# Teeth project outward from root circle to OD tip circle.
# Drive face  8° from radial  → self-locking (pawl cannot override on load)
# Back face  60° from radial  → shallow ramp (pawl slides over on forward spin)
# Bore = 120 mm  → fits spool hub OD
# Face width = 20 mm centred in 21 mm thickness (0.5 mm shoulder each side)

OD_MM        = 213.0          # tip circle diameter
BORE_MM      = 120.2        # spool hub fit
THICK_MM     = 21.0
N_TEETH      = 24
R_TIP        = OD_MM / 2.0            # 106.5 mm
R_ROOT       = 97.185               # root circle radius
TOOTH_H      = 9.315              # tip - root
FACE_W       = 20.0                   # axial tooth face (from aria_mechanical.md)
DRIVE_DEG    = 8.0
BACK_DEG     = 60.0
Z_OFF        = (THICK_MM - FACE_W) / 2.0   # 0.5 mm shoulder

# --- base ring: bore to root circle ---
base = (
    cq.Workplane("XY")
    .circle(R_ROOT)
    .circle(BORE_MM / 2.0)
    .extrude(THICK_MM)
)

# --- add 24 asymmetric teeth ---
d_drive = TOOTH_H * math.tan(math.radians(DRIVE_DEG))
d_back  = TOOTH_H * math.tan(math.radians(BACK_DEG))

for i in range(N_TEETH):
    a = math.radians(i * 360.0 / N_TEETH)
    ca, sa = math.cos(a), math.sin(a)

    def g(r, t):   # local radial/tangential → global XY
        return (r*ca - t*sa, r*sa + t*ca)

    p_back  = g(R_ROOT, -d_back)
    p_drive = g(R_ROOT,  d_drive)
    p_tip   = g(R_TIP,   0.0)

    tooth = (
        cq.Workplane("XY")
        .workplane(offset=Z_OFF)
        .polyline([p_back, p_tip, p_drive])
        .close()
        .extrude(FACE_W)
    )
    try:
        base = base.union(tooth)
    except Exception:
        pass

result = base
bb = result.val().BoundingBox()
print(f"BBOX:{bb.xlen:.3f},{bb.ylen:.3f},{bb.zlen:.3f}")

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_ratchet_ring_preview.step"
_stl  = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_ratchet_ring_preview.stl"
try:
    _os.makedirs(_os.path.dirname(_step), exist_ok=True)
except OSError:
    pass
try:
    _os.makedirs(_os.path.dirname(_stl), exist_ok=True)
except OSError:
    pass
_exp.export(result, _step, _exp.ExportTypes.STEP)
_exp.export(result, _stl,  _exp.ExportTypes.STL)
print(f"EXPORTED STEP: {_step}")
print(f"EXPORTED STL: {_stl}")
