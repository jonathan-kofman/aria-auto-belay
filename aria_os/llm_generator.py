"""
LLM-based CadQuery code generator for arbitrary parts.
Calls Anthropic API; builds system/user prompts from plan + context.
"""
import os
import re
from pathlib import Path
from typing import Any, Optional

from .context_loader import get_mechanical_constants, load_context


def _get_api_key(repo_root: Optional[Path] = None) -> str:
    """Get ANTHROPIC_API_KEY from os.environ or .env in repo root."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "ANTHROPIC_API_KEY":
                        return v.strip().strip('"').strip("'")
        except Exception:
            pass
    raise RuntimeError(
        "Set ANTHROPIC_API_KEY in environment or in a .env file in the repo root. "
        "See .env.example for format."
    )


def _build_system_prompt(context: dict[str, str]) -> str:
    """Build system prompt: CadQuery expert, constants, failures, patterns, required ending."""
    constants = get_mechanical_constants(context)
    constants_block = "\n".join(f"#   {k}: {v}" for k, v in sorted(constants.items()))
    failures_raw = context.get("aria_failures", "")
    # Summarize failure patterns (avoid these)
    avoid = """
- Never use annular/donut profile for initial extrusion. Solid first, then cut interior.
- Always work on EXISTING FACE of the body: .faces(">Z").workplane(), not new planes.
- Do not reference faces by index (e.g. faces[0]); use direction: faces(">Z"), faces("<Z").
- Ensure base solid is built and valid before any cut or hole.
- NEVER apply .chamfer() and .fillet() to the same part in sequence without selecting specific edges — use edge selectors.
- Apply chamfer BEFORE fillet, never after.
- For end chamfers use: .faces(">X").chamfer(depth) not .edges().chamfer()
- For selective edges: .edges("|Z").fillet(r) for vertical edges only.
- After adding raised features (bosses, shoulders, rings), the original face selector may point to the raised feature face, not the base plate. Always add holes BEFORE raised features, or use explicit workplane construction.

- NEVER use .union() on a bare Workplane() object.
  Union must always be: existing_result = existing_result.union(new_shape)
  where existing_result already has a solid on the stack.

- NEVER use the same angle for both drive face and back face
  of an asymmetric tooth. The asymmetry is the entire purpose
  of the ratchet profile — drive face must be nearly radial
  (8 deg) and back face must be gradual (60 deg).

  Correct tooth pattern for circular arrays:
    # Build ring body first
    result = (cq.Workplane("XY")
        .cylinder(HEIGHT_MM, OD_MM/2)
        .cylinder(HEIGHT_MM, ID_MM/2, combine="cut"))

    # Build ONE tooth as a separate solid
    tooth_base = (cq.Workplane("XY")
        ... tooth profile geometry ...
        .extrude(HEIGHT_MM))

    # Pattern the tooth using rotate + union in a loop
    import math
    for i in range(N_TEETH):
        angle = i * 360.0 / N_TEETH
        rotated = tooth_base.rotate((0,0,0),(0,0,1), angle)
        result = result.union(rotated)

  Never do:
    cq.Workplane("XY").union(tooth_base)  # WRONG - empty stack
    result.union(cq.Workplane("XY").box(...))  # WRONG - union with workplane not solid
"""
    return f"""You are a CadQuery expert. Output ONLY a Python code block. No explanation, no markdown outside the block.

Imports (use exactly):
  import cadquery as cq
  from cadquery import exporters

Rules:
- Always start from cq.Workplane("XY").
- Build order: base shape first, then shell/hollow, then additive features, then subtractive cuts last.
- All dimensions in mm.

Mechanical constants (from aria_mechanical.md) — use these when relevant:
{constants_block}

Avoid these patterns (from aria_failures.md):
{avoid}
- NEVER union a cylinder to create a rounded end — use a 2D profile with .threePointArc() instead.

Required code structure:

  ## REQUIRED: All numeric dimensions must be module-level constants

  EVERY dimension that appears in the geometry must be declared as
  a module-level ALL_CAPS constant BEFORE it is used.
  This is mandatory — the optimizer cannot tune inline literals.

  Required format:
    # === PART PARAMETERS (tunable) ===
    LENGTH_MM = 60.0       # overall length
    WIDTH_MM = 12.0        # overall width
    THICKNESS_MM = 6.0     # overall thickness
    PIVOT_HOLE_DIA_MM = 6.0
    PIVOT_OFFSET_MM = 22.0
    NOSE_RADIUS_MM = 6.0
    FILLET_MM = 0.5
    # === END PARAMETERS ===

    # geometry uses constants only, never inline numbers
    result = cq.Workplane("XY").box(LENGTH_MM, WIDTH_MM, THICKNESS_MM)

  Inline numbers that are NOT dimensions (like 0 for centering,
  360 for full circle, number of holes) are allowed inline.

  Every dimension from the part description must have its own constant.
  Group them all at the top under the "PART PARAMETERS" comment block.

