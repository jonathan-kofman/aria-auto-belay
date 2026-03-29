"""
ARIA Arc Lattice Panel — Fusion 360 Python API script
Run: Utilities > Scripts and Add-Ins > Scripts > Add → select this file → Run

Geometry (all in mm; Fusion API uses cm internally):
  Panel:  120 × 70 × 8 mm
  Frame:  5 mm wall on all sides
  Interior: 110 × 60 mm
  Grid:   6 cols × 6 rows  → CELL_W=18.33mm, CELL_H=10mm
  CUT_DIA = 17.5mm (r=8.75mm)

  diagonal_dist = sqrt((CELL_W/2)² + CELL_H²)
                = sqrt(9.165² + 10²) = sqrt(84+100) = 13.56mm

  same-row gap      = CELL_W - CUT_DIA = 18.33 - 17.5 = 0.83mm  ← visible gap
  diagonal overlap  = CUT_DIA - diagonal_dist = 17.5 - 13.56 = 3.94mm ← clear X-struts

  strut half-width  = sqrt(r² - (diagonal_dist/2)²)
                    = sqrt(76.56 - 45.78) = sqrt(30.78) = 5.55mm

Brick-offset: odd rows shift right by CELL_W/2 for hex-close packing.
Partial circles at frame boundary are clipped by an interior mask body.
"""

import adsk.core
import adsk.fusion
import traceback
import math

# ---------------------------------------------------------------------------
# Parameters (mm)
# ---------------------------------------------------------------------------
W_MM,  H_MM,  T_MM   = 120.0, 70.0, 8.0
FRAME_MM               = 5.0
IW_MM  = W_MM  - 2 * FRAME_MM   # 110 mm
IH_MM  = H_MM  - 2 * FRAME_MM   #  60 mm

N_COLS, N_ROWS = 6, 6
CELL_W_MM = IW_MM / N_COLS        # 18.333 mm
CELL_H_MM = IH_MM / N_ROWS        # 10.0   mm
CUT_R_MM  = 17.5 / 2              # 8.75   mm  (diameter 17.5mm)

# Fusion 360 uses centimetres
_CM = 0.10   # mm → cm

W  = W_MM  * _CM;  H  = H_MM  * _CM;  T  = T_MM  * _CM
IW = IW_MM * _CM;  IH = IH_MM * _CM
CW = CELL_W_MM * _CM;  CH = CELL_H_MM * _CM
CR = CUT_R_MM  * _CM

# Tiny inset for interior mask so circle clips never erode frame
_INSET = 0.001   # 0.01 mm (in cm)


