"""Run generated CadQuery code, parse BBOX output, compare to spec, check exported STEP."""
import re
import sys
from io import StringIO
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple


@dataclass
class ValidationResult:
    passed: bool
    geometry: Any  # CQ Workplane or Solid
    error: str = ""
    bbox: Optional[Tuple[float, float, float]] = None  # (dx, dy, dz) in mm
    bbox_match: bool = False
    file_valid: bool = False
    solid_count: int = 0
    errors: List[str] = field(default_factory=list)
    stdout_capture: str = ""


def check_feature_completeness(code: str, plan: dict) -> tuple[bool, str]:
    """
    Verify that required plan features are present in generated code.
    This is a heuristic string-based check to catch missing critical operations.
    """
    if not isinstance(plan, dict):
        return True, ""

    features = plan.get("features", []) or []
    code_lower = (code or "").lower()

    if plan.get("hollow"):
        if ".cut(" not in code_lower:
            return False, "missing: interior void cut for hollow part"

    for f in features:
        if not isinstance(f, dict):
            continue
        ftype = str(f.get("type", "")).lower()
        if ftype == "bore":
            if ".hole(" not in code_lower and ".cutblind(" not in code_lower:
                return False, "missing: bore operation (.hole or .cutBlind)"
        elif ftype == "slot":
            has_rect = ".rect(" in code_lower
            has_cut = ".cutblind(" in code_lower or ".cutthruall(" in code_lower
            if not (has_rect and has_cut):
                return False, "missing: slot operation (.rect with cut)"
        elif ftype == "bolt_circle":
            has_polar = ".polararray(" in code_lower
            has_loop_holes = ("for " in code_lower and ".hole(" in code_lower)
            if not (has_polar or has_loop_holes):
                return False, "missing: bolt circle hole pattern (polarArray or looped holes)"

    return True, ""

def validate_mesh_integrity(stl_path: str) -> dict:
    """
    Check STL for common mesh errors before printing.
    Uses numpy-stl if available, falls back to file size check.
    """
    try:
        import numpy as np
        from stl import mesh as stl_mesh

        m = stl_mesh.Mesh.from_file(stl_path)

        # Check for degenerate triangles (zero area)
        v0, v1, v2 = m.v0, m.v1, m.v2
        cross = np.cross(v1 - v0, v2 - v0)
        areas = np.sqrt((cross**2).sum(axis=1))
        degenerate_count = int((areas < 1e-10).sum())

        # Rough disconnected-body indicator: unique vertex count at 0.001mm rounding
        all_verts = np.vstack([v0, v1, v2])
        unique_verts = np.unique(np.round(all_verts, 3), axis=0)

        return {
            "valid": degenerate_count == 0,
            "triangle_count": int(len(m.vectors)),
            "degenerate_triangles": int(degenerate_count),
            "unique_vertices": int(len(unique_verts)),
            "print_ready": degenerate_count == 0,
        }
    except ImportError:
        size = Path(stl_path).stat().st_size if Path(stl_path).exists() else 0
        return {
            "valid": size > 10000,
            "print_ready": size > 10000,
            "note": "install numpy-stl for full validation",
        }