Common CadQuery patterns:
  Box:      cq.Workplane("XY").box(length, width, height)
  Cylinder: cq.Workplane("XY").cylinder(height, radius)   # radius in mm
  Hollow:   build solid then .cut(inner_solid) or cut inner volume
  Hole:     .faces(">Z").workplane().center(x,y).hole(diameter)   # through
  Blind:    .faces(">Z").workplane().center(x,y).circle(radius).cutBlind(-depth)
  Slot:     .faces(">Z").workplane().center(x,y).rect(length, width).cutBlind(-depth) or .cutThruAll()
  Fillet:   .edges("|Z").fillet(radius)
  Bolt circle: use .faces(">Z").workplane() then .polarArray(radius, count) or place holes at (r*cos(a), r*sin(a)) for a in angles
  Rounded end tip (correct way): use a 2D profile with semicircle at one end via .threePointArc(), do NOT union a cylinder:
    result = (cq.Workplane("XY")
        .moveTo(0, -w/2)
        .lineTo(L-r, -w/2)
        .threePointArc((L, 0), (L-r, w/2))
        .lineTo(0, w/2)
        .close()
        .extrude(thickness))
  Chamfer on end face (correct): chamfer BEFORE fillet, use face selectors for chamfer:
    result = (cq.Workplane("XY")
        .box(L, W, H)
        .faces(">X").chamfer(depth)   # chamfer +X end
        .faces("<X").chamfer(depth)   # chamfer -X end
        .edges("|Z").fillet(r))       # fillet only vertical edges
  Holes on plate with raised boss (correct order): add ALL holes BEFORE raised features:
    result = (cq.Workplane("XY")
        .cylinder(H, OD/2)            # base cylinder
        .faces(">Z").workplane()
        .hole(bore_dia)               # center bore FIRST
        .faces(">Z").workplane()
        .polarArray(bcd/2, 0, 360, n_holes)
        .hole(hole_dia))              # bolt holes SECOND
    # Add shoulder LAST — after all holes
    shoulder = (cq.Workplane("XY")
        .cylinder(shoulder_H, shoulder_OD/2)
        .faces(">Z").workplane().hole(bore_dia))
    result = result.union(shoulder)

  Asymmetric ratchet tooth (correct implementation):

    # Tooth at angle 0, extending outward from ring
    # drive_face_angle = 8 deg from radial (steep face)
    # back_face_angle = 60 deg from radial (gradual face)
    import math
    root_r = OUTER_DIAMETER_MM / 2
    tip_r = root_r + TOOTH_HEIGHT_MM

    drive_rad = math.radians(DRIVE_ANGLE_DEG)
    back_rad = math.radians(BACK_ANGLE_DEG)

    # Tooth tip width creates angular offset at tip
    tip_half_angle = math.atan2(TOOTH_TIP_WIDTH_MM/2, tip_r)

    # Drive face (steep, 8 deg): nearly radial
    drive_root_angle = 0.0
    drive_root = (root_r * math.cos(drive_root_angle),
                  root_r * math.sin(drive_root_angle))

    # Drive face tip point: offset by tip flat half-angle (near radial)
    drive_tip_angle = drive_root_angle + tip_half_angle
    drive_tip = (tip_r * math.cos(drive_tip_angle),
                 tip_r * math.sin(drive_tip_angle))

    # Back face (gradual, 60 deg from radial)
    back_angular_width = (TOOTH_HEIGHT_MM * math.tan(back_rad)) / root_r
    back_root_angle = drive_root_angle - back_angular_width
    back_root = (root_r * math.cos(back_root_angle),
                 root_r * math.sin(back_root_angle))

    # Back face tip: other side of tip flat
    back_tip_angle = drive_tip_angle - 2 * tip_half_angle
    back_tip = (tip_r * math.cos(back_tip_angle),
                tip_r * math.sin(back_tip_angle))

    # Build tooth profile from these 4 points (asymmetric)
    tooth_profile = (cq.Workplane("XY")
        .moveTo(*back_root)
        .lineTo(*back_tip)
        .lineTo(*drive_tip)
        .lineTo(*drive_root)
        .close()
        .extrude(THICKNESS_MM))

    # Then rotate+union loop as before:
    # for i in range(N_TEETH):
    #   angle = i*360.0/N_TEETH
    #   result = result.union(tooth_profile.rotate((0,0,0),(0,0,1), angle))

