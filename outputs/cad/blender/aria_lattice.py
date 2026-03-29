"""
Run:
  blender --background --python "C:\Users\jonko\Downloads\aria-auto-belay\outputs\cad\blender\aria_lattice.py"
"""
import bpy
from pathlib import Path

def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = "aria_lattice"
    Path(r"C:\Users\jonko\AppData\Local\Temp\pytest-of-jonko\pytest-0\test_lattice_contains_bpy_refe0\x.stl").parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.stl_export(filepath=r"C:\Users\jonko\AppData\Local\Temp\pytest-of-jonko\pytest-0\test_lattice_contains_bpy_refe0\x.stl", export_selected_objects=False)
    print("Exported STL:", r"C:\Users\jonko\AppData\Local\Temp\pytest-of-jonko\pytest-0\test_lattice_contains_bpy_refe0\x.stl")

if __name__ == "__main__":
    main()
