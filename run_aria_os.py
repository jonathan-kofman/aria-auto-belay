#!/usr/bin/env python3
"""ARIA-OS CLI: python run_aria_os.py \"describe the part you want\"
  --list     List all generated parts with file sizes and validation status
  --validate Re-validate all existing STEP outputs (size + re-import)
"""
import sys
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


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
    if len(sys.argv) < 2:
        print("Usage: python run_aria_os.py \"describe the part you want\"")
        print("       python run_aria_os.py --list")
        print("       python run_aria_os.py --validate")
        print("Example: python run_aria_os.py \"generate the ARIA housing shell\"")
        sys.exit(1)
    goal = " ".join(sys.argv[1:])
    from aria_os import run
    run(goal, repo_root=ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
