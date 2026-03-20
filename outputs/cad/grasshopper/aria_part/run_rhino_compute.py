"""
Run with local Rhino compute server:
  python "C:\Users\jonko\Downloads\aria-auto-belay\outputs\cad\grasshopper\aria_part\run_rhino_compute.py"
"""
import json
from pathlib import Path

PARAMS = Path(r"C:\Users\jonko\Downloads\aria-auto-belay\outputs\cad\grasshopper\aria_part\params.json")

def main():
    print("rhino.compute runner stub")
    print("Load params:", PARAMS)
    print("Expected outputs:")
    print("  STEP:", r"C:\Users\jonko\Downloads\aria-auto-belay\outputs\cad\step\aria_part.step")
    print("  STL :", r"C:\Users\jonko\Downloads\aria-auto-belay\outputs\cad\stl\aria_part.stl")
    print("Implement Rhino/Grasshopper definition call here.")

if __name__ == "__main__":
    main()
