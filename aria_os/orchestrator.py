"""ARIA-OS orchestrator: load context -> plan -> route -> generate -> validate -> export -> log."""
import sys as _sys
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


def _prompt_gdnt_drawing() -> bool:
    """Ask user if they want a GD&T drawing. Returns True if yes. Non-blocking if not a tty."""
    if not _sys.stdin.isatty():
        return False
    try:
        print()
        ans = input("[GD&T] Generate engineering drawing for this part? [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def run(goal: str, repo_root: Path | None = None, max_attempts: int = 3, *, preview: bool = False, auto_draw: bool = False):
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
    # Extract user-specified dimensions and populate plan["params"] so templates honour them.
    # Must happen BEFORE attach_brief_to_plan so the engineering brief reflects user dims.
    from .spec_extractor import extract_spec, merge_spec_into_plan as _merge_spec
    _spec = extract_spec(goal)
    if _spec:
        _merge_spec(_spec, plan)
        # Sync user-specified dims back into base_shape so validation expected_bbox
        # reflects what the user actually asked for, not the planner's template defaults.
        _base = plan.get("base_shape")
        if not isinstance(_base, dict):
            plan["base_shape"] = {}
            _base = plan["base_shape"]
        if isinstance(_base, dict):
            _DIM_KEYS = (
                "od_mm", "bore_mm", "id_mm", "thickness_mm", "height_mm",
                "width_mm", "depth_mm", "length_mm",
                # diameter_mm excluded: for box parts it captures sub-feature dims (ports/holes),
                # not the part's base shape — syncing it would mislead bbox validation.
            )
            # Also write the bare (no _mm) key that planner uses for box dims
            _SHORT_KEY = {
                "width_mm": "width", "height_mm": "height", "depth_mm": "depth",
                "length_mm": "length", "thickness_mm": "thickness",
            }
            for _k in _DIM_KEYS:
                if _k in _spec:
                    _base[_k] = _spec[_k]
                    if _k in _SHORT_KEY:
                        _base[_SHORT_KEY[_k]] = _spec[_k]
        _user_dims = [
            f"{k}={v} (user)"
            for k, v in _spec.items()
            if k not in ("part_type", "material")
        ]
        if _user_dims:
            print(f"[SPEC] {' '.join(_user_dims)}")

    # --- CEM: resolve physics model for this domain, auto-generate if unknown ---
    # Priority: static registry (aria/lre) → dynamic registry → LLM-generated new CEM
    # CEM outputs fill in plan["params"] without overwriting user-explicit values.
    # This is the LEAP-71 layer: engineering constraints → physics-derived geometry.
    try:
        from .cem_generator import resolve_and_compute
        _cem_params = plan.get("params") or {}
        _cem_result = resolve_and_compute(goal, plan.get("part_id", ""), _cem_params, repo_root)
        if _cem_result:
            params_target = plan.setdefault("params", {})
            injected = []
            for k, v in _cem_result.items():
                if k == "part_family":
                    continue
                if k not in params_target or params_target[k] is None:
                    params_target[k] = v
                    injected.append(f"{k}={v}")
            if injected:
                print(f"[CEM] Physics params injected: {' '.join(injected)}")
            plan["cem_context"] = _cem_result
    except Exception as _cem_exc:
        print(f"[CEM] skipped: {_cem_exc}")

    plan = attach_brief_to_plan(goal, plan, context, repo_root=repo_root)

    plan_text = plan.get("engineering_brief") or plan.get("text", str(plan))
    part_id   = plan.get("part_id", "")

    # Prefer Claude-based router; fall back to heuristic if LLM unavailable
    if not plan.get("cad_tool_selected"):
        try:
            from .multi_cad_router import CADRouter
            decision = CADRouter.route(goal, dry_run=False)
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
    print(f"[AUTOMATION] Primary CAD: {cad_tool} (artifacts -> outputs/cad/...)")
    print("-" * 64)
    # Encode-safe: replace chars the Windows console can't handle
    _enc = getattr(_sys.stdout, "encoding", "utf-8") or "utf-8"
    print(plan_text.encode(_enc, errors="replace").decode(_enc))
    print("=" * 64 + "\n")

    paths     = get_output_paths(part_id or goal, repo_root)
    step_path = Path(paths["step_path"])
    stl_path  = Path(paths["stl_path"])

    # --- Generate artifacts ---
    artifacts: dict[str, str] = {}

    if cad_tool == "grasshopper":
        _gh_previous_failures: list[str] = []
        _gh_succeeded = False
        for _gh_attempt in range(max_attempts):
            try:
                artifacts = write_grasshopper_artifacts(
                    plan if isinstance(plan, dict) else {},
                    goal,
                    str(step_path),
                    str(stl_path),
                    repo_root=repo_root,
                )
                _gh_succeeded = True
                break
            except RuntimeError as _gh_err:
                _gh_reason = str(_gh_err)
                _gh_previous_failures.append(_gh_reason)
                print(f"[GH RETRY {_gh_attempt + 1}/{max_attempts}] {_gh_reason}")
                event_bus.emit("error", f"GH attempt {_gh_attempt + 1} failed: {_gh_reason}", {"part_id": part_id})
                if _gh_attempt + 1 >= max_attempts:
                    print(f"[GH FAIL] All {max_attempts} attempts exhausted.")
                    artifacts = {"status": "failure", "error": _gh_reason, "previous_failures": _gh_previous_failures}

        if not _gh_succeeded:
            # Fall back to CadQuery so the pipeline always produces geometry.
            # GH script artifacts are still written to disk — they can be used in
            # Rhino Compute later. CadQuery gives an immediate STEP/STL.
            print(f"[GH→CQ FALLBACK] Rhino Compute unavailable — generating CadQuery artifact instead.")
            session["gh_fallback"] = True
            cad_tool = "cadquery"
        else:
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

    elif cad_tool == "sdf":
        try:
            from .sdf_heat_exchanger import write_sdf_artifacts
            artifacts = write_sdf_artifacts(
                plan if isinstance(plan, dict) else {},
                goal,
                str(stl_path),
                repo_root=repo_root,
            )
            if artifacts.get("stl_path"):
                session["stl_path"] = artifacts["stl_path"]
            if artifacts.get("error"):
                session["sdf_error"] = artifacts["error"]
                print(f"[SDF ERROR] {artifacts['error']}")
            else:
                meta = artifacts.get("meta", {})
                print(
                    f"[SDF] {meta.get('tpms_type', 'tpms')} | "
                    f"scale={meta.get('scale_mm', 0):.1f}mm | "
                    f"{meta.get('voxels', 0):,} voxels | "
                    f"{meta.get('triangles', 0):,} triangles"
                )
                session["sdf_meta"] = meta
                event_bus.emit("complete", "SDF generation complete", {"part_id": part_id})
        except ImportError as _sdf_imp:
            print(f"[SDF] scikit-image not installed — falling back to cadquery.")
            print(f"      Run: pip install scikit-image")
            # Fall through to cadquery below by setting cad_tool
            cad_tool = "cadquery"
            event_bus.emit("error", f"SDF import error: {_sdf_imp}", {"part_id": part_id})
        except Exception as exc:
            event_bus.emit("error", f"SDF failed: {exc}", {"part_id": part_id})
            print(f"[SDF ERROR] {exc}")

    if cad_tool == "cadquery":
        try:
            from .cadquery_generator import write_cadquery_artifacts

            # Build a generate_fn compatible with run_validation_loop protocol:
            #   generate_fn(plan, step_path, stl_path, repo_root, previous_failures=None) -> dict
            def _cq_generate_fn(p, sp, st, rr, previous_failures=None):
                return write_cadquery_artifacts(
                    p if isinstance(p, dict) else {},
                    goal,
                    str(sp),
                    str(st),
                    repo_root=rr,
                    previous_failures=previous_failures,
                )

            _val_plan = {"part_id": part_id, "params": plan.get("params", {}), "text": goal}

            val_result = run_validation_loop(
                generate_fn=_cq_generate_fn,
                goal=goal,
                plan=_val_plan,
                step_path=str(step_path),
                stl_path=str(stl_path),
                max_attempts=max_attempts,
                repo_root=repo_root,
                skip_visual=True,
                check_quality=True,
            )

            # Extract results from validation loop
            gen_result = val_result.get("generate_result", {})
            artifacts = gen_result if isinstance(gen_result, dict) else {}

            if gen_result.get("step_path"):
                session["step_path"] = gen_result["step_path"]
            if gen_result.get("stl_path"):
                session["stl_path"] = gen_result["stl_path"]
            if gen_result.get("bbox"):
                session["bbox"] = gen_result["bbox"]
            if gen_result.get("script_path"):
                session["script_path"] = gen_result["script_path"]
                artifacts["script_path"] = gen_result["script_path"]
            if gen_result.get("error"):
                session["cq_error"] = gen_result["error"]

            session["validation"] = {
                "geo":  val_result.get("geo_result", {}),
                "vis":  val_result.get("vis_result", {}),
                "quality": val_result.get("quality_result", {}),
                "attempts": val_result.get("attempts", 1),
                "status": val_result.get("status"),
                "validation_failures": val_result.get("validation_failures", []),
            }

            if val_result.get("status") == "success":
                event_bus.emit("complete", "CadQuery generation complete", {"part_id": part_id})
            else:
                _val_failures = val_result.get("validation_failures", [])
                print(f"[CQ VALIDATION FAIL] {val_result.get('attempts', 0)} attempts exhausted. Failures: {_val_failures}")
                event_bus.emit("error", f"CQ validation failed after {val_result.get('attempts', 0)} attempts", {"part_id": part_id})

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
            print(f"[FUSION360] Run this script inside Fusion 360 to produce STEP/STL.")
            event_bus.emit("complete", "Fusion 360 script written", {"part_id": part_id})
        except Exception as exc:
            event_bus.emit("error", f"Fusion 360 generator failed: {exc}", {"part_id": part_id})
            print(f"[FUSION360 ERROR] {exc}")

        # Always generate a CadQuery approximation so the pipeline produces immediate geometry.
        # The Fusion script is the authoritative design (lattice/generative/simulation);
        # the CQ artifact is a structural placeholder for assembly and preview.
        print(f"[FUSION360→CQ] Generating CadQuery approximation for preview/assembly...")
        session["fusion_cq_approx"] = True
        cad_tool = "cadquery"

    # --- Run validation loop for grasshopper backend ---
    # CadQuery validation is handled above via its own run_validation_loop call.
    # Grasshopper artifacts are produced by write_grasshopper_artifacts, so we wire
    # a generate_fn that re-invokes that function on retry.
    if cad_tool == "grasshopper" and artifacts.get("script_path"):
        if step_path.exists() or stl_path.exists():
            try:
                _val_plan = {"part_id": part_id, "params": plan.get("params", {}), "text": goal}

                def _gh_regen_fn(p, sp, st, rr, previous_failures=None):
                    """Re-invoke grasshopper generation for validation retries."""
                    try:
                        regen_artifacts = write_grasshopper_artifacts(
                            plan if isinstance(plan, dict) else {},
                            goal,
                            str(sp),
                            str(st),
                            repo_root=rr,
                        )
                        return {
                            "status": "success" if regen_artifacts.get("script_path") else "failure",
                            "step_path": str(sp) if Path(sp).exists() else None,
                            "stl_path":  str(st) if Path(st).exists() else None,
                            "error": regen_artifacts.get("error"),
                            "script_path": regen_artifacts.get("script_path"),
                        }
                    except RuntimeError as e:
                        return {
                            "status": "failure",
                            "step_path": str(sp) if Path(sp).exists() else None,
                            "stl_path":  str(st) if Path(st).exists() else None,
                            "error": str(e),
                        }

                val_result = run_validation_loop(
                    generate_fn=_gh_regen_fn,
                    goal=goal,
                    plan=_val_plan,
                    step_path=str(step_path),
                    stl_path=str(stl_path),
                    max_attempts=max_attempts,
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
            import subprocess as _subprocess
            result = _subprocess.run(
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
            if not step_info.get("readable", True) and cad_tool != "sdf":
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

    # --- Preview UI: show 3D model + let user choose export format ---
    if preview:
        _stl_for_preview = session.get("stl_path") or (str(stl_path) if stl_path.exists() else None)
        _script_for_preview = session.get("script_path")
        if _stl_for_preview and Path(_stl_for_preview).exists():
            from .preview_ui import show_preview
            _export_choice = show_preview(
                _stl_for_preview,
                part_id=part_id or goal[:40],
                script_path=_script_for_preview,
            )
            session["export_choice"] = _export_choice
            # Act on choice: delete unwanted output files
            if _export_choice == "skip":
                print("[PREVIEW] Discarding outputs as requested.")
                for _p in (step_path, stl_path):
                    if _p.exists():
                        _p.unlink(missing_ok=True)
                event_bus.emit("complete", "Preview: user discarded run", {"part_id": part_id})
                return session
            elif _export_choice == "fusion":
                # Generate Fusion 360 parametric script from the same plan
                try:
                    from .fusion_generator import write_fusion_artifacts
                    _fusion_result = write_fusion_artifacts(
                        plan, goal,
                        str(step_path), str(stl_path),
                        repo_root=repo_root,
                    )
                    _fscript = _fusion_result["script_path"]
                    print()
                    print("=" * 64)
                    print("  FUSION 360 SCRIPT GENERATED")
                    print("=" * 64)
                    print(f"  Script:  {_fscript}")
                    print()
                    print("  To use it in Fusion 360:")
                    print("    1. Open Fusion 360")
                    print("    2. Tools → Add-Ins → Scripts and Add-Ins")
                    print("    3. Click the '+' next to My Scripts, point to the folder above")
                    print("    4. Select the script and click Run")
                    print("    5. The part builds with a full parametric feature tree")
                    print("=" * 64)
                    session["fusion_script"] = _fscript
                except Exception as _fe:
                    print(f"[PREVIEW] Fusion script generation failed: {_fe}")
                # Keep STEP + STL as well (useful for reference / assembly)
            elif _export_choice == "step":
                if stl_path.exists():
                    stl_path.unlink(missing_ok=True)
                    print(f"[PREVIEW] STL removed (step-only export): {stl_path}")
            elif _export_choice == "stl":
                if step_path.exists():
                    step_path.unlink(missing_ok=True)
                    print(f"[PREVIEW] STEP removed (stl-only export): {step_path}")
            # "both" → keep everything (default)
        else:
            print("[PREVIEW] No STL available for preview — skipping viewer.")

    # --- GD&T drawing prompt ---
    if step_path.exists() and session.get("export_choice") != "skip":
        _ask_gdnt = auto_draw or _prompt_gdnt_drawing()
        if _ask_gdnt:
            try:
                from .drawing_generator import generate_gdnt_drawing
                _drawing_path = generate_gdnt_drawing(
                    step_path,
                    part_id or "aria_part",
                    params=plan.get("params"),
                    repo_root=repo_root,
                )
                print(f"[GD&T] Drawing saved: {_drawing_path}")
                session["drawing_path"] = str(_drawing_path)
            except Exception as _de:
                print(f"[GD&T] Drawing generation failed: {_de}")

    # --- FEA/CFD physics analysis prompt (after STEP export) ---
    if (step_path.exists() or stl_path.exists()) and session.get("export_choice") != "skip":
        try:
            from .physics_analyzer import prompt_and_analyze as _phys_prompt
            _phys_result = _phys_prompt(
                part_id=plan.get("part_id", ""),
                params=plan.get("params", {}),
                goal=goal,
                step_path=str(step_path),
                repo_root=repo_root,
            )
            if _phys_result:
                session["physics_analysis"] = _phys_result
                if not _phys_result["passed"]:
                    print(f"[PHYSICS] FAIL — SF={_phys_result.get('safety_factor', '?')}")
                    for _f in _phys_result["failures"]:
                        print(f"  \u2717 {_f}")
                else:
                    _phys_sf = _phys_result.get("safety_factor")
                    if _phys_sf is not None:
                        print(f"[PHYSICS] PASS — SF={_phys_sf:.2f}")
                    else:
                        print(f"[PHYSICS] PASS")
                for _w in _phys_result.get("warnings", []):
                    print(f"  \u26a0 {_w}")
        except Exception as _phys_exc:
            print(f"[PHYSICS] Analysis skipped: {_phys_exc}")

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
                # Determine the required SF threshold for this part
                _sf_val = _cem_result.static_min_sf
                _sf_mode = _cem_result.static_failure_mode or "unknown"
                _PART_SF_THRESHOLDS = {
                    "aria_ratchet_ring": ("tooth_shear", 8.0),
                    "aria_spool": ("radial_load", 2.0),
                    "aria_cam_collar": ("taper_engagement", 2.0),
                    "aria_housing": ("wall_bending", 2.0),
                    "aria_brake_drum": ("hoop_stress", 2.0),
                }
                _threshold = 2.0
                for _pid_key, (_mode, _thr) in _PART_SF_THRESHOLDS.items():
                    if _pid_key in (part_id or "").lower():
                        _threshold = _thr
                        break
                print(f"[CEM HARD FAIL] SF {_sf_val:.2f} below required {_threshold:.1f} for {part_id}. Export blocked.")
                event_bus.emit("cem", f"CEM FAIL: {_cem_result.summary}",
                               {"part_id": part_id, "passed": False,
                                "sf": _cem_result.static_min_sf})
                # Block export: remove generated STEP/STL files
                for _block_path in (step_path, stl_path):
                    if _block_path.exists():
                        _block_path.unlink(missing_ok=True)
                        print(f"[CEM] Removed: {_block_path}")
                session["cem_blocked"] = True
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

    # bbox_within_2pct: works for both cylindrical (od_mm) and box (width/height/depth) parts
    _bbox_within_2pct = False
    if _bbox and _spec:
        _od = _spec.get("od_mm")
        _w  = _spec.get("width_mm")
        _h  = _spec.get("height_mm")
        _d  = _spec.get("depth_mm")
        if _od and _bbox.get("x"):
            _tol = _od * 0.02
            _bbox_within_2pct = (
                abs(_bbox.get("x", 0) - _od) <= _tol
                and abs(_bbox.get("y", 0) - _od) <= _tol
            )
        elif _w and _h and _d:
            _tol = 2.0  # 2mm absolute tolerance for box parts
            _bbox_within_2pct = (
                abs(_bbox.get("x", 0) - _w) <= _tol
                and abs(_bbox.get("y", 0) - _h) <= _tol
                and abs(_bbox.get("z", 0) - _d) <= _tol
            )

    # Read the actual generated code from the script file (for few-shot learning)
    _generated_code = f"# routed_tool={cad_tool}"
    _script_path = session.get("script_path", "")
    if _script_path:
        try:
            _generated_code = Path(_script_path).read_text(encoding="utf-8")
        except Exception:
            pass

    # Collect the actual error message if generation failed
    _run_error = session.get("cq_error") or session.get("validation", {}).get("error") or ""
    if not _run_error and _val_status == "failure":
        _run_error = str(session.get("validation", {}).get("failures", "validation failed"))

    record_attempt(
        goal=goal,
        plan_text=plan_text,
        part_id=part_id or "aria_part",
        code=_generated_code,
        passed=_passed,
        bbox=_bbox or {"x": 0.0, "y": 0.0, "z": 0.0},
        error=_run_error or None,
        cem_snapshot=load_cem_geometry(repo_root),
        cem_passed=_cem_passed,
        feature_complete=True,
        mesh_clean=bool(_mesh_clean) if _mesh_clean is not None else True,
        bbox_within_2pct=_bbox_within_2pct,
        tool_used=cad_tool,
        repo_root=repo_root,
    )

    # --- Version tracking: write meta JSON for the generated part ---
    if (step_path.exists() or stl_path.exists()) and part_id:
        try:
            import json as _json
            from datetime import datetime as _dt
            _meta_dir = repo_root / "outputs" / "cad" / "meta"
            _meta_dir.mkdir(parents=True, exist_ok=True)
            _meta_file = _meta_dir / f"{part_id}.json"

            # Preserve existing meta and overlay new fields
            _existing_meta: dict = {}
            if _meta_file.exists():
                try:
                    _existing_meta = _json.loads(_meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Try to get git SHA for traceability
            _git_sha = ""
            try:
                import subprocess as _sp
                _git_sha = _sp.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(repo_root), stderr=_sp.DEVNULL, text=True
                ).strip()
            except Exception:
                pass

            _meta_file.write_text(_json.dumps({
                **_existing_meta,
                "part_id":    part_id,
                "goal":       goal,
                "params":     plan.get("params") or {},
                "cad_tool":   cad_tool,
                "step_path":  str(step_path) if step_path.exists() else "",
                "stl_path":   str(stl_path) if stl_path.exists() else "",
                "bbox_mm":    session.get("bbox") or {},
                "cem_sf":     (session.get("cem") or {}).get("static_min_sf"),
                "cem_passed": (session.get("cem") or {}).get("passed"),
                "generated_at": _dt.now().isoformat(),
                "git_sha":    _git_sha,
            }, indent=2), encoding="utf-8")
        except Exception as _me:
            print(f"[META] Could not write meta JSON: {_me}")

    event_bus.emit("complete", f"Pipeline complete for {part_id or goal}", {"session": session})
    logger_log(session)
    return session
