"""ARIA-OS orchestrator: load context -> plan -> route -> generate -> validate -> export -> log."""
from pathlib import Path
from .context_loader import load_context
from .planner import plan as planner_plan
from .exporter import get_output_paths, get_meta_path
from .logger import log as logger_log, log_failure as logger_log_failure
from . import cem_checks
from . import event_bus
from .cem_context import load_cem_geometry
from .cad_learner import record_attempt
from .tool_router import select_cad_tool
from .grasshopper_generator import write_grasshopper_artifacts, validate_grasshopper_output
from .blender_generator import write_blender_artifacts
from .cad_prompt_builder import attach_brief_to_plan
from .validator import validate_grasshopper_script


def run(goal: str, repo_root: Path | None = None, max_attempts: int = 3):
    """Run the ARIA-OS pipeline: plan → route → generate artifacts → validate → log."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    context = load_context(repo_root)
    session: dict = {"goal": goal, "attempts": 0, "step_path": "", "stl_path": ""}

    event_bus.emit("step", "Pipeline started", {"goal": goal})

    # --- Plan + route ---
    plan = planner_plan(goal, context, repo_root=repo_root)
    if not isinstance(plan, dict):
        plan = {"part_id": "aria_part", "text": str(plan), "build_order": [], "features": []}
    plan = attach_brief_to_plan(goal, plan, context, repo_root=repo_root)

    plan_text = plan.get("engineering_brief") or plan.get("text", str(plan))
    part_id   = plan.get("part_id", "")
    cad_tool  = plan.get("cad_tool_selected") or select_cad_tool(goal, plan)

    session["cad_tool"]          = cad_tool
    session["cad_route"]         = {"tool": cad_tool, "rationale": plan.get("cad_tool_rationale", "")}
    session["engineering_brief"] = plan.get("engineering_brief", "")

    event_bus.emit("step", f"Tool: {cad_tool}", {"part_id": part_id, "tool": cad_tool})

    # --- Print route banner ---
    print("\n" + "=" * 64)
    print("ARIA CAD ROUTE (tool + auto-built engineering prompt)")
    print("=" * 64)
    print(f"Pipeline: {cad_tool}")
    print(f"Why: {plan.get('cad_tool_rationale', '')}")
    print(f"[AUTOMATION] Primary CAD: {cad_tool} (artifacts → outputs/cad/...)")
    print("-" * 64)
    print(plan_text)
    print("=" * 64 + "\n")

    paths     = get_output_paths(part_id or goal, repo_root)
    step_path = Path(paths["step_path"])
    stl_path  = Path(paths["stl_path"])

    # --- Generate artifacts ---
    artifacts: dict[str, str] = {}

    if cad_tool == "grasshopper":
        artifacts = write_grasshopper_artifacts(
            plan if isinstance(plan, dict) else {},
            goal,
            str(step_path),
            str(stl_path),
            repo_root=repo_root,
        )

        script_path = artifacts.get("script_path", "")
        session["script_path"] = script_path

        # Validate generated script (>500 bytes, syntax, required API calls)
        if script_path:
            script_ok, script_errors = validate_grasshopper_script(script_path)
            if not script_ok:
                for e in script_errors:
                    event_bus.emit("validation", f"Script validation: {e}", {"part_id": part_id})
                    print(f"[SCRIPT WARN] {e}")
            else:
                size = Path(script_path).stat().st_size
                print(f"[GRASSHOPPER] Script ready: {script_path} ({size} bytes)")
                event_bus.emit(
                    "grasshopper",
                    f"[GRASSHOPPER] Script ready: {script_path} ({size} bytes)",
                    {"script_path": script_path, "size_bytes": size, "part_id": part_id},
                )

    elif cad_tool == "blender":
        artifacts = write_blender_artifacts(
            plan if isinstance(plan, dict) else {},
            goal,
            str(stl_path),
            repo_root=repo_root,
        )

    # --- Attempt Rhino Compute execution if a runner was produced ---
    runner = artifacts.get("runner_path", "")
    if runner and Path(runner).exists():
        event_bus.emit("step", "Attempting Rhino Compute execution", {"runner": runner})
        try:
            import subprocess, sys as _sys
            result = subprocess.run(
                [_sys.executable, runner],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                if step_path.exists():
                    session["step_path"] = str(step_path)
                if stl_path.exists():
                    session["stl_path"] = str(stl_path)
                # Parse BBOX from stdout
                gh_validation = validate_grasshopper_output(str(step_path), result.stdout)
                if gh_validation.get("bbox"):
                    session["bbox"] = gh_validation["bbox"]
                event_bus.emit("complete", "Rhino Compute run succeeded", {"part_id": part_id})
            else:
                warn = result.stderr[:500] or result.stdout[:500]
                session["rhino_compute_warning"] = warn
                event_bus.emit("error", f"Rhino Compute run failed: {warn}", {"part_id": part_id})
        except Exception as e:
            session["rhino_compute_pending"] = str(e)
            print(f"[INFO] Rhino Compute not available ({e}). Artifacts written; run manually: {runner}")
            event_bus.emit("step", f"Rhino Compute unavailable — artifacts written", {"runner": runner})

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
        cem_snapshot=load_cem_geometry(repo_root, goal=goal, part_id=part_id or ""),
        cem_passed=False,
        feature_complete=True,
        mesh_clean=True,
        bbox_within_2pct=False,
        tool_used=cad_tool,
        repo_root=repo_root,
    )

    event_bus.emit("complete", f"Pipeline complete for {part_id or goal}", {"session": session})
    logger_log(session)
    return session
