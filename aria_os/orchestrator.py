"""ARIA-OS orchestrator: load context -> plan -> generate -> validate -> export -> log."""
from pathlib import Path
from .context_loader import load_context
from .planner import plan as planner_plan
from .generator import generate as generator_generate, KNOWN_PART_IDS
from .validator import validate, validate_housing_spec, validate_step_file, validate_mesh_integrity, ValidationResult
from .exporter import export, get_output_paths, get_meta_path
from .logger import log as logger_log, log_failure as logger_log_failure
from . import cem_checks


def run(goal: str, repo_root: Path | None = None, max_attempts: int = 3):
    """Run the full loop. On retry, passes previous code and error to generator (LLM can fix)."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    context = load_context(repo_root)
    session = {"goal": goal, "attempts": 0, "step_path": "", "stl_path": ""}
    last_error = ""
    last_code = ""

    for attempt in range(1, max_attempts + 1):
        session["attempts"] = attempt
        plan = planner_plan(goal, context)
        plan_text = plan.get("text", str(plan)) if isinstance(plan, dict) else plan
        part_id = plan.get("part_id", "") if isinstance(plan, dict) else ""
        route_reason = plan.get("route_reason", "")
        force_llm = plan.get("force_llm", False) or bool(route_reason)
        use_llm = part_id not in KNOWN_PART_IDS or force_llm

        # FIX 4: Route logging — always show which path was taken
        if use_llm:
            if route_reason:
                print(f"[LLM] {route_reason}")
            elif part_id not in KNOWN_PART_IDS:
                print("[LLM] Unknown part -> LLM route")
            else:
                print("[LLM] Forced LLM route")
        else:
            print(f"[TEMPLATE] Using validated template: {part_id}")
        print(plan_text)

        expected_bbox = plan.get("expected_bbox") if isinstance(plan, dict) else None

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

        part_name = goal if use_llm else (part_id or goal)
        paths = get_output_paths(part_name, repo_root)
        step_path = Path(paths["step_path"])
        stl_path = Path(paths["stl_path"])

        if use_llm:
            inject = {"STEP_PATH": str(step_path), "STL_PATH": str(stl_path), "PART_NAME": part_name}
            result = validate(code, expected_bbox=expected_bbox, inject_namespace=inject, min_step_size_kb=1.0)
        else:
            result = validate(code, expected_bbox=expected_bbox)
        if not result.passed:
            last_error = result.error or "; ".join(result.errors)
            continue

        if "housing" in goal.lower() or "shell" in goal.lower():
            spec = {"width": 700.0, "height": 680.0, "depth": 344.0}
            validate_housing_spec(result, spec)
            if not result.passed:
                last_error = result.error
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
            if cem_result.static_min_sf is not None:
                session["cem_static_min_sf"] = cem_result.static_min_sf
            if not cem_result.overall_passed:
                print(f"[CEM FAIL] {cem_result.summary}")
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

        # Mesh integrity check (STL) — advisory for print readiness
        try:
            stl_path_check = Path(session.get("stl_path", ""))
            if stl_path_check.exists():
                mesh = validate_mesh_integrity(str(stl_path_check))
                session["mesh_validation"] = mesh
                if int(mesh.get("degenerate_triangles", 0)) > 0:
                    print(f"[MESH WARNING] {mesh.get('degenerate_triangles')} degenerate triangles found — do not print until geometry is fixed")
        except Exception as e:
            session["mesh_validation_error"] = str(e)

        logger_log(session)
        return session

    logger_log_failure(session, last_error)
    print("Diagnosis:", last_error)
    return session
