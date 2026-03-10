# 2026-03-10 — Blender lattice pipeline

## Files and architecture

- Created `aria_os/lattice/blender_pipeline.py`:
  - `find_blender()` tries common executables and runs `--version` to verify.
  - `run_blender_script()` runs Blender in `--background --factory-startup` with a pattern-specific script.
  - `generate_lattice(params: LatticeParams) -> LatticeResult`:
    - Validates params via `aria_os.lattice.validator.validate_params`.
    - Writes `outputs/blender_params_temp.json` with lattice params and output paths.
    - Dispatches to `aria_os/lattice/blender_scripts/{honeycomb,arc_weave,octet_truss}.py`.
    - Requires STL output to exist; optionally derives bbox from STL using `numpy-stl` if available.
    - Writes `outputs/cad/meta/<part>.json` with bbox and lattice metadata.
- Created `aria_os/lattice/blender_scripts/`:
  - `honeycomb.py`: builds a solid panel in bmesh, then boolean-cuts a grid of hexagonal voids (optionally skin_core). Exports STL in mm (internal scale meters).
  - `arc_weave.py`: builds quarter-arc struts per cell plus a rectangular frame, joins and cleans the mesh, exports STL in mm.
  - `octet_truss.py`: builds an octet truss grid (cylindrical struts plus node cross-struts) via bmesh cylinders between points, cleans, and exports STL.
- Updated `aria_os/lattice/__init__.py`:
  - Now exports `generate_lattice` from `blender_pipeline` plus `LatticeParams`/`LatticeResult`.
- Kept and reused:
  - `aria_os/lattice/params.py` (LatticeParams/LatticeResult dataclasses).
  - `aria_os/lattice/validator.py` (process limits + weight estimation).
- Deleted CadQuery-based lattice implementation:
  - `aria_os/lattice/patterns/arc_weave.py`
  - `aria_os/lattice/patterns/honeycomb.py`
  - `aria_os/lattice/patterns/octet_truss.py`
  - `aria_os/lattice/forms/skin_core.py`
  - `aria_os/lattice/forms/conformal.py`
  - `aria_os/lattice/forms/volumetric.py` (did not exist)
  - `aria_os/lattice/forms/__init__.py`
  - `aria_os/lattice/patterns/__init__.py`
  - `aria_os/lattice/generator.py`

## CLI integration

- Updated `run_aria_os.py`:
  - Added `run_lattice_test()`:
    - Uses `aria_os.lattice.blender_pipeline.find_blender()` to check installation.
    - If Blender missing, prints a clear failure message and instructions.
    - If present, exercises three quick parts via `aria_os.lattice.generate_lattice`:
      - Honeycomb volumetric (40×40×5 mm).
      - Arc weave volumetric.
      - Octet truss volumetric (30×30×30 mm).
  - Wired new flag:
    - `python run_aria_os.py --lattice-test` → `run_lattice_test()`.
  - Existing `--lattice` CLI remains:
    - Still builds `LatticeParams` from flags and now calls the Blender-backed `generate_lattice`.

## Blender installation status

- Checked `blender --version`:
  - PowerShell reported: `blender : The term 'blender' is not recognized as the name of a cmdlet...`
- Checked `where blender`:
  - Returned no paths.
- Conclusion: **Blender is NOT INSTALLED** on this system at the time of this session.
- Wrote `outputs/INSTALL_BLENDER.md` with:
  - Install instructions for Blender 4.x on Windows.
  - Verification step (`blender --version`).
  - Post-install test command: `python run_aria_os.py --lattice-test`.

## Pipeline tests (expected to fail until Blender is installed)

### 1. Lattice self-test

- Command:
  - `.venv\Scripts\python.exe run_aria_os.py --lattice-test`
- Result:
  - `[FAIL] Blender not found.`
  - Printed instructions to install Blender and rerun `--lattice-test`.

### 2. Honeycomb volumetric

- Command:
  - `.venv\Scripts\python.exe run_aria_os.py --lattice --pattern honeycomb --form volumetric --width 100 --height 80 --depth 8 --cell-size 10 --strut 2.0 --process fdm --name honeycomb_final`
- Result:
  - Printed: `Generating honeycomb volumetric lattice...`
  - Raised `RuntimeError` in `blender_pipeline.generate_lattice`:
    - `Blender not found. See outputs/INSTALL_BLENDER.md`
    - `Install from: https://www.blender.org/download/`
  - Exit code: 1.

### 3. Arc weave skin_core

- Command:
  - `.venv\Scripts\python.exe run_aria_os.py --lattice --pattern arc_weave --form skin_core --width 120 --height 80 --depth 12 --cell-size 12 --strut 1.5 --skin 2.0 --process both --name arc_weave_final`
- Result:
  - Printed: `Generating arc_weave skin_core lattice...`
  - Same `RuntimeError` as above: Blender not found.
  - Exit code: 1.

### 4. Octet truss volumetric

- Command:
  - `.venv\Scripts\python.exe run_aria_os.py --lattice --pattern octet_truss --form volumetric --width 45 --height 45 --depth 45 --cell-size 15 --strut 2.0 --process dmls --name octet_final`
- Result:
  - Printed: `Generating octet_truss volumetric lattice...`
  - Same `RuntimeError` as above: Blender not found.
  - Exit code: 1.

## Summary / Next steps

- **Status**: Code-side migration from CadQuery lattices to a Blender headless pipeline is complete:
  - CadQuery lattice modules removed.
  - Blender pipeline and scripts created and wired into `run_aria_os.py` and `aria_os.lattice`.
- **Blocker**: Blender is not currently installed, so no STL files could be generated or inspected.
- **To enable full testing**:
  1. Install Blender 4.x on Windows using `outputs/INSTALL_BLENDER.md`.
  2. Ensure `blender` is on PATH (`blender --version`).
  3. Rerun:
     - `python run_aria_os.py --lattice-test`
     - Then the individual `--lattice` pattern commands for honeycomb, arc weave, and octet truss.

