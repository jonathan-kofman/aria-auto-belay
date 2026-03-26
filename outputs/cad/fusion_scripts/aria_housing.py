"""
ARIA-OS Generated Fusion 360 Script — ARIA motor housing shell, 260mm OD, 10mm wall, 180mm length
Standard parametric script stub.
"""
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        root = design.rootComponent
        ui.messageBox("ARIA-OS script generated for: ARIA motor housing shell, 260mm OD, 10mm wall, 180mm length\nExport targets:\nSTEP: /tmp/pytest-of-root/pytest-7/test_fusion_script_references_0/h.step\nSTL: /tmp/pytest-of-root/pytest-7/test_fusion_script_references_0/h.stl")
    except:
        if ui:
            ui.messageBox("Fusion script failed:\n" + traceback.format_exc())
