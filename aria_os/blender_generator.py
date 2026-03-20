"""
aria_os/blender_generator.py
Writes headless Blender script artifacts.
"""
from pathlib import Path
from typing import Any, Optional


def write_blender_artifacts(
    plan: dict[str, Any],
    goal: str,
    stl_path: str,
    repo_root: Optional[Path] = None,
) -> dict[str, str]:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    part_slug = (plan.get("part_id") or "aria_part").replace("/", "_")
    out_dir = repo_root / "outputs" / "cad" / "blender"
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / f"{part_slug}.py"

    script_path.write_text(
        f'''"""
Run:
  blender --background --python "{script_path}"
"""
import bpy
from pathlib import Path

def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = "{part_slug}"
    Path(r"{stl_path}").parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.stl_export(filepath=r"{stl_path}", export_selected_objects=False)
    print("Exported STL:", r"{stl_path}")

if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )
    return {"script_path": str(script_path)}
