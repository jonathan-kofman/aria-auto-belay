"""
Assemble multiple STEP parts with position/rotation and export as a single STEP/STL.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class AssemblyPart:
    step_path: str
    position: tuple  # (x, y, z) in mm
    rotation: tuple   # (rx, ry, rz) in degrees
    name: str


class Assembler:
    """Position multiple parts and export as one STEP and one STL."""

    def __init__(self, repo_root: Optional[Path] = None):
        if repo_root is None:
            repo_root = Path(__file__).resolve().parent.parent
        self.repo_root = Path(repo_root)
        self.step_dir = self.repo_root / "outputs" / "cad" / "step"
        self.stl_dir = self.repo_root / "outputs" / "cad" / "stl"
        self.step_dir.mkdir(parents=True, exist_ok=True)
        self.stl_dir.mkdir(parents=True, exist_ok=True)

    def assemble(self, parts: List[AssemblyPart], name: str) -> str:
        """
        parts: list of AssemblyPart(step_path, position, rotation, name)
        name: assembly name for output file
        Returns: path to assembly STEP file.
        """
        import cadquery as cq
        from cadquery import Assembly

        assy = Assembly(None, name=name)
        for part in parts:
            step_path = Path(part.step_path)
            if not step_path.exists():
                raise FileNotFoundError(f"STEP not found: {step_path}")
            shape = cq.importers.importStep(str(step_path))
            # Workplane or compound from importStep; Assembly.add accepts Shape or Workplane
            if hasattr(shape, "val") and shape.val() is not None:
                wp = shape
            else:
                wp = cq.Workplane("XY").add(shape)
            # Location: position (x,y,z) + rotation (rx, ry, rz) in degrees. Order: translate then rotate Z, Y, X.
            pos = cq.Vector(part.position[0], part.position[1], part.position[2])
            rx, ry, rz = part.rotation[0], part.rotation[1], part.rotation[2]
            loc = cq.Location(pos)
            if rz != 0:
                loc = loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rz)
            if ry != 0:
                loc = loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), ry)
            if rx != 0:
                loc = loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), rx)
            assy.add(wp, loc=loc, name=part.name)

        step_path = self.step_dir / f"{name}.step"
        stl_path = self.stl_dir / f"{name}.stl"
        assy.export(str(step_path), exportType="STEP")
        assy.export(str(stl_path), exportType="STL")
        return str(step_path)