# ---------------------------------------------------------------------------
def run(context):
    ui = None
    try:
        app    = adsk.core.Application.get()
        ui     = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)

        # Force direct design — required for programmatic booleans
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent

        extrudes = root.features.extrudeFeatures
        combines = root.features.combineFeatures
        sketches = root.sketches
        xyPlane  = root.xYConstructionPlane

        # ------------------------------------------------------------------ #
        # 1 — Panel slab                                                       #
        # ------------------------------------------------------------------ #
        sk_panel = sketches.add(xyPlane)
        sk_panel.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(-W / 2, -H / 2, 0),
            adsk.core.Point3D.create( W / 2,  H / 2, 0),
        )
        prof = sk_panel.profiles.item(0)
        ei   = extrudes.createInput(
            prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(T))
        panel_feat = extrudes.add(ei)
        panel_body = panel_feat.bodies.item(0)
        panel_body.name = "arc_lattice_panel"

        # ------------------------------------------------------------------ #
        # 2 — Interior mask body (clips circle cuts to keep frame intact)      #
        # ------------------------------------------------------------------ #
        sk_mask = sketches.add(xyPlane)
        sk_mask.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(-IW / 2 + _INSET, -IH / 2 + _INSET, 0),
            adsk.core.Point3D.create( IW / 2 - _INSET,  IH / 2 - _INSET, 0),
        )
        prof_mask = sk_mask.profiles.item(0)
        ei_mask   = extrudes.createInput(
            prof_mask, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        # Extend above and below by 1mm so mask fully contains all cylinders
        ei_mask.setSymmetricExtent(
            adsk.core.ValueInput.createByReal(T / 2 + 0.1 * _CM), True)
        mask_feat = extrudes.add(ei_mask)
        mask_body = mask_feat.bodies.item(0)
        mask_body.name = "_interior_mask"

        # ------------------------------------------------------------------ #
        # 3 — Circle cuts (brick-offset grid, clipped to interior)             #
        # ------------------------------------------------------------------ #
        cut_count = 0
        for row in range(-1, N_ROWS + 1):
            cy    = -IH / 2 + (row + 0.5) * CH
            xoff  = (row % 2) * (CW / 2)

            for col in range(-1, N_COLS + 1):
                cx = -IW / 2 + (col + 0.5) * CW + xoff

                # Skip circles that don't intersect the interior at all
                if cx + CR <= -IW / 2 or cx - CR >= IW / 2:
                    continue
                if cy + CR <= -IH / 2 or cy - CR >= IH / 2:
                    continue

                # -- Cylinder body --
                sk_cyl = sketches.add(xyPlane)
                sk_cyl.sketchCurves.sketchCircles.addByCenterRadius(
                    adsk.core.Point3D.create(cx, cy, 0), CR
                )
                prof_cyl = sk_cyl.profiles.item(0)
                ei_cyl   = extrudes.createInput(
                    prof_cyl, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                ei_cyl.setSymmetricExtent(
                    adsk.core.ValueInput.createByReal(T / 2 + 0.1 * _CM), True)
                cyl_feat = extrudes.add(ei_cyl)
                cyl_body = cyl_feat.bodies.item(0)

                # -- Clip cylinder to interior mask --
                tools = adsk.core.ObjectCollection.create()
                tools.add(mask_body)
                ci = combines.createInput(cyl_body, tools)
                ci.operation        = adsk.fusion.FeatureOperations.IntersectFeatureOperation
                ci.isKeepToolBodies = True   # keep mask for next iteration
                combines.add(ci)
                # cyl_body is now the clipped cylinder

                # -- Cut clipped cylinder from panel --
                tools2 = adsk.core.ObjectCollection.create()
                tools2.add(cyl_body)
                ci2 = combines.createInput(panel_body, tools2)
                ci2.operation        = adsk.fusion.FeatureOperations.CutFeatureOperation
                ci2.isKeepToolBodies = False  # consume clipped cyl
                combines.add(ci2)

                cut_count += 1

        # ------------------------------------------------------------------ #
        # 4 — Remove mask body                                                 #
        # ------------------------------------------------------------------ #
        bodies_to_del = adsk.core.ObjectCollection.create()
        bodies_to_del.add(mask_body)
        root.features.removeFeatures.add(bodies_to_del)

        # ------------------------------------------------------------------ #
        # 5 — Export STEP + STL                                                #
        # ------------------------------------------------------------------ #
        step_path = r"C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/arc_lattice_panel.step"
        stl_path  = r"C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/arc_lattice_panel.stl"

        mgr = design.exportManager

        step_opts = mgr.createSTEPExportOptions(step_path)
        mgr.execute(step_opts)

        stl_opts = mgr.createSTLExportOptions(panel_body)
        stl_opts.filename     = stl_path
        stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
        mgr.execute(stl_opts)

        msg = (
            f"Arc lattice panel complete.\n"
            f"  Cuts applied: {cut_count}\n"
            f"  Grid: {N_COLS} cols × {N_ROWS} rows\n"
            f"  Cell: {CELL_W_MM:.1f} × {CELL_H_MM:.1f} mm\n"
            f"  Cut dia: {CUT_R_MM*2:.1f} mm\n"
            f"  Same-row gap: {CELL_W_MM - CUT_R_MM*2:.2f} mm\n"
            f"  Diagonal strut overlap: {CUT_R_MM*2 - math.sqrt((CW/2/0.1)**2+(CH/0.1)**2):.2f} mm\n"
            f"  STEP → {step_path}\n"
            f"  STL  → {stl_path}"
        )
        ui.messageBox(msg)

    except Exception:
        if ui:
            ui.messageBox("Error:\n" + traceback.format_exc())
