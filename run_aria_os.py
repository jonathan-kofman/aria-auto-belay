#!/usr/bin/env python3
"""ARIA-OS CLI: python run_aria_os.py \"describe the part you want\"
  --list       List all generated parts with file sizes and validation status
  --validate   Re-validate all existing STEP outputs (size + re-import)
  --modify     Modify existing part: --modify <path_to_.py> \"modification description\"
  --assemble   Create assembly from JSON: --assemble assembly_configs/foo.json
"""
import sys
import json
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def run_modify(base_part_path: str, modification: str):
    """Run PartModifier and print result + geometry stats."""
    from aria_os.modifier import PartModifier
    from aria_os.context_loader import load_context
    mod = PartModifier(repo_root=ROOT)
    context = load_context(ROOT)
    result = mod.modify(base_part_path, modification, context=context)
    if result.passed:
        print("Modification passed.")
        if result.bbox:
            print(f"BBOX: {result.bbox[0]:.2f} x {result.bbox[1]:.2f} x {result.bbox[2]:.2f} mm")
    else:
        print("Modification failed:", result.error)
    return result


def run_assemble(config_path: str):
    """Load JSON config, run Assembler, export STEP/STL."""
    from aria_os.assembler import Assembler, AssemblyPart
    path = ROOT / config_path if not Path(config_path).is_absolute() else Path(config_path)
    if not path.exists():
        print(f"Config not found: {path}")
        sys.exit(1)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    name = cfg.get("name", "assembly")
    parts = []
    for p in cfg.get("parts", []):
        step_path = p.get("step_path")
        if not Path(step_path).is_absolute():
            step_path = str(ROOT / step_path)
        parts.append(AssemblyPart(
            step_path=step_path,
            position=tuple(p.get("position", [0, 0, 0])),
            rotation=tuple(p.get("rotation", [0, 0, 0])),
            name=p.get("name", "part"),
        ))
    assy = Assembler(repo_root=ROOT)
    constraints = cfg.get("constraints", [])
    # run_assemble does not load full context; assembler will do so if needed
    out_path = assy.assemble(parts, name, constraints=constraints or None, context=None)
    print(f"Assembly exported: {out_path}")


def list_parts():
    """List all .step files in outputs/cad/step with size and validation status."""
    step_dir = ROOT / "outputs" / "cad" / "step"
    if not step_dir.exists():
        print("No outputs/cad/step directory.")
        return
    from aria_os.validator import validate_step_file
    steps = sorted(step_dir.glob("*.step"))
    if not steps:
        print("No STEP files found.")
        return
    print(f"{'Part':<25} {'STEP size':<12} {'STL size':<12} {'Valid':<8}")
    print("-" * 60)
    stl_dir = ROOT / "outputs" / "cad" / "stl"
    for p in steps:
        name = p.stem
        step_kb = p.stat().st_size / 1024
        stl_path = stl_dir / (name + ".stl")
        stl_kb = stl_path.stat().st_size / 1024 if stl_path.exists() else 0
        valid, count, errs = validate_step_file(p, min_size_kb=1.0)
        status = "OK" if valid else ("FAIL: " + "; ".join(errs[:1]))
        print(f"{name:<25} {step_kb:>8.1f} KB   {stl_kb:>8.1f} KB   {status:<8}")


def validate_all():
    """Re-validate all STEP files: size >= 10 KB and re-import has >= 1 solid."""
    step_dir = ROOT / "outputs" / "cad" / "step"
    if not step_dir.exists():
        print("No outputs/cad/step directory.")
        return
    from aria_os.validator import validate_step_file
    steps = sorted(step_dir.glob("*.step"))
    if not steps:
        print("No STEP files found.")
        return
    all_ok = True
    for p in steps:
        valid, solid_count, errs = validate_step_file(p, min_size_kb=10.0)
        if valid:
            print(f"OK  {p.name}  (solids: {solid_count}, {p.stat().st_size/1024:.1f} KB)")
        else:
            all_ok = False
            print(f"FAIL {p.name}: {'; '.join(errs)}")
    sys.exit(0 if all_ok else 1)

