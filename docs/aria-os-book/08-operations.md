[<-- Back to Table of Contents](./README.md) | [<-- Previous: Gotchas](./07-gotchas.md) | [Next: Roadmap -->](./09-roadmap.md)

---

# Operations

## CLI Quick Reference

### Part Generation

```bash
# Basic generation (natural language goal)
python run_aria_os.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"

# Full pipeline: generate + FEA + GD&T drawing + render + CAM + setup sheet
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD" --machine "HAAS VF2"

# Generate from a photo
python run_aria_os.py --image photo.jpg "it's a bracket"

# Preview in 3D browser before export
python run_aria_os.py --preview "aluminium bracket 100x60x8mm"

# Modify an existing part
python run_aria_os.py --modify outputs/cad/generated_code/aria_spool.py "add 6x M6 bolt circle at 90mm radius"
```

### Validation and Analysis

```bash
# List all generated parts with status
python run_aria_os.py --list

# Re-validate all STEP files
python run_aria_os.py --validate

# Run CEM physics check on all parts
python run_aria_os.py --cem-full

# Material study for a part
python run_aria_os.py --material-study aria_ratchet_ring
python run_aria_os.py --material-study-all

# Run FEA or CFD on a specific STEP file
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step --fea
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step --cfd
```

### Manufacturing Outputs

```bash
# GD&T engineering drawing SVG
python run_aria_os.py --draw outputs/cad/step/aria_spool.step

# Fusion 360 CAM script
python run_aria_os.py --cam outputs/cad/step/aria_housing.step --material aluminium_6061

# Machinability check (undercut detection, axis classification)
python run_aria_os.py --cam-validate outputs/cad/step/aria_housing.step

# CNC setup sheet (markdown + JSON)
python run_aria_os.py --setup outputs/cad/step/aria_housing.step outputs/cam/aria_housing/aria_housing_cam.py
```

### Optimization

```bash
# Parametric optimizer
python run_aria_os.py --optimize aria_spool --goal minimize_weight --constraint "SF>=2.0"

# Optimize then regenerate CAD with best result
python run_aria_os.py --optimize-and-regenerate aria_spool --goal minimize_weight --material 6061_al

# Print-fit scaling check
python run_aria_os.py --print-scale aria_ratchet_ring --scale 0.75
```

### Assembly

```bash
# Assembly from JSON config
python run_aria_os.py --assemble assembly_configs/aria_clutch_assembly.json

# Fusion 360 constrained assembly script
python run_aria_os.py --constrain assembly_configs/clock_gear_train.json --proximity 50

# Generate and add to existing assembly
python run_aria_os.py --generate-and-assemble "pump housing" --into assembly_configs/foo.json --as pump_housing --at "0,0,10"
```

### Batch Generation

```bash
# Generate all parts from a JSON list
python batch.py parts/clock_parts.json

# Skip already-generated parts
python batch.py parts/clock_parts.json --skip-existing

# Filter to specific parts
python batch.py parts/clock_parts.json --only "escape" --workers 4

# Generate with PNG previews
python batch.py parts/clock_parts.json --render
```

### Specialized Domains

```bash
# ECAD: KiCad PCB generation
python run_aria_os.py --ecad "ARIA ESP32 board, 80x60mm, 12V, UART, BLE, HX711"

# ECAD variant study
python run_aria_os.py --ecad-variants "ARIA ESP32 board, 80x60mm" --variants variants/aria_board_variants.json

# Civil engineering DXF
python run_aria_os.py --autocad "drainage plan" --state TX --discipline drainage

# Lattice generation (Blender)
python run_aria_os.py --lattice --pattern honeycomb --form volumetric --width 100 --height 100 --depth 10

# Scenario: decompose real-world situation into parts
python run_aria_os.py --scenario "a climber takes a lead fall on a 15m route"

# System: full machine design
python run_aria_os.py --system "design a desktop CNC router 300x300x100mm"
```

### Dashboard

```bash
# Windows (auto-setup)
scripts/START_DASHBOARD.bat

# Manual
streamlit run aria_dashboard.py
```

### API Server

```bash
uvicorn aria_os.api_server:app --host 0.0.0.0 --port 8000
```

---

## Running the Coordinator (5-Phase Agent Pipeline)

The coordinator is the most powerful mode. It runs all 5 phases:

```bash
python run_aria_os.py --coordinator "titanium flange 80mm OD, 6x M5 bolt circle"
```

What happens:
1. **Phase 1:** 4 parallel web searches for materials, shape, dimensions, CAD references
2. **Phase 2:** SpecAgent extracts params, LLM builds step-by-step build recipe
3. **Phase 3:** DesignerAgent generates geometry (template or LLM), EvalAgent validates, RefinerAgent retries (up to 10 iterations)
4. **Phase 4:** 7 parallel outputs (FEA, drawing, DFM, Fusion, quote, Onshape, visual verification)
5. **Phase 5:** Memory record, MillForge bridge, summary

