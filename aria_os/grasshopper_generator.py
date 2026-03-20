"""
aria_os/grasshopper_generator.py
Writes Grasshopper/rhino.compute automation artifacts.
"""
import json
from pathlib import Path
from typing import Any, Optional


def write_grasshopper_artifacts(
    plan: dict[str, Any],
    goal: str,
    step_path: str,
    stl_path: str,
    repo_root: Optional[Path] = None,
) -> dict[str, str]:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    part_slug = (plan.get("part_id") or "aria_part").replace("/", "_")
    out_dir = repo_root / "outputs" / "cad" / "grasshopper" / part_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    params_path = out_dir / "params.json"
    runner_path = out_dir / "run_rhino_compute.py"

    params = {
        "goal": goal,
        "part_id": plan.get("part_id", ""),
        "base_shape": plan.get("base_shape", {}),
        "features": plan.get("features", []),
        "step_path": step_path,
        "stl_path": stl_path,
    }
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")

    runner_path.write_text(
        f'''"""
Run with local Rhino compute server:
  python "{runner_path}"
"""
import json
from pathlib import Path

PARAMS = Path(r"{params_path}")

def main():
    print("rhino.compute runner stub")
    print("Load params:", PARAMS)
    print("Expected outputs:")
    print("  STEP:", r"{step_path}")
    print("  STL :", r"{stl_path}")
    print("Implement Rhino/Grasshopper definition call here.")

if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )

    return {"params_path": str(params_path), "runner_path": str(runner_path)}