def run_print_scale(args: list[str]):
    """
    Scale an existing STEP file for print-fit checks:
      python run_aria_os.py --print-scale <part_stub> --scale 0.75
    Requires Rhino Compute (RHINO_COMPUTE_URL env var, default http://localhost:6500).
    Reports dims + 256mm bed fit; writes scaled STEP/STL via Rhino Compute.
    """
    if len(args) < 1:
        print("Usage: python run_aria_os.py --print-scale <part_stub> --scale <factor>")
        sys.exit(1)
    part_stub = args[0]
    scale = 1.0
    i = 1
    while i < len(args):
        if args[i] == "--scale" and i + 1 < len(args):
            try:
                scale = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    from aria_os.exporter import get_output_paths

    paths = get_output_paths(part_stub, ROOT)
    step_path = Path(paths["step_path"])
    if not step_path.exists():
        step_dir = ROOT / "outputs" / "cad" / "step"
        matches = [p for p in step_dir.glob("*.step") if part_stub.lower() in p.stem.lower()]
        if matches:
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            step_path = matches[0]
        else:
            print(f"STEP not found for stub: {part_stub}")
            sys.exit(1)

    compute_url = (
        __import__("os").environ.get("RHINO_COMPUTE_URL", "http://localhost:6500").rstrip("/")
    )

    try:
        import requests  # type: ignore
        resp = requests.get(f"{compute_url}/version", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Rhino Compute not available at {compute_url}: {e}")
        print("To use --print-scale, start Rhino Compute and set RHINO_COMPUTE_URL.")
        print("See docs/rhino_compute_setup.md for setup instructions.")
        sys.exit(1)

    pct = int(round(scale * 100))
    out_base = f"{step_path.stem}_print_{pct}pct"
    out_step = ROOT / "outputs" / "cad" / "step" / f"{out_base}.step"
    out_stl = ROOT / "outputs" / "cad" / "stl" / f"{out_base}.stl"
    out_step.parent.mkdir(parents=True, exist_ok=True)
    out_stl.parent.mkdir(parents=True, exist_ok=True)

    # Build RhinoCommon scale script and post to Rhino Compute
    script = f"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import Rhino

step_file = r"{step_path}"
out_step = r"{out_step}"
out_stl = r"{out_stl}"
scale = {scale}

objs = rs.Command('_-Import "' + step_file + '" _Enter', False)
all_objs = rs.AllObjects()
if all_objs:
    xform = rg.Transform.Scale(rg.Point3d.Origin, scale)
    for obj_id in all_objs:
        rs.TransformObject(obj_id, xform)
    bb_pts = [rs.BoundingBox([o]) for o in all_objs]
    all_pts = [pt for bb in bb_pts if bb for pt in bb]
    if all_pts:
        xs = [p.X for p in all_pts]
        ys = [p.Y for p in all_pts]
        zs = [p.Z for p in all_pts]
        xlen = max(xs) - min(xs)
        ylen = max(ys) - min(ys)
        zlen = max(zs) - min(zs)
        print(f"BBOX:{{xlen:.3f}},{{ylen:.3f}},{{zlen:.3f}}")
    rs.SelectObjects(all_objs)
    rs.Command(f'_-Export "{{out_step}}" _Enter', False)
    rs.Command(f'_-Export "{{out_stl}}" _Enter _Enter', False)
"""

    try:
        resp = requests.post(
            f"{compute_url}/grasshopper",
            json={"algo": script, "pointer": None, "values": []},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        stdout = str(data.get("stdout", ""))
        m = __import__("re").search(r"BBOX:([\d.]+),([\d.]+),([\d.]+)", stdout)
        scaled_dims = (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else (0, 0, 0)
    except Exception as e:
        print(f"Rhino Compute scale failed: {e}")
        sys.exit(1)

    bed_mm = 256.0
    fit = max(scaled_dims[0], scaled_dims[1]) <= bed_mm
    clearance = (bed_mm - max(scaled_dims[0], scaled_dims[1])) / 2.0

    print("=== Print Scale ===")
    print(f"Input STEP:  {step_path}")
    print(f"Scale:       {scale} ({pct}%)")
    print(f"Scaled dims: {scaled_dims[0]:.2f} x {scaled_dims[1]:.2f} x {scaled_dims[2]:.2f} mm")
    print(f"Output STEP: {out_step}")
    print(f"Output STL:  {out_stl}")
    print(f"Fits 256mm bed: {'YES' if fit else 'NO'} (clearance per side: {clearance:.2f} mm)")


def run_optimize(args: list[str]):
    """CLI entry for --optimize."""
    if len(args) < 1:
        print("Usage: python run_aria_os.py --optimize <code_or_stub> --goal <goal> [--constraint RULE ...] [--max-iter N]")
        sys.exit(1)
    code_stub = args[0]
    goal = "minimize_weight"
    constraints: list[str] = []
    max_iter = 20

    i = 1
    while i < len(args):
        tok = args[i]
        if tok == "--goal" and i + 1 < len(args):
            goal = args[i + 1]
            i += 2
        elif tok == "--constraint" and i + 1 < len(args):
            constraints.append(args[i + 1])
            i += 2
        elif tok in ("--max-iter", "--max_iter") and i + 1 < len(args):
            try:
                max_iter = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    # Resolve code path or stub to an actual file in outputs/cad/generated_code
    gen_dir = ROOT / "outputs" / "cad" / "generated_code"
    direct = Path(code_stub)
    if not direct.is_absolute():
        direct = (ROOT / code_stub).resolve()
    resolved_path: Path | None = None
    if direct.exists():
        resolved_path = direct
    else:
        # Search by substring in generated_code filenames
        if gen_dir.exists():
            matches: list[Path] = []
            for p in gen_dir.glob("*.py"):
                if code_stub.lower() in p.name.lower():
                    matches.append(p)
            if matches:
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                resolved_path = matches[0]
    if resolved_path is None:
        print(f"Could not find generated code matching: {code_stub!r}")
        if gen_dir.exists():
            print("Available generated code files:")
            for p in sorted(gen_dir.glob("*.py")):
                print(f"  - {p.name}")
        sys.exit(1)

    from aria_os.optimizer import PartOptimizer

    opt = PartOptimizer(repo_root=ROOT)
    result = opt.optimize(str(resolved_path), goal=goal, constraints=constraints, context=None, max_iterations=max_iter)
    print("=== Optimization Result ===")
    print(f"Part:        {result.part_name}")
    print(f"Goal:        {result.goal}")
    print(f"Constraints: {result.constraints}")
    print(f"Iterations:  {result.iterations}")
    print(f"Converged:   {result.converged}")
    print(f"Best score:  {result.best_score}")
    print(f"Best params: {result.best_params}")
    print(f"Best STEP:   {result.best_step_path}")
    print(result.summary)

def run_optimize_and_regenerate(args: list[str]):
    """CLI entry for --optimize-and-regenerate."""
    if len(args) < 1:
        print("Usage: python run_aria_os.py --optimize-and-regenerate <code_or_stub> --goal <goal> [--constraint RULE ...] [--material MATERIAL_ID] [--max-iter N]")
        sys.exit(1)
    code_stub = args[0]
    goal = "minimize_weight"
    constraints: list[str] = []
    material: str | None = None
    max_iter = 20

    i = 1
    while i < len(args):
        tok = args[i]
        if tok == "--goal" and i + 1 < len(args):
            goal = args[i + 1]
            i += 2
        elif tok == "--constraint" and i + 1 < len(args):
            constraints.append(args[i + 1])
            i += 2
        elif tok == "--material" and i + 1 < len(args):
            material = args[i + 1]
            i += 2
        elif tok in ("--max-iter", "--max_iter") and i + 1 < len(args):
            try:
                max_iter = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    # Resolve code path or stub to an actual file in outputs/cad/generated_code
    gen_dir = ROOT / "outputs" / "cad" / "generated_code"
    direct = Path(code_stub)
    if not direct.is_absolute():
        direct = (ROOT / code_stub).resolve()
    resolved_path: Path | None = None
    if direct.exists():
        resolved_path = direct
    else:
        if gen_dir.exists():
            matches: list[Path] = []
            for p in gen_dir.glob("*.py"):
                if code_stub.lower() in p.name.lower():
                    matches.append(p)
            if matches:
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                resolved_path = matches[0]
    if resolved_path is None:
        print(f"Could not find generated code matching: {code_stub!r}")
        if gen_dir.exists():
            print("Available generated code files:")
            for p in sorted(gen_dir.glob('*.py')):
                print(f"  - {p.name}")
        sys.exit(1)

    from aria_os.optimizer import PartOptimizer
    from aria_os.context_loader import load_context

    context = load_context(ROOT)
    opt = PartOptimizer(repo_root=ROOT)
    out = opt.optimize_and_regenerate(
        base_code_path=str(resolved_path),
        goal=goal,
        constraints=constraints,
        context=context,
        material=material,
        max_iterations=max_iter,
    )

    opt_result = out.get("optimization")
    print("=== Optimize + Regenerate Result ===")
    if opt_result is not None:
        print(f"Part:        {getattr(opt_result, 'part_name', '')}")
        print(f"Goal:        {getattr(opt_result, 'goal', '')}")
        print(f"Constraints: {getattr(opt_result, 'constraints', [])}")
        print(f"Iterations:  {getattr(opt_result, 'iterations', 0)}")
        print(f"Converged:   {getattr(opt_result, 'converged', False)}")
        print(f"Best params: {getattr(opt_result, 'best_params', {})}")
        print(f"Best STEP:   {getattr(opt_result, 'best_step_path', '')}")
    print(f"Recommended material: {out.get('recommended_material')}")
    gen = out.get("generation") or {}
    if gen:
        print(f"Generated STEP: {gen.get('step_path')}")
    print(out.get("summary", ""))


def run_cem_full():
    """Run CEM checks on all parts with meta JSON and print a rich report."""
    from aria_os.context_loader import load_context
    from aria_os import cem_checks
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console(highlight=False, emoji=False)
    context = load_context(ROOT)
    report = cem_checks.run_full_system_cem(ROOT / "outputs", context)

    total = report.get("total_parts", 0)
    passed = report.get("passed", 0)
    failed = report.get("failed", [])
    weakest_part = report.get("weakest_part")
    weakest_sf = report.get("weakest_sf")
    system_passed = report.get("system_passed", True)

    status_text = "OK ALL PARTS PASS" if system_passed else "[!] ATTENTION NEEDED"

    header = Panel.fit(
        f"ARIA SYSTEM CEM REPORT\n\n"
        f"Parts checked: {total}\n"
        f"Passed:        {passed}\n"
        f"Failed:        {len(failed)}\n"
        f"System status: {status_text}",
        title="ARIA CEM",
    )
    console.print(header)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Part", style="cyan")
    table.add_column("Static SF", justify="right")
    table.add_column("Status", justify="center")

    results = report.get("results", {})
    for name, data in results.items():
        sf = data.get("static_min_sf")
        ok = data.get("overall_passed", False)
        status = "[OK] PASS" if ok else "[FAIL] FAIL"
        sf_str = f"{sf:.2f}" if sf is not None else "-"
        table.add_row(name, sf_str, status)

    console.print(table)

    if weakest_part:
        console.print(
            f"Weakest link: [bold]{weakest_part}[/bold] "
            f"({weakest_sf:.2f}x SF)" if weakest_sf is not None else f"Weakest link: {weakest_part}"
        )


def run_generate_and_assemble(description: str, into_path: str, part_label: str, at_vec: str, rot_vec: str | None = None):
    """Generate a part, append it to an assembly config, and re-run assembly."""
    from aria_os import run as orchestrator_run

    # 1. Generate part
    session = orchestrator_run(description, repo_root=ROOT)
    step_path_str = session.get("step_path")
    if not step_path_str:
        print("Generation did not produce a STEP path.")
        sys.exit(1)
    step_path = Path(step_path_str)
    if not step_path.exists():
        print(f"Generated STEP not found: {step_path}")
        sys.exit(1)

    # 2. Load assembly JSON
    cfg_path = ROOT / into_path if not Path(into_path).is_absolute() else Path(into_path)
    if not cfg_path.exists():
        print(f"Assembly config not found: {cfg_path}")
        sys.exit(1)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    # 3. Parse vectors
    def _parse_vec(txt: str) -> list[float]:
        parts = [p for p in txt.split(",") if p.strip()]
        if len(parts) != 3:
            raise ValueError(f"Expected 3 comma-separated values, got: {txt!r}")
        return [float(p) for p in parts]

    pos = _parse_vec(at_vec)
    rot = _parse_vec(rot_vec) if rot_vec else [0.0, 0.0, 0.0]

    # 4. Append new part entry
    rel_step = step_path
    try:
        rel_step = step_path.relative_to(ROOT)
    except ValueError:
        rel_step = step_path

    parts = cfg.get("parts", [])
    parts.append(
        {
            "name": part_label,
            "step_path": str(rel_step).replace("\\", "/"),
            "position": pos,
            "rotation": rot,
            "notes": "auto-added by --generate-and-assemble",
        }
    )
    cfg["parts"] = parts
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    # 5. Re-run assembly
    run_assemble(str(cfg_path))


def run_material_study_cli(part_stub: str):
    """CLI entry for --material-study."""
    from rich.console import Console
    from rich.table import Table
    from aria_os.context_loader import load_context
    from aria_os.material_study import run_material_study

    console = Console(highlight=False, emoji=False)
    context = load_context(ROOT)
    outputs_dir = ROOT / "outputs"
    result = run_material_study(part_stub, context, outputs_dir)

    console.print(f"[bold]Material study for[/bold] {result.part_name} (criticality: {result.part_criticality}, SF target={result.sf_target:.1f}x)")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Rank", justify="right")
    table.add_column("Material")
    table.add_column("SF", justify="right")
    table.add_column("Weight [g]", justify="right")
    table.add_column("Rel Cost", justify="right")
    table.add_column("Mach", justify="right")
    table.add_column("Verdict")

    for r in result.ranked_results:
        table.add_row(
            str(r.rank),
            r.material.id,
            f"{r.sf:.2f}",
            f"{r.weight_g:.0f}",
            f"{r.relative_cost:.2f}",
            f"{r.machinability:.1f}",
            r.verdict,
        )

    console.print(table)
    console.print(f"[bold]Recommendation:[/bold] {result.recommendation.id} - {result.recommendation_reasoning}")
    console.print(f"Baseline material rank: {result.current_material_rank}")


def run_material_study_all_cli():
    from aria_os.context_loader import load_context
    from aria_os.material_study import run_material_study_all
    from rich.console import Console
    from rich.table import Table

    console = Console(highlight=False, emoji=False)
    context = load_context(ROOT)

    console.print("\n[bold]Running material studies on all parts...[/bold]\n")

    report = run_material_study_all(context, ROOT / "outputs")
    if "error" in report:
        console.print(f"[red]Error: {report['error']}[/red]")
        return

    table = Table(title="ARIA Material Study - All Parts")
    table.add_column("Part", style="cyan", width=36)
    table.add_column("Criticality", width=13)
    table.add_column("Recommended", style="green", width=17)
    table.add_column("SF", justify="right", width=6)
    table.add_column("Current", width=12)
    table.add_column("Action", width=8)

    for row in report["summary"]:
        action_style = "green" if row["action"] == "OK" else "red"
        table.add_row(
            row["part"],
            row["criticality"],
            row["recommended"],
            f"{row['recommended_sf']:.2f}",
            row["current"],
            f"[{action_style}]{row['action']}[/{action_style}]",
        )

    console.print(table)
    console.print(f"\nFull results saved to: {report['output_file']}")


def run_lattice_test():
    """Quick test to verify Blender pipeline works."""
    from rich.console import Console
    from aria_os.lattice.blender_pipeline import find_blender

    console = Console(highlight=False, emoji=False)

    blender = find_blender()
    if blender is None:
        console.print("[FAIL] Blender not found.")
        console.print("Install from: https://www.blender.org/download/")
        console.print("Then run: python run_aria_os.py --lattice-test")
        return

    console.print(f"[OK] Blender found: {blender}")
    console.print("Running quick geometry test...")

    from aria_os.lattice import generate_lattice, LatticeParams

    params = LatticeParams(
        pattern="honeycomb",
        form="volumetric",
        width_mm=40,
        height_mm=40,
        depth_mm=5,
        cell_size_mm=10,
        strut_diameter_mm=2.0,
        frame_thickness_mm=3.0,
        process="fdm",
        part_name="lattice_test_honeycomb",
    )

    try:
        result = generate_lattice(params)
        console.print(f"[OK] Honeycomb: {result.summary}")
        console.print(f"     STL: {result.stl_path}")
    except Exception as e:
        console.print(f"[FAIL] Honeycomb: {e}")

    params.pattern = "arc_weave"
    params.part_name = "lattice_test_arc_weave"
    try:
        result = generate_lattice(params)
        console.print(f"[OK] Arc weave: {result.summary}")
    except Exception as e:
        console.print(f"[FAIL] Arc weave: {e}")

    params.pattern = "octet_truss"
    params.width_mm = 30
    params.height_mm = 30
    params.depth_mm = 30
    params.cell_size_mm = 15
    params.part_name = "lattice_test_octet"
    try:
        result = generate_lattice(params)
        console.print(f"[OK] Octet truss: {result.summary}")
    except Exception as e:
        console.print(f"[FAIL] Octet truss: {e}")


def run_lattice(args: list[str]):
    """
    CLI entry for lattice generation:
      python run_aria_os.py --lattice --pattern honeycomb --form volumetric ...
    """
    from rich.console import Console
    from aria_os.lattice import generate_lattice, LatticeParams

    console = Console(highlight=False, emoji=False)

    def get_arg(flag: str, default: str) -> str:
        try:
            idx = args.index(flag)
            return args[idx + 1]
        except (ValueError, IndexError):
            return default

    def get_bool_arg(flag: str, default: bool = False) -> bool:
        if flag in args:
            return True
        neg = f"--no-{flag.lstrip('-')}"
        if neg in args:
            return False
        return default

    params = LatticeParams(
        pattern=get_arg("--pattern", "honeycomb"),
        form=get_arg("--form", "volumetric"),
        width_mm=float(get_arg("--width", "100")),
        height_mm=float(get_arg("--height", "100")),
        depth_mm=float(get_arg("--depth", "10")),
        cell_size_mm=float(get_arg("--cell-size", "10")),
        strut_diameter_mm=float(get_arg("--strut", "1.5")),
        skin_thickness_mm=float(get_arg("--skin", "2.0")),
        frame_thickness_mm=float(get_arg("--frame", "5.0")),
        interlaced=get_bool_arg("--interlaced", default=False),
        weave_offset_mm=float(get_arg("--weave-offset", "0.0")),
        process=get_arg("--process", "both"),
        part_name=get_arg("--name", "lattice_panel"),
    )

    console.print(f"\nGenerating {params.pattern} {params.form} lattice...")

    result = generate_lattice(params)

    for w in result.process_warnings:
        console.print(f"  [WARN] {w}")

    console.print(f"\n[DONE] {result.summary}")
    console.print(f"  STEP: {result.step_path}")
    console.print(f"  STL:  {result.stl_path}")
    console.print(f"  Cells: {result.cell_count}")
    console.print(f"  Min feature: {result.min_feature_mm}mm")
    console.print(f"  Est. weight: {result.estimated_weight_g:.1f}g")

    if result.passed_process_check:
        console.print("  Process check: PASS")
    else:
        console.print("  Process check: FAIL - see warnings")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--list":
        list_parts()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--validate":
        validate_all()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--modify":
        if len(sys.argv) < 4:
            print("Usage: python run_aria_os.py --modify <path_to_.py> \"modification description\"")
            sys.exit(1)
        base_part_path = sys.argv[2]
        modification = " ".join(sys.argv[3:])
        run_modify(base_part_path, modification)
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--assemble":
        if len(sys.argv) < 3:
            print("Usage: python run_aria_os.py --assemble assembly_configs/aria_clutch_assembly.json")
            sys.exit(1)
        run_assemble(sys.argv[2])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--print-scale":
        if len(sys.argv) < 4:
            print("Usage: python run_aria_os.py --print-scale <part_stub> --scale <factor>")
            sys.exit(1)
        run_print_scale(sys.argv[2:])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--optimize":
        if len(sys.argv) < 3:
            print("Usage: python run_aria_os.py --optimize <code_path> --goal <goal> [--constraint RULE ...]")
            sys.exit(1)
        run_optimize(sys.argv[2:])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--optimize-and-regenerate":
        if len(sys.argv) < 3:
            print("Usage: python run_aria_os.py --optimize-and-regenerate <code_path_or_stub> --goal <goal> [--constraint RULE ...] [--material MATERIAL_ID]")
            sys.exit(1)
        run_optimize_and_regenerate(sys.argv[2:])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--cem-full":
        run_cem_full()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--material-study":
        if len(sys.argv) < 3:
            print("Usage: python run_aria_os.py --material-study <part_name_or_stub>")
            sys.exit(1)
        run_material_study_cli(sys.argv[2])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--material-study-all":
        run_material_study_all_cli()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--lattice-test":
        run_lattice_test()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--lattice":
        if len(sys.argv) < 3:
            print(
                "Usage: python run_aria_os.py --lattice "
                "--pattern [arc_weave|honeycomb|octet_truss] "
                "--form [volumetric|conformal|skin_core] ..."
            )
            sys.exit(1)
        run_lattice(sys.argv[2:])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--generate-and-assemble":
        # Parse: --generate-and-assemble <desc...> --into PATH --as LABEL --at "x,y,z" [--rot "rx,ry,rz"]
        if len(sys.argv) < 4:
            print("Usage: python run_aria_os.py --generate-and-assemble \"part description\" --into assembly_configs/foo.json --as label --at \"x,y,z\" [--rot \"rx,ry,rz\"]")
            sys.exit(1)
        argv = sys.argv[2:]
        # Find --into as delimiter for description
        try:
            into_idx = argv.index("--into")
        except ValueError:
            print("Missing --into for --generate-and-assemble")
            sys.exit(1)
        description = " ".join(argv[:into_idx])
        into_path = None
        part_label = None
        at_vec = None
        rot_vec = None
        i = into_idx
        while i < len(argv):
            tok = argv[i]
            if tok == "--into" and i + 1 < len(argv):
                into_path = argv[i + 1]
                i += 2
            elif tok == "--as" and i + 1 < len(argv):
                part_label = argv[i + 1]
                i += 2
            elif tok == "--at" and i + 1 < len(argv):
                at_vec = argv[i + 1]
                i += 2
            elif tok == "--rot" and i + 1 < len(argv):
                rot_vec = argv[i + 1]
                i += 2
            else:
                i += 1
        if not (into_path and part_label and at_vec):
            print("Missing required flags for --generate-and-assemble (need --into, --as, --at).")
            sys.exit(1)
        run_generate_and_assemble(description, into_path, part_label, at_vec, rot_vec)
        return
    # --- --image: analyse a photo and derive a goal, then run pipeline ---
    if len(sys.argv) >= 2 and sys.argv[1] == "--image":
        if len(sys.argv) < 3:
            print("Usage: python run_aria_os.py --image <photo.jpg> [\"optional hint\"] [--preview]")
            sys.exit(1)
        _argv_rest = sys.argv[2:]
        _preview = "--preview" in _argv_rest
        _argv_clean = [a for a in _argv_rest if a != "--preview"]
        _image_path = _argv_clean[0]
        _hint = " ".join(_argv_clean[1:])
        from aria_os.llm_client import analyze_image_for_cad
        print(f"[IMAGE] Analysing {_image_path}...")
        _goal = analyze_image_for_cad(_image_path, hint=_hint, repo_root=ROOT)
        if not _goal:
            print("[IMAGE] Could not extract a goal from the image. Provide a hint with a description.")
            sys.exit(1)
        print(f"[IMAGE] Goal: {_goal}")
        from aria_os import run
        run(_goal, repo_root=ROOT, preview=_preview)
        print("Done.")
        return

    if len(sys.argv) < 2:
        print("Usage: python run_aria_os.py \"describe the part you want\"")
        print("       python run_aria_os.py --image <photo.jpg> [\"hint\"] [--preview]")
        print("       python run_aria_os.py --list")
        print("       python run_aria_os.py --validate")
        print("       python run_aria_os.py --modify <path_to_.py> \"modification\"")
        print("       python run_aria_os.py --assemble <config.json>")
        print("Example: python run_aria_os.py \"generate the ARIA housing shell\"")
        sys.exit(1)

    # Strip --preview from args before joining into goal
    _args = sys.argv[1:]
    _preview = "--preview" in _args
    _args = [a for a in _args if a != "--preview"]
    goal = " ".join(_args)
    from aria_os import run
    run(goal, repo_root=ROOT, preview=_preview)
    print("Done.")


if __name__ == "__main__":
    main()
