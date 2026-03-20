"""
Build the rich engineering prompt ARIA-OS sends to Claude (CadQuery path) and
summarize which CAD toolchain is selected (CadQuery vs Fusion vs Grasshopper vs Blender).

Users can type a short goal; this module expands it into a structured brief + routing rationale.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .cem_context import load_cem_geometry, format_cem_block
from .tool_router import select_cad_tool


def cad_tool_rationale(cad_tool: str, plan: dict[str, Any]) -> str:
    """Human-readable reason for the selected pipeline."""
    t = (cad_tool or "cadquery").lower()
    part_id = plan.get("part_id", "") or ""
    rr = plan.get("route_reason") or plan.get("cem_route_reason") or ""
    mapping = {
        "cadquery": (
            "Prismatic / boolean / hole features -> headless CadQuery in this repo; "
            "exports STEP + STL under outputs/cad/."
        ),
        "fusion": (
            "Lattice, volumetric infill, or CAM-heavy intent -> run the generated Fusion 360 API script "
            "under outputs/cad/fusion_scripts/ (Design Extension may be required for lattice)."
        ),
        "grasshopper": (
            "Helical / loft / sweep / freeform surface intent -> use Grasshopper + Rhino "
            "(rhino.compute) artifacts under outputs/cad/grasshopper/."
        ),
        "blender": (
            "Mesh cleanup / organic sculpt intent -> run the Blender background script "
            "under outputs/cad/blender/ (STL-focused)."
        ),
    }
    base = mapping.get(t, mapping["cadquery"])
    extras: list[str] = []
    if part_id:
        extras.append(f"part_id={part_id}")
    if rr:
        extras.append(rr)
    if extras:
        return base + " " + " | ".join(extras)
    return base


def build_engineering_brief(
    goal: str,
    plan: dict[str, Any],
    context: dict[str, str],
    *,
    repo_root: Optional[Path] = None,
    cad_tool: Optional[str] = None,
) -> str:
    """
    Full structured brief used as the primary user-facing generation prompt for Claude (CadQuery),
    and printed for other CAD routes so you see what the system inferred.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    tool = cad_tool if cad_tool else select_cad_tool(goal, plan)
    cem = plan.get("cem_context") if isinstance(plan.get("cem_context"), dict) else None
    if not cem:
        cem = load_cem_geometry(repo_root)
    cem_block = format_cem_block(cem if isinstance(cem, dict) else {})

    part_id = plan.get("part_id", "aria_part")
    material = plan.get("material", "")
    base_shape = plan.get("base_shape", {})
    features = plan.get("features", []) or []
    build_order = plan.get("build_order", []) or []

    lines = [
        "=== ARIA CAD GENERATION REQUEST (auto-expanded from your short goal) ===",
        "",
        "## 1) Your intent (verbatim)",
        goal.strip() or "(empty)",
        "",
        "## 2) Selected CAD pipeline",
        f"Primary tool: **{tool}**",
        cad_tool_rationale(tool, plan),
        "",
        "## 3) Part identity",
        f"- part_id: {part_id}",
        f"- material (if specified in plan): {material or 'use context / defaults'}",
        "",
        "## 4) Structured plan (from planner)",
        plan.get("text", str(plan)),
        "",
        "## 5) Base shape / dimensions (structured)",
        json.dumps(base_shape, indent=2) if base_shape else "(none)",
        "",
        "## 6) Planned features",
        json.dumps(features, indent=2) if features else "(none)",
        "",
        "## 7) Build order",
        "\n".join(f"  - {s}" for s in build_order) if build_order else "(none)",
        "",
        "## 8) CEM / physics-derived context (ground truth for sizes where applicable)",
        cem_block.rstrip(),
        "",
        "## 9) Instructions for the code generator",
        "Generate CadQuery Python that implements the part above. Prefer simple, robust solids:",
        "solid first, then cuts/holes; avoid fragile fillets/chamfers unless required.",
        "Honor dimensions in the plan and CEM block. End with STEP/STL export and META JSON as required.",
    ]

    if tool != "cadquery":
        lines.extend(
            [
                "",
                "## 10) Note on this route",
                "This run also writes tool-specific automation files; a small CadQuery placeholder solid "
                "may be exported so the pipeline always has STEP/STL paths. Refine geometry in the "
                f"primary tool ({tool}) using the generated scripts.",
            ]
        )

    return "\n".join(lines)


def attach_brief_to_plan(
    goal: str,
    plan: dict[str, Any],
    context: dict[str, str],
    *,
    repo_root: Optional[Path] = None,
    cad_tool: Optional[str] = None,
) -> dict[str, Any]:
    """Mutate plan in place with engineering_brief + selected cad_tool; return plan."""
    tool = cad_tool if cad_tool else select_cad_tool(goal, plan)
    plan["cad_tool_selected"] = tool
    plan["cad_tool_rationale"] = cad_tool_rationale(tool, plan)
    plan["engineering_brief"] = build_engineering_brief(
        goal, plan, context, repo_root=repo_root, cad_tool=tool
    )
    return plan
