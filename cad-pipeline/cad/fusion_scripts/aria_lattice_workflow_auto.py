"""
ARIA Lattice Workflow (Fusion automation helper)

Automates the repetitive Fusion-side setup for lattice evaluation:
1) Switch to Direct Design mode.
2) Import generated STL lattice (from ARIA pipeline).
3) Build matching rectangular frame body as native BRep.
4) Position imported lattice at frame opening center.

Notes:
- This script does not require Design Extension APIs.
- It is intended to remove repetitive manual setup steps.
- STL stays as mesh by default (robust). Convert Mesh->BRep manually when needed.
"""

import adsk.core
import adsk.fusion
import traceback
from pathlib import Path


# ---- Default parameters (mm) ----
OUTER_W = 152.4
OUTER_H = 304.8
FRAME_T = 50.8
FRAME_DEPTH = 8.0
LATTICE_Z_OFFSET = 0.0

# Preferred generated lattice artifact (update if you use a different output name)
DEFAULT_STL = "outputs/cad/stl/arc_weave_7repeat_interlaced.stl"


def _largest_profile(sketch: adsk.fusion.Sketch) -> adsk.fusion.Profile:
    best = None
    best_a = -1.0
    for i in range(sketch.profiles.count):
        p = sketch.profiles.item(i)
        try:
            a = p.areaProperties().area
            if a > best_a:
                best_a = a
                best = p
        except Exception:
            pass
    return best


def _get_repo_root() -> Path:
    # Script file path: <repo>/cad/fusion_scripts/aria_lattice_workflow_auto.py
    # Repo root should be 2 levels up from this script.
    return Path(__file__).resolve().parents[2]


def _create_frame(root: adsk.fusion.Component, ui: adsk.core.UserInterface) -> adsk.fusion.BRepBody:
    feats = root.features
    NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
    POS = adsk.fusion.ExtentDirections.PositiveExtentDirection

    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = "ARIA_Lattice_Frame_Sketch"
    lines = sk.sketchCurves.sketchLines

    # Centered outer rectangle
    x0 = -OUTER_W / 2.0
    y0 = -OUTER_H / 2.0
    x1 = OUTER_W / 2.0
    y1 = OUTER_H / 2.0

    p = adsk.core.Point3D.create
    lines.addByTwoPoints(p(x0, y0, 0), p(x1, y0, 0))
    lines.addByTwoPoints(p(x1, y0, 0), p(x1, y1, 0))
    lines.addByTwoPoints(p(x1, y1, 0), p(x0, y1, 0))
    lines.addByTwoPoints(p(x0, y1, 0), p(x0, y0, 0))

    # Centered inner opening rectangle
    ix0 = x0 + FRAME_T
    iy0 = y0 + FRAME_T
    ix1 = x1 - FRAME_T
    iy1 = y1 - FRAME_T
    lines.addByTwoPoints(p(ix0, iy0, 0), p(ix1, iy0, 0))
    lines.addByTwoPoints(p(ix1, iy0, 0), p(ix1, iy1, 0))
    lines.addByTwoPoints(p(ix1, iy1, 0), p(ix0, iy1, 0))
    lines.addByTwoPoints(p(ix0, iy1, 0), p(ix0, iy0, 0))

    prof = _largest_profile(sk)
    if not prof:
        raise RuntimeError("Could not find frame profile.")

    # Build solid slab
    ext = feats.extrudeFeatures.createInput(prof, NEW)
    ext.setOneSideExtent(
        adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(FRAME_DEPTH)),
        POS,
    )
    slab = feats.extrudeFeatures.add(ext)
    body = slab.bodies.item(0)
    body.name = "ARIA_Frame_Body"

    # Cut inner opening through all
    sk_cut = root.sketches.add(root.xYConstructionPlane)
    sk_cut.name = "ARIA_Lattice_Opening_Cut"
    l2 = sk_cut.sketchCurves.sketchLines
    l2.addByTwoPoints(p(ix0, iy0, 0), p(ix1, iy0, 0))
    l2.addByTwoPoints(p(ix1, iy0, 0), p(ix1, iy1, 0))
    l2.addByTwoPoints(p(ix1, iy1, 0), p(ix0, iy1, 0))
    l2.addByTwoPoints(p(ix0, iy1, 0), p(ix0, iy0, 0))

    p_cut = _largest_profile(sk_cut)
    if p_cut:
        cut = feats.extrudeFeatures.createInput(p_cut, CUT)
        cut.setAllExtent(POS)
        try:
            cut.participantBodies = [body]
        except Exception:
            pass
        feats.extrudeFeatures.add(cut)

    ui.messageBox(
        f"Frame created.\n"
        f"Outer: {OUTER_W:.1f} x {OUTER_H:.1f} mm\n"
        f"Frame thickness: {FRAME_T:.1f} mm\n"
        f"Depth: {FRAME_DEPTH:.1f} mm"
    )
    return body


def _import_lattice_stl(app: adsk.core.Application, root: adsk.fusion.Component, ui: adsk.core.UserInterface) -> bool:
    repo_root = _get_repo_root()
    stl_path = (repo_root / DEFAULT_STL).resolve()
    if not stl_path.exists():
        ui.messageBox(
            "Lattice STL not found.\n\n"
            f"Expected:\n{stl_path}\n\n"
            "Generate one first with:\n"
            "python run_aria_os.py --lattice --pattern arc_weave --form volumetric "
            "--width 152.4 --height 304.8 --depth 8 --cell-size 7.25 --strut 1.6 "
            "--frame 50.8 --interlaced --weave-offset 0.9 --name arc_weave_7repeat_interlaced"
        )
        return False

    import_mgr = app.importManager
    opts = import_mgr.createSTLImportOptions(str(stl_path), root)
    opts.isViewFit = True
    import_mgr.importToTarget(opts, root)
    ui.messageBox(f"Imported lattice STL:\n{stl_path}")
    return True


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("Open a Fusion Design document first.")
            return

        # Use direct mode for robust script behavior
        if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            design.designType = adsk.fusion.DesignTypes.DirectDesignType

        root = design.rootComponent

        _import_lattice_stl(app, root, ui)
        _create_frame(root, ui)

        ui.messageBox(
            "ARIA lattice workflow automation done.\n\n"
            "Next suggested steps:\n"
            "1) Inspect -> Section Analysis\n"
            "2) Mesh workspace -> Convert Mesh (if BRep edits needed)\n"
            "3) Modify -> Combine (if joining with native bodies)"
        )

    except Exception:
        if ui:
            ui.messageBox("FAILED:\n" + traceback.format_exc())
