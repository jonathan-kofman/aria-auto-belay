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
    out_path = assy.assemble(parts, name)
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
    if len(sys.argv) < 2:
        print("Usage: python run_aria_os.py \"describe the part you want\"")
        print("       python run_aria_os.py --list")
        print("       python run_aria_os.py --validate")
        print("       python run_aria_os.py --modify <path_to_.py> \"modification\"")
        print("       python run_aria_os.py --assemble <config.json>")
        print("Example: python run_aria_os.py \"generate the ARIA housing shell\"")
        sys.exit(1)
    goal = " ".join(sys.argv[1:])
    from aria_os import run
    run(goal, repo_root=ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