def validate(code: str, expected_bbox: Optional[Tuple[float, float, float]] = None,
             step_path: Optional[Path] = None, min_step_size_kb: float = 50.0,
             inject_namespace: Optional[dict] = None) -> ValidationResult:
    """
    Execute code, capture stdout, parse BBOX line, check result and optional file.
    inject_namespace: dict merged into exec namespace (e.g. STEP_PATH, STL_PATH for LLM-generated code).
    """
    out = StringIO()
    err = StringIO()
    namespace = dict(inject_namespace or {})
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = out, err
        exec(code, namespace)
    except Exception as e:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        return ValidationResult(
            passed=False, geometry=None, error=str(e),
            errors=[str(e)], stdout_capture=out.getvalue())
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

    stdout_capture = out.getvalue()
    result = namespace.get("result")
    if result is None:
        return ValidationResult(
            passed=False, geometry=None, error="Code did not define 'result'",
            errors=["No 'result' defined"], stdout_capture=stdout_capture)

    # Parse BBOX from printed output
    bbox = None
    m = re.search(r"BBOX:([\d.]+),([\d.]+),([\d.]+)", stdout_capture)
    if m:
        bbox = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    if bbox is None:
        try:
            import cadquery as cq
            solid = result.val() if hasattr(result, "val") else result
            if hasattr(solid, "BoundingBox"):
                bb = solid.BoundingBox()
                bbox = (bb.xlen, bb.ylen, bb.zlen)
        except Exception as e:
            pass

    errors: List[str] = []
    bbox_match = True
    if expected_bbox and bbox:
        tol = 0.5
        for i, (a, b) in enumerate(zip(bbox, expected_bbox)):
            if abs(a - b) > tol:
                bbox_match = False
                errors.append(f"Bbox axis {i}: got {a:.2f}, expected {b:.2f} ±{tol}")
    elif expected_bbox and not bbox:
        bbox_match = False
        errors.append("No BBOX parsed from stdout and could not compute from geometry")

    file_valid = False
    solid_count = 0
    if step_path and Path(step_path).exists():
        size_kb = Path(step_path).stat().st_size / 1024
        if size_kb < min_step_size_kb:
            errors.append(f"STEP file too small: {size_kb:.1f} KB (min {min_step_size_kb} KB)")
        try:
            import cadquery as cq
            imported = cq.importers.importStep(str(step_path))
            vals = imported.solids().vals() if hasattr(imported, "solids") else []
            solid_count = len(vals) if vals else (1 if imported.val() else 0)
            if solid_count >= 1:
                file_valid = True
            else:
                errors.append("Re-imported STEP has no solids")
        except Exception as e:
            errors.append(f"STEP re-import failed: {e}")
    elif step_path and not Path(step_path).exists():
        errors.append(f"STEP file not found: {step_path}")
    else:
        file_valid = True  # No file to check

    passed = bbox_match and len(errors) == 0
    if expected_bbox and not bbox_match:
        passed = False
    if step_path:
        if not file_valid or solid_count < 1:
            passed = False

    return ValidationResult(
        passed=passed,
        geometry=result,
        error="; ".join(errors) if errors else "",
        bbox=bbox,
        bbox_match=bbox_match,
        file_valid=file_valid if step_path else True,
        solid_count=solid_count,
        errors=errors,
        stdout_capture=stdout_capture,
    )


def validate_housing_spec(result: ValidationResult, spec: dict) -> ValidationResult:
    """Check housing bbox 700x680x344 ±0.5 mm. Mutates result.passed and result.errors."""
    if result.bbox is None:
        result.passed = False
        result.errors.append("No bounding box")
        result.error = result.error or "No bounding box"
        return result
    dx, dy, dz = result.bbox
    w = spec.get("width", 700)
    h = spec.get("height", 680)
    d = spec.get("depth", 344)
    tol = 0.5
    if abs(dx - w) > tol or abs(dy - h) > tol or abs(dz - d) > tol:
        result.passed = False
        result.errors.append(f"Bbox {dx:.2f}x{dy:.2f}x{dz:.2f} mm, expected {w}x{h}x{d} ±{tol} mm")
        result.error = result.errors[-1]
    return result


def validate_step_file(step_path: Path, min_size_kb: float = 10.0) -> Tuple[bool, int, List[str]]:
    """Check STEP file: size >= min_size_kb and re-import has >= 1 solid. Returns (file_valid, solid_count, errors)."""
    errors: List[str] = []
    if not Path(step_path).exists():
        return False, 0, [f"STEP file not found: {step_path}"]
    size_kb = Path(step_path).stat().st_size / 1024
    if size_kb < min_size_kb:
        errors.append(f"STEP file too small: {size_kb:.1f} KB (min {min_size_kb} KB)")
    try:
        import cadquery as cq
        imported = cq.importers.importStep(str(step_path))
        vals = imported.solids().vals() if hasattr(imported, "solids") else []
        solid_count = len(vals) if vals else (1 if imported.val() else 0)
        if solid_count < 1:
            errors.append("Re-imported STEP has no solids")
        return (len(errors) == 0 and solid_count >= 1), solid_count, errors
    except Exception as e:
        errors.append(f"STEP re-import failed: {e}")
        return False, 0, errors