Every generated script MUST end with these exact lines (STEP_PATH, STL_PATH and PART_NAME are injected at runtime):
  bb = result.val().BoundingBox()
  print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
  exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
  exporters.export(result, STL_PATH, exporters.ExportTypes.STL)

  # === META JSON (required for optimizer and CEM) ===
  import json as _json, pathlib as _pathlib
  _meta = {{
      "part_name": PART_NAME,
      "bbox_mm": {{"x": round(bb.xlen, 3), "y": round(bb.ylen, 3), "z": round(bb.zlen, 3)}},
      "dims_mm": {{}}
  }}
  # Collect all _MM constants automatically
  import sys as _sys
  _frame_vars = {{k: v for k, v in globals().items() if k.endswith('_MM') and isinstance(v, (int, float))}}
  _meta["dims_mm"] = _frame_vars
  _json_path = _pathlib.Path(STEP_PATH).parent.parent / "meta" / (_pathlib.Path(STEP_PATH).stem + ".json")
  _json_path.parent.mkdir(parents=True, exist_ok=True)
  _json_path.write_text(_json.dumps(_meta, indent=2))
  print(f\"META:{{_json_path}}\")

The variable 'result' must be the final Workplane or solid. Do not define STEP_PATH, STL_PATH or PARTNAME; they are provided."""


def _build_user_prompt(
    plan: dict[str, Any],
    previous_code: Optional[str] = None,
    previous_error: Optional[str] = None,
) -> str:
    """Build user prompt from plan dict; optionally include previous attempt and error."""
    lines = [
        "Plan (structured):",
        plan.get("text", str(plan)),
        "",
        "Build order:",
    ]
    for s in plan.get("build_order", []):
        lines.append(f"  - {s}")
    lines.append("")
    lines.append("Generate CadQuery Python for this part. Output code only.")
    if previous_error and previous_code:
        lines.append("")
        lines.append(f"Previous attempt failed with: {previous_error}")
        lines.append("Previous code was:")
        lines.append("```")
        lines.append(previous_code[:4000] if len(previous_code) > 4000 else previous_code)
        lines.append("```")
        lines.append("Fix the specific issue and regenerate.")
    return "\n".join(lines)


def _extract_code(response: str) -> Optional[str]:
    """Extract Python code from ```python ... ``` or full response."""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL)
    if m:
        return m.group(1).strip()
    if "import cadquery" in response or "cq.Workplane" in response:
        return response.strip()
    return None


def generate(
    plan: dict[str, Any],
    context: dict[str, str],
    repo_root: Optional[Path] = None,
    previous_code: Optional[str] = None,
    previous_error: Optional[str] = None,
) -> str:
    """
    Call Anthropic API to generate CadQuery code. Returns code string.
    Raises on API error or if no code could be extracted.
    """
    api_key = _get_api_key(repo_root)
    system = _build_system_prompt(context)
    user = _build_user_prompt(plan, previous_code, previous_error)

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package required for LLM generation. Install with: pip install anthropic"
        ) from None

    client = anthropic.Anthropic(api_key=api_key)
    # Use latest Claude model; fallback to claude-sonnet-4-5 or similar
    model = "claude-sonnet-4-20250514"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as e:
        if "claude-sonnet-4-20250514" in str(e) or "model" in str(e).lower():
            model = "claude-3-5-sonnet-20241022"
            msg = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        else:
            raise
    text = ""
    for b in msg.content:
        if hasattr(b, "text"):
            text += b.text
    code = _extract_code(text)
    if not code:
        raise RuntimeError("LLM did not return valid CadQuery code. No code block or cadquery import found.")
    return code


def save_generated_code(code: str, part_name: str, repo_root: Optional[Path] = None) -> Path:
    """Save generated code to outputs/cad/generated_code/YYYY-MM-DD_HH-MM_partname.py"""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    from datetime import datetime
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M")
    safe_name = re.sub(r"[^\w\-]", "_", part_name)[:50]
    dir_path = repo_root / "outputs" / "cad" / "generated_code"
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{stamp}_{safe_name}.py"
    path.write_text(code, encoding="utf-8")
    return path
