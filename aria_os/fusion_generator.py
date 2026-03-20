"""
aria_os/fusion_generator.py
Generates a Fusion 360 Python API script users run inside Fusion.
"""
import json
from pathlib import Path
from typing import Any, Optional

from .cem_context import load_cem_geometry


def generate_fusion_script(
    plan: dict[str, Any],
    goal: str,
    step_path: str,
    stl_path: str,
    repo_root: Optional[Path] = None,
) -> str:
    cem = load_cem_geometry(repo_root)
    part_name = (goal or "aria_part")[:60]
    stl_path_escaped = stl_path.replace("\\", "/")

    housing_od = cem.get("output_housing_od_mm", 260.0)
    housing_length = cem.get("output_housing_length_mm", 200.0)
    is_lattice = any(kw in (goal or "").lower() for kw in ["lattice", "gyroid", "octet", "infill", "honeycomb", "energy absorber"])

    if is_lattice:
        return f'''"""
ARIA-OS Generated Fusion 360 Script — {part_name}
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

        HOUSING_OD_MM = {housing_od}
        HOUSING_LENGTH_MM = {housing_length}

        sketch = sketches.add(xyPlane)
        circles = sketch.sketchCurves.sketchCircles
        circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), HOUSING_OD_MM / 20.0)
        prof = sketch.profiles.item(0)
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(HOUSING_LENGTH_MM / 10.0))
        extrudes.add(extInput)

        exportMgr = design.exportManager
        stlOptions = exportMgr.createSTLExportOptions(rootComp)
        stlOptions.filename = "{stl_path_escaped}"
        exportMgr.execute(stlOptions)
        ui.messageBox("ARIA-OS: Export complete\\n{stl_path_escaped}")
    except:
        if ui:
            ui.messageBox("Fusion script failed:\\n" + traceback.format_exc())
'''

    return f'''"""
ARIA-OS Generated Fusion 360 Script — {part_name}
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
        ui.messageBox("ARIA-OS script generated for: {part_name}\\nExport targets:\\nSTEP: {step_path}\\nSTL: {stl_path}")
    except:
        if ui:
            ui.messageBox("Fusion script failed:\\n" + traceback.format_exc())
'''


def write_fusion_artifacts(
    plan: dict[str, Any],
    goal: str,
    step_path: str,
    stl_path: str,
    repo_root: Optional[Path] = None,
) -> dict[str, str]:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    part_slug = (plan.get("part_id") or "aria_part").replace("/", "_")
    out_dir = repo_root / "outputs" / "cad" / "fusion_scripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / f"{part_slug}.py"
    params_path = out_dir / f"{part_slug}.json"

    script = generate_fusion_script(plan, goal, step_path, stl_path, repo_root=repo_root)
    script_path.write_text(script, encoding="utf-8")
    params_path.write_text(
        json.dumps(
            {
                "goal": goal,
                "part_id": plan.get("part_id", ""),
                "step_path": step_path,
                "stl_path": stl_path,
                "features": plan.get("features", []),
                "base_shape": plan.get("base_shape", {}),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"script_path": str(script_path), "params_path": str(params_path)}
