"""ARIA-OS orchestrator: load context -> plan -> generate -> validate -> export -> log."""
from pathlib import Path
from .context_loader import load_context
from .planner import plan as planner_plan
from .generator import generate as generator_generate, KNOWN_PART_IDS
from .validator import (
    validate,
    validate_housing_spec,
    validate_step_file,
    validate_mesh_integrity,
    check_feature_completeness,
)
from .exporter import export, get_output_paths, get_meta_path
from .logger import log as logger_log, log_failure as logger_log_failure
from . import cem_checks
from .cem_context import load_cem_geometry
from .cad_learner import record_attempt
from .tool_router import select_cad_tool, get_output_formats
from .fusion_generator import write_fusion_artifacts
from .grasshopper_generator import write_grasshopper_artifacts
from .blender_generator import write_blender_artifacts
from .cad_prompt_builder import attach_brief_to_plan


def run(goal: str, repo_root: Path | None = None, max_attempts: int = 3):
    """Run the full loop. On retry, passes previous code and error to generator (LLM can fix)."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    context = load_context(repo_root)
    session = {"goal": goal, "attempts": 0, "step_path": "", "stl_path": ""}
    last_error = ""
    last_code = ""

    # Plan + route once (unchanged across LLM retries)
    plan = planner_plan(goal, context, repo_root=repo_root)
    if not isinstance(plan, dict):
        plan = {"part_id": "aria_part", "text": str(plan), "build_order": [], "features": []}
    plan = attach_brief_to_plan(goal, plan, context, repo_root=repo_root)
    plan_text = plan.get("engineering_brief") or plan.get("text", str(plan))
    part_id = plan.get("part_id", "")
    cad_tool = plan.get("cad_tool_selected") or select_cad_tool(goal, plan)
    session["cad_tool"] = cad_tool
    session["cad_route"] = {
        "tool": cad_tool,
        "rationale": plan.get("cad_tool_rationale", ""),
    }
    session["engineering_brief"] = plan.get("engineering_brief", "")
    route_reason = plan.get("route_reason", "")
    force_llm = plan.get("force_llm", False) or bool(route_reason)
    use_llm = cad_tool == "cadquery" and (part_id not in KNOWN_PART_IDS or force_llm)
    expected_bbox = plan.get("expected_bbox") if isinstance(plan, dict) else None

    # Print route info ONCE
    print("\n" + "=" * 64)
    print("ARIA CAD ROUTE (tool + auto-built engineering prompt)")
    print("=" * 64)
    print(f"Pipeline: {cad_tool}")
    print(f"Why: {plan.get('cad_tool_rationale', '')}")
    if use_llm:
        if route_reason:
            print(f"[LLM] {route_reason}")
        elif part_id not in KNOWN_PART_IDS:
            print("[LLM] Unknown part -> LLM route")
        else:
            print("[LLM] Forced LLM route (overrides template)")
    else:
        if cad_tool == "cadquery":
            print(f"[TEMPLATE] CadQuery validated template: {part_id}")
        else:
            print(f"[AUTOMATION] Primary CAD: {cad_tool} (see outputs/cad/... scripts); placeholder solid for pipeline.")
    print("-" * 64)
    print(plan_text)
    print("=" * 64 + "\n")

    part_name = goal if use_llm else (part_id or goal)
    paths = get_output_paths(part_name, repo_root)
    step_path = Path(paths["step_path"])
    stl_path = Path(paths["stl_path"])

    # Non-CadQuery routes: no LLM retry loop
    if cad_tool != "cadquery":
        artifacts: dict[str, str] = {}
        if cad_tool == "fusion":
            artifacts = write_fusion_artifacts(plan if isinstance(plan, dict) else {}, goal, str(step_path), str(stl_path), repo_root=repo_root)
        elif cad_tool == "grasshopper":
            artifacts = write_grasshopper_artifacts(plan if isinstance(plan, dict) else {}, goal, str(step_path), str(stl_path), repo_root=repo_root)
        elif cad_tool == "blender":
            artifacts = write_blender_artifacts(plan if isinstance(plan, dict) else {}, goal, str(stl_path), repo_root=repo_root)

        try:
            import cadquery as cq
            from cadquery import exporters
            base = cq.Workplane("XY").box(20, 20, 20)
            out_formats = get_output_formats(cad_tool)
            if "step" in out_formats:
                step_path.parent.mkdir(parents=True, exist_ok=True)
                exporters.export(base, str(step_path), exporters.ExportTypes.STEP)
                session["step_path"] = str(step_path)
            if "stl" in out_formats:
                stl_path.parent.mkdir(parents=True, exist_ok=True)
                exporters.export(base, str(stl_path), exporters.ExportTypes.STL)
                session["stl_path"] = str(stl_path)
        except Exception as e:
            session["error"] = f"{cad_tool} routed export failed: {e}"
            logger_log_failure(session, session["error"])
            print("Diagnosis:", session["error"])
            return session

        session["automation_artifacts"] = artifacts
        session["attempts"] = 1
        record_attempt(
            goal=goal,
            plan_text=plan_text,
            part_id=part_id or "aria_part",
            code=f"# routed_tool={cad_tool}",
            passed=True,
            bbox={"x": 20.0, "y": 20.0, "z": 20.0},
            error=None,
            cem_snapshot=load_cem_geometry(repo_root),
            cem_passed=False,
            feature_complete=True,
            mesh_clean=True,
            bbox_within_2pct=False,
            tool_used=cad_tool,
            repo_root=repo_root,
        )
        logger_log(session)
        return session

    for attempt in range(1, max_attempts + 1):
        session["attempts"] = attempt

        try:
            code = generator_generate(
                plan, context,
                repo_root=repo_root,
                previous_code=last_code or None,
                previous_error=last_error or None,
                goal=goal,
            )
        except RuntimeError as e:
            last_error = str(e)
            print(f"Generation failed: {e}")
            continue
        last_code = code

        if use_llm:
            inject = {"STEP_PATH": str(step_path), "STL_PATH": str(stl_path), "PART_NAME": part_name}
            result = validate(code, expected_bbox=expected_bbox, inject_namespace=inject, min_step_size_kb=1.0)
        else:
            result = validate(code, expected_bbox=expected_bbox)

        bbox_dict = None
        bbox_within_2pct = False
        if result.bbox:
            bbox_dict = {"x": result.bbox[0], "y": result.bbox[1], "z": result.bbox[2]}
            if expected_bbox:
                ratios = []
                for got, exp in zip(result.bbox, expected_bbox):
                    if exp:
                        ratios.append(abs(got - exp) / abs(exp))
                bbox_within_2pct = bool(ratios) and all(r <= 0.02 for r in ratios)

        feature_complete, feature_error = check_feature_completeness(code, plan if isinstance(plan, dict) else {})
        if not feature_complete:
            result.passed = False
            last_error = feature_error

        cem_passed = False
        cem_summary = ""
        if not result.passed:
            record_attempt(
                goal=goal,
                plan_text=plan_text,
                part_id=part_id or "aria_part",
                code=code,
                passed=False,
                bbox=bbox_dict,
                error=last_error or result.error or "; ".join(result.errors) if result.errors else last_error,
                cem_snapshot=load_cem_geometry(repo_root),
                cem_passed=False,
                feature_complete=feature_complete,
                mesh_clean=False,
                bbox_within_2pct=bbox_within_2pct,
                tool_used=cad_tool,
                repo_root=repo_root,
            )
            last_error = result.error or "; ".join(result.errors)
            continue

        if "housing" in goal.lower() or "shell" in goal.lower():
            spec = {"width": 700.0, "height": 680.0, "depth": 344.0}
            validate_housing_spec(result, spec)
            if not result.passed:
                last_error = result.error
                record_attempt(
                    goal=goal,
                    plan_text=plan_text,
                    part_id=part_id or "aria_part",
                    code=code,
                    passed=False,
                    bbox=bbox_dict,
                    error=last_error,
                    cem_snapshot=load_cem_geometry(repo_root),
                    cem_passed=False,
                    feature_complete=feature_complete,
                    mesh_clean=False,
                    bbox_within_2pct=bbox_within_2pct,
                    tool_used=cad_tool,
                    repo_root=repo_root,
                )
                continue

        if use_llm:
            session["step_path"] = str(step_path)
            session["stl_path"] = str(stl_path)
        else:
            paths = export(result.geometry, part_id or goal, repo_root)
            session["step_path"] = paths["step_path"]
            session["stl_path"] = paths["stl_path"]

        # CEM integration: run physics checks using meta JSON if available
        try:
            meta_path_str = get_meta_path(part_id or part_name, repo_root)
            cem_result = cem_checks.run_cem_checks(part_id or part_name, Path(meta_path_str), context)
            session["cem_overall_passed"] = cem_result.overall_passed
            session["cem_summary"] = cem_result.summary
            cem_passed = bool(cem_result.overall_passed)
            cem_summary = cem_result.summary or ""
            if cem_result.static_min_sf is not None:
                session["cem_static_min_sf"] = cem_result.static_min_sf
            if not cem_result.overall_passed:
                print(f"[CEM FAIL] {cem_result.summary}")
                result.passed = False
                last_error = cem_result.summary
                record_attempt(
                    goal=goal,
                    plan_text=plan_text,
                    part_id=part_id or "aria_part",
                    code=code,
                    passed=False,
                    bbox=bbox_dict,
                    error=last_error,
                    cem_snapshot=load_cem_geometry(repo_root),
                    cem_passed=False,
                    feature_complete=feature_complete,
                    mesh_clean=False,
                    bbox_within_2pct=bbox_within_2pct,
                    tool_used=cad_tool,
                    repo_root=repo_root,
                )
                continue
            else:
                print(f"[CEM PASS] {cem_result.summary}")
        except Exception as e:
            # CEM is advisory; do not fail geometry run if integration fails
            session["cem_error"] = str(e)

        step_path_check = Path(session["step_path"])
        file_valid, solid_count, file_errors = validate_step_file(step_path_check, min_size_kb=1.0)
        if not file_valid and file_errors:
            if solid_count < 1:
                last_error = "; ".join(file_errors)
                continue
            session["validation_errors"] = file_errors

        # Mesh integrity check (STL) - advisory for print readiness
        try:
            stl_path_check = Path(session.get("stl_path", ""))
            mesh_clean = False
            if stl_path_check.exists():
                mesh = validate_mesh_integrity(str(stl_path_check))
                session["mesh_validation"] = mesh
                mesh_clean = int(mesh.get("degenerate_triangles", 0)) == 0
                if int(mesh.get("degenerate_triangles", 0)) > 0:
                    print(f"[MESH WARNING] {mesh.get('degenerate_triangles')} degenerate triangles found - do not print until geometry is fixed")
            record_attempt(
                goal=goal,
                plan_text=plan_text,
                part_id=part_id or "aria_part",
                code=code,
                passed=True,
                bbox=bbox_dict,
                error=None,
                cem_snapshot=load_cem_geometry(repo_root),
                cem_passed=cem_passed,
                feature_complete=feature_complete,
                mesh_clean=mesh_clean,
                bbox_within_2pct=bbox_within_2pct,
                tool_used=cad_tool,
                repo_root=repo_root,
            )
        except Exception as e:
            session["mesh_validation_error"] = str(e)
            record_attempt(
                goal=goal,
                plan_text=plan_text,
                part_id=part_id or "aria_part",
                code=code,
                passed=True,
                bbox=bbox_dict,
                error=None,
                cem_snapshot=load_cem_geometry(repo_root),
                cem_passed=cem_passed,
                feature_complete=feature_complete,
                mesh_clean=False,
                bbox_within_2pct=bbox_within_2pct,
                tool_used=cad_tool,
                repo_root=repo_root,
            )

        logger_log(session)
        return session

    logger_log_failure(session, last_error)
    print("Diagnosis:", last_error)
    return session
