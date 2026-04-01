# ARIA-OS Fusion 360 Parametric
# Run: Utilities > Scripts and Add-Ins > Run Script
import adsk.core, adsk.fusion, traceback

OD_MM=100.0; HEIGHT_MM=50.0; BORE_MM=30.0
PART_NAME='aria_part'; STL_PATH=r'C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/llm_gopro_mount_adapter_prong_clip.stl'; STEP_PATH=r'C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/llm_gopro_mount_adapter_prong_clip.step'

def run(context):
    ui = None
    try:
        app    = adsk.core.Application.get(); ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root   = design.rootComponent
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0,0,0), OD_MM/20.0)
        ei = root.features.extrudeFeatures.createInput(
            sk.profiles.item(0),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(HEIGHT_MM/10.0))
        root.features.extrudeFeatures.add(ei).bodies.item(0).name = PART_NAME
        if BORE_MM > 0:
            sk2 = root.sketches.add(root.xYConstructionPlane)
            sk2.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(0,0,0), BORE_MM/20.0)
            ci = root.features.extrudeFeatures.createInput(
                sk2.profiles.item(0),
                adsk.fusion.FeatureOperations.CutFeatureOperation)
            ci.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)
            root.features.extrudeFeatures.add(ci)
        mgr = design.exportManager
        mgr.execute(mgr.createSTEPExportOptions(STEP_PATH))
        so = mgr.createSTLExportOptions(root); so.filename=STL_PATH; mgr.execute(so)
        ui.messageBox(f'{PART_NAME} done\nSTEP: {STEP_PATH}')
    except Exception:
        if ui: ui.messageBox('Fusion failed:\n' + traceback.format_exc())
