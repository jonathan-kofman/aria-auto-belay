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

Every generated script MUST end with these exact lines (STEP_PATH and STL_PATH are injected at runtime):
  bb = result.val().BoundingBox()
  print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
  exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)
  exporters.export(result, STL_PATH, exporters.ExportTypes.STL)

The variable 'result' must be the final Workplane or solid. Do not define STEP_PATH or STL_PATH; they are provided."""


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