Output example:
```
================================================================
  COORDINATOR -- Job a1b2c3d4e5f6
  Goal: titanium flange 80mm OD, 6x M5 bolt circle
================================================================

  [Phase 1] Skipping research -- 4 dimensions already specified

  [Phase 2] Spec: 8 params, material: titanium_6al4v
  [Phase 2] Build recipe: 1240 chars

  [Phase 3] PASS -- 1 iterations, 0 failures

  [Phase 4] FEA: PASS SF=3.2
  [Phase 4] Drawing: outputs/drawings/titanium_flange.svg
  [Phase 4] DFM: Score: 78/100 -- CNC milling recommended
  [Phase 4] Fusion: outputs/cad/fusion_scripts/titanium_flange.py
  [Phase 4] Quote: $42.50
  [Phase 4] Onshape: https://cad.onshape.com/documents/...
  [Phase 4] Visual: PASS (92% confidence, 5/5 features)

  [Phase 5] Finalizing...

  ================================ SUMMARY ================================
  Job:        a1b2c3d4e5f6
  Status:     PASS
  Time:       34.2s
  STEP:       outputs/cad/step/titanium_flange.step
  Phases:     research, synthesis, geometry, manufacturing, finalize
  =========================================================================
```

---

## Adding a New CadQuery Template

To add support for a new part type:

### Step 1: Write the template function

```python
# In aria_os/generators/cadquery_generator.py

def _cq_my_new_part(params: dict[str, Any]) -> str:
    width  = float(params.get("width_mm", 100.0))
    height = float(params.get("height_mm", 50.0))
    # ... extract all relevant params with defaults

    return f"""
import cadquery as cq

WIDTH_MM  = {width}
HEIGHT_MM = {height}

result = cq.Workplane("XY").box(WIDTH_MM, HEIGHT_MM, 10.0)
bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.3f}},{{bb.ylen:.3f}},{{bb.zlen:.3f}}")
"""
```

### Step 2: Add to `_CQ_TEMPLATE_MAP`

```python
_CQ_TEMPLATE_MAP: dict[str, Any] = {
    # ...existing entries...
    "my_new_part":     _cq_my_new_part,
    "alias_one":       _cq_my_new_part,
    "alias_two":       _cq_my_new_part,
}
```

### Step 3: Add keyword entries for fuzzy matching

```python
_KEYWORD_TO_TEMPLATE: list[tuple[list[str], Any]] = [
    # ...existing entries...
    (["my_new_part", "my new part", "alias_one", "alias one"], _cq_my_new_part),
]
```

### Step 4: Add part type detection in `spec_extractor.py`

```python
_PART_TYPE_KEYWORDS: list[tuple[str, str]] = [
    # ...existing entries...
    ("my new part",   "my_new_part"),
    ("alias one",     "my_new_part"),
]
```

### Step 5: Test

```bash
python run_aria_os.py "my new part 100x50mm"
# Should hit template path, generate in <5 seconds
```

---

## Tuning the Validation Layer

### Bbox Tolerance

The bbox validator uses a default tolerance of +/-10%. To adjust:

```python
# In post_gen_validator.py
check_geometry(stl_path, spec, tolerance=0.15)  # 15% tolerance
```

### Bore Detection Threshold

Bore detection uses a spec-derived threshold when bore_mm and od_mm are known:

```
threshold = 1 - (bore_mm / od_mm)^2 * 0.5
```

For unknown bore dimensions, the fixed threshold is 0.65. Adjust in `_detect_bore()`.

### Visual Verification Confidence

The vision API returns a confidence score (0.0-1.0). Current threshold for PASS is implicit (the vision model decides `overall_match`). To add a confidence gate:

```python
result = verify_visual(step_path, stl_path, goal, spec)
if result["confidence"] < 0.7:
    result["verified"] = False  # reject low-confidence passes
```

---

## Output Files Reference

After a full pipeline run, these files are produced:

```
outputs/
  cad/
    step/<part_id>.step           # Production-ready STEP solid
    stl/<part_id>.stl             # Mesh for preview/3D printing
    generated_code/<part_id>.py   # CadQuery script that generated the part
    meta/<part_id>.json           # Version metadata: goal, params, CEM SF, bbox, git SHA
    fusion_scripts/<part_id>.py   # Fusion 360 parametric API script
    fusion_scripts/<part_id>.json # Fusion 360 part metadata
  cam/<part_id>/
    <part_id>_cam.py              # Fusion 360 CAM script
    setup_sheet.md                # CNC operator setup (markdown)
    setup_sheet.json              # CNC operator setup (machine-readable)
    machinability.json            # DFM analysis results
  drawings/
    <part_id>.svg                 # GD&T engineering drawing (A3 landscape)
  screenshots/
    <part_id>.png                 # PNG render of STL
  ecad/<board>/
    <board>_pcbnew.py             # KiCad scripting console script
    <board>_bom.json              # Bill of materials
    validation.json               # ERC/DRC results
```

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: Gotchas](./07-gotchas.md) | [Next: Roadmap -->](./09-roadmap.md)
