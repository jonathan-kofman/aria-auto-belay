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
from .post_gen_validator import run_validation_loop, check_output_quality


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

    # Extract user-specified dimensions and populate plan["params"] so templates honour them.
    from .spec_extractor import extract_spec, merge_spec_into_plan as _merge_spec
    _spec = extract_spec(goal)
    if _spec:
        _merge_spec(_spec, plan)
        # Sync user-specified dims back into base_shape so validation expected_bbox
        # reflects what the user actually asked for, not the planner's template defaults.
        _base = plan.get("base_shape")
        if isinstance(_base, dict):
            _DIM_KEYS = (
                "od_mm", "bore_mm", "id_mm", "thickness_mm", "height_mm",
                "width_mm", "depth_mm", "length_mm", "diameter_mm",
            )
            for _k in _DIM_KEYS:
                if _k in _spec:
                    _base[_k] = _spec[_k]
        _user_dims = [
            f"{k}={v} (user)"
            for k, v in _spec.items()
            if k not in ("part_type", "material")
        ]
        if _user_dims:
            print(f"[SPEC] {' '.join(_user_dims)}")

    plan_text = plan.get("engineering_brief") or plan.get("text", str(plan))
    part_id   = plan.get("part_id", "")

    # Prefer Claude-based router; fall back to heuristic if LLM unavailable
    if not plan.get("cad_tool_selected"):
        try:
            from .multi_cad_router import CADRouter
            router = CADRouter()
            decision = router.route(goal, dry_run=False)
            cad_tool = decision["backend"]
            plan["cad_tool_selected"]  = cad_tool
            plan["cad_tool_rationale"] = decision.get("reasoning", "")
            plan["cad_tool_decision"]  = decision
        except Exception:
            cad_tool = select_cad_tool(goal, plan)
    else:
        cad_tool = plan["cad_tool_selected"]

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
        _gh_previous_failures: list[str] = []
        for _gh_attempt in range(max_attempts):
            try:
                artifacts = write_grasshopper_artifacts(
                    plan if isinstance(plan, dict) else {},
                    goal,
                    str(step_path),
                    str(stl_path),
                    repo_root=repo_root,
                )
                break
            except RuntimeError as _gh_err:
                _gh_reason = str(_gh_err)
                _gh_previous_failures.append(_gh_reason)
                print(f"[GH RETRY {_gh_attempt + 1}/{max_attempts}] {_gh_reason}")
                event_bus.emit("error", f"GH attempt {_gh_attempt + 1} failed: {_gh_reason}", {"part_id": part_id})
                if _gh_attempt + 1 >= max_attempts:
                    print(f"[GH FAIL] All {max_attempts} attempts exhausted.")
                    artifacts = {"status": "failure", "error": _gh_reason, "previous_failures": _gh_previous_failures}
        else:
            artifacts = artifacts if artifacts else {"status": "failure", "error": "GH loop exhausted"}

        script_path = artifacts.get("script_path", "")
        session["script_path"] = script_path

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

    elif cad_tool == "cadquery":
        try:
            from .cadquery_generator import write_cadquery_artifacts
            artifacts = write_cadquery_artifacts(
                plan if isinstance(plan, dict) else {},
                goal,
                str(step_path),
                str(stl_path),
                repo_root=repo_root,
            )
            if artifacts.get("step_path"):
                session["step_path"] = artifacts["step_path"]
            if artifacts.get("stl_path"):
                session["stl_path"] = artifacts["stl_path"]
            if artifacts.get("bbox"):
                session["bbox"] = artifacts["bbox"]
            event_bus.emit("complete", "CadQuery generation complete", {"part_id": part_id})
        except Exception as exc:
            event_bus.emit("error", f"CadQuery failed: {exc}", {"part_id": part_id})
            print(f"[CADQUERY ERROR] {exc}")

    elif cad_tool == "fusion360":
        try:
            from .fusion_generator import generate_fusion_script
            fusion_script = generate_fusion_script(
                plan if isinstance(plan, dict) else {},
                goal,
                str(step_path),
                str(stl_path),
                repo_root=repo_root,
            )
            # Write script to outputs dir
            fusion_dir = repo_root / "outputs" / "cad" / "fusion" / (part_id or "aria_part")
            fusion_dir.mkdir(parents=True, exist_ok=True)
            script_file = fusion_dir / f"{part_id or 'aria_part'}_fusion.py"
            script_file.write_text(fusion_script, encoding="utf-8")
            artifacts["script_path"] = str(script_file)
            session["script_path"] = str(script_file)
            print(f"[FUSION360] Script ready: {script_file}")
            event_bus.emit("complete", "Fusion 360 script written", {"part_id": part_id})
        except Exception as exc:
            event_bus.emit("error", f"Fusion 360 generator failed: {exc}", {"part_id": part_id})
            print(f"[FUSION360 ERROR] {exc}")

    # --- Run validation loop for geometry-producing backends ---
    if cad_tool in ("grasshopper", "cadquery") and artifacts.get("script_path"):
        # Only run validation if files were already produced (CadQuery in-process)
        # or if a STEP/STL file exists from a prior Rhino Compute run
        if step_path.exists() or stl_path.exists():
            try:
                _val_plan = {"part_id": part_id, "params": plan.get("params", {}), "text": goal}

                def _noop_generate(p, sp, st, rr):
                    # Geometry already produced; just return existing paths
                    return {
                        "status": "success" if Path(st).exists() else "failure",
                        "step_path": str(sp) if Path(sp).exists() else None,
                        "stl_path":  str(st) if Path(st).exists() else None,
                        "error": None,
                    }

                val_result = run_validation_loop(
                    generate_fn=_noop_generate,
                    goal=goal,
                    plan=_val_plan,
                    step_path=str(step_path),
                    stl_path=str(stl_path),
                    max_attempts=1,  # files already generated; one-shot validation
                    repo_root=repo_root,
                    skip_visual=True,
                    check_quality=True,
                )
                session["validation"] = {
                    "geo":  val_result.get("geo_result", {}),
                    "vis":  val_result.get("vis_result", {}),
                    "quality": val_result.get("quality_result", {}),
                    "attempts": val_result.get("attempts", 1),
                    "status": val_result.get("status"),
                    "validation_failures": val_result.get("validation_failures", []),
                }
                event_bus.emit("validation", f"Geometry check: {val_result['status']}", {"part_id": part_id})
            except Exception as exc:
                print(f"[VALIDATION WARN] {exc}")

    # --- Attempt Rhino Compute execution (grasshopper only) ---
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
            event_bus.emit("step", "Rhino Compute unavailable — artifacts written", {"runner": runner})

    # --- Output quality: STEP readable + STL watertight check/repair (all backends) ---
    if step_path.exists() or stl_path.exists():
        try:
            quality = check_output_quality(str(step_path), str(stl_path))
            session["output_quality"] = quality
            stl_info = quality.get("stl", {})
            step_info = quality.get("step", {})
            if stl_info.get("repaired"):
                print(f"[QUALITY] STL repaired (was not watertight): {stl_path}")
                event_bus.emit("validation", "STL repaired", {"part_id": part_id, "stl_path": str(stl_path)})
            if not step_info.get("readable", True):
                print(f"[QUALITY] STEP not readable: {step_path}")
                event_bus.emit("validation", "STEP not readable", {"part_id": part_id})
            if quality.get("passed"):
                event_bus.emit("validation", "Output quality OK", {"part_id": part_id})
            else:
                failures = quality.get("failures", [])
                event_bus.emit("validation", f"Output quality issues: {failures}", {"part_id": part_id})
        except Exception as exc:
            print(f"[QUALITY WARN] {exc}")

    session["automation_artifacts"] = artifacts
    session["attempts"] = 1

    # --- CEM physics check (runs for every single-part generation) ---
    _cem_result = None
    _cem_passed = None
    if part_id and (step_path.exists() or stl_path.exists()):
        try:
            _meta_path = Path(get_meta_path(part_id, repo_root))
            _cem_result = cem_checks.run_cem_checks(part_id, _meta_path, context)
            _cem_passed = _cem_result.overall_passed
            session["cem"] = {
                "passed": _cem_result.overall_passed,
                "summary": _cem_result.summary,
                "static_min_sf": _cem_result.static_min_sf,
                "static_failure_mode": _cem_result.static_failure_mode,
            }
            if not _cem_result.overall_passed:
                print(f"[CEM FAIL] {_cem_result.summary}")
                event_bus.emit("cem", f"CEM FAIL: {_cem_result.summary}",
                               {"part_id": part_id, "passed": False,
                                "sf": _cem_result.static_min_sf})
            else:
                print(f"[CEM OK] {_cem_result.summary}")
                event_bus.emit("cem", f"CEM OK: {_cem_result.summary}",
                               {"part_id": part_id, "passed": True,
                                "sf": _cem_result.static_min_sf})
        except Exception as _cem_exc:
            print(f"[CEM WARN] {_cem_exc}")

    # --- Derive real learning-log values from actual run results ---
    _bbox = session.get("bbox") or {}
    _quality = session.get("output_quality", {})
    _mesh_clean = _quality.get("stl", {}).get("watertight_after") if _quality else None
    _val_status = session.get("validation", {}).get("status")

    # passed = no validation failure AND CEM didn't hard-fail AND output quality OK
    _passed = (
        _val_status != "failure"
        and (_cem_passed is not False)
        and _quality.get("passed", True)
    )

    # bbox_within_2pct: check XY bbox vs spec od_mm within 2 %
    _bbox_within_2pct = False
    if _bbox and _spec:
        _od = _spec.get("od_mm")
        if _od and _bbox.get("x"):
            _tol = _od * 0.02
            _bbox_within_2pct = (
                abs(_bbox.get("x", 0) - _od) <= _tol
                and abs(_bbox.get("y", 0) - _od) <= _tol
            )

    record_attempt(
        goal=goal,
        plan_text=plan_text,
        part_id=part_id or "aria_part",
        code=f"# routed_tool={cad_tool}",
        passed=_passed,
        bbox=_bbox or {"x": 0.0, "y": 0.0, "z": 0.0},
        error=None,
        cem_snapshot=load_cem_geometry(repo_root, goal=goal, part_id=part_id or ""),
        cem_passed=_cem_passed,
        feature_complete=True,
        mesh_clean=bool(_mesh_clean) if _mesh_clean is not None else True,
        bbox_within_2pct=_bbox_within_2pct,
        tool_used=cad_tool,
        repo_root=repo_root,
    )

    event_bus.emit("complete", f"Pipeline complete for {part_id or goal}", {"session": session})
    logger_log(session)
    return session
