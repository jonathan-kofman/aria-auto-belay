"""ARIA-OS orchestrator: load context -> plan -> generate -> validate -> export -> log."""
from pathlib import Path
from .context_loader import load_context
from .planner import plan as planner_plan
from .generator import generate as generator_generate, KNOWN_PART_IDS
from .validator import validate, validate_housing_spec, validate_step_file, ValidationResult
from .exporter import export, get_output_paths
from .logger import log as logger_log, log_failure as logger_log_failure


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
        print(plan_text)

        part_id = plan.get("part_id", "") if isinstance(plan, dict) else ""
        use_llm = part_id not in KNOWN_PART_IDS
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
            inject = {"STEP_PATH": str(step_path), "STL_PATH": str(stl_path)}
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

        step_path_check = Path(session["step_path"])
        file_valid, solid_count, file_errors = validate_step_file(step_path_check, min_size_kb=1.0)
        if not file_valid and file_errors:
            if solid_count < 1:
                last_error = "; ".join(file_errors)
                continue
            session["validation_errors"] = file_errors

        logger_log(session)
        return session

    logger_log_failure(session, last_error)
    print("Diagnosis:", last_error)
    return session
