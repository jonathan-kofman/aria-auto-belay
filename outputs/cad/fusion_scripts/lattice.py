"""
ARIA-OS Generated Fusion 360 Script — aria energy absorber lattice
Run in Fusion: Utilities > Scripts and Add-Ins > Run
"""
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent
        sketches = rootComp.sketches
        extrudes = rootComp.features.extrudeFeatures
        xyPlane = rootComp.xYConstructionPlane

        HOUSING_OD_MM = 260.0
        HOUSING_LENGTH_MM = 327.0

        sketch = sketches.add(xyPlane)
        circles = sketch.sketchCurves.sketchCircles
        circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), HOUSING_OD_MM / 20.0)
        prof = sketch.profiles.item(0)
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(HOUSING_LENGTH_MM / 10.0))
        extrudes.add(extInput)

        exportMgr = design.exportManager
        stlOptions = exportMgr.createSTLExportOptions(rootComp)
        stlOptions.filename = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/llm_lattice.stl"
        exportMgr.execute(stlOptions)
        ui.messageBox("ARIA-OS: Export complete\nC:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/llm_lattice.stl")
    except:
        if ui:
            ui.messageBox("Fusion script failed:\n" + traceback.format_exc())
