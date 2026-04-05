[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Vision](./02-the-vision.md) | [Next: The Foundation -->](./04-the-foundation.md)

---

# The Map

## Architecture Overview

ARIA-OS is a 5-phase pipeline orchestrated by the `CoordinatorAgent`. Each phase runs specialized agents in parallel where possible, with serial dependencies between phases.

```
                         USER INPUT
                            |
                    "bracket 120x60mm, 4 holes"
                            |
                    +-------v--------+
                    | CoordinatorAgent|
                    +-------+--------+
                            |
          +-----------------+-----------------+
          |                                   |
     Single Part?                        Assembly?
          |                                   |
          v                                   v
  5-Phase Pipeline                    AssemblyAgent
                                   (decompose -> generate each
                                    part -> assemble STEP)
```

---

## The 5-Phase Pipeline

```
Phase 1 ─ RESEARCH (parallel)
  ├── Materials search      "bracket material properties yield strength"
  ├── Shape search          "bracket shape geometry cross section"
  ├── Dimensions search     "bracket exact dimensions mm measurements"
  └── CAD references search "bracket 3D model CAD STEP drawing"
  
  Skip condition: >=4 dimensions already specified in the goal
  │
  v
Phase 2 ─ SYNTHESIS (serial)
  ├── SpecAgent: extract structured spec from goal text
  │   └── od_mm, bore_mm, height_mm, n_teeth, n_bolts, material, part_type, ...
  ├── Build Recipe: LLM synthesizes step-by-step CadQuery instructions from research
  └── Output: geometry_spec = { spec, cem_params, material, research_context, build_recipe }
  │
  v
Phase 3 ─ GEOMETRY + VALIDATION (serial, up to 10 iterations)
  ├── DesignerAgent generates code:
  │   ├── 1. Template match?  ──> execute directly (instant, 100% reliable)
  │   ├── 2. Zoo.dev available? -> text-to-STEP API call
  │   ├── 3. Anthropic Claude? -> LLM code gen (best quality)
  │   ├── 4. Gemini Flash?    -> LLM code gen (fast, good)
  │   ├── 5. Gemma 4 31B?     -> local LLM via Ollama
  │   └── 6. Deterministic    -> fallback template or failure
  ├── EvalAgent validates:
  │   ├── Bbox dimensions match spec
  │   ├── STEP file readable, solid count >= 1
  │   ├── STL watertight, mesh integrity
  │   └── Bore, bolt circle, bolt spacing checks
  ├── RefinerAgent (on failure):
  │   └── Injects failure context into next iteration prompt
  └── Domains: CAD (CadQuery), ECAD (KiCad), Civil (DXF)
  │
  v
Phase 4 ─ MANUFACTURING OUTPUTS (parallel, 90s timeout each)
  ├── FEA: beam bending, hoop stress, gear tooth, bolt shear
  ├── GD&T Drawing: A3 landscape SVG with 3 ortho views + title block
  ├── DFM: manufacturability score + process recommendation
  ├── Fusion 360: parametric script for Fusion API
  ├── Quote: unit cost estimate (material + machining)
  ├── Onshape: STEP upload -> live parametric model + BOM + mass properties
  └── Visual Verification: 3 rendered views -> Gemini/Claude vision -> feature PASS/FAIL
  │
  v
Phase 5 ─ FINALIZE (serial)
  ├── Record to memory system (learning from successes and failures)
  ├── MillForge bridge job (if enabled)
  └── Summary report with all output paths
```

---

## Key Modules

### Entry Points

| Module | Role |
|---|---|
| `run_aria_os.py` | CLI entry point, argument parsing, dispatches to orchestrator or coordinator |
| `aria_os/agents/coordinator.py` | 5-phase pipeline orchestrator, never generates geometry directly |
| `aria_os/api_server.py` | FastAPI server: `POST /api/generate`, `GET /api/health`, `GET /api/runs` |

### Agent System (`aria_os/agents/`)

| Agent | Phase | Responsibility |
|---|---|---|
| `CoordinatorAgent` | All | Decomposes goal, delegates to workers, manages phases |
| `SpecAgent` | 2 | Extracts structured spec dict from natural language |
| `DesignerAgent` | 3 | Generates CadQuery/CAM/ECAD code (template or LLM) |
| `EvalAgent` | 3 | Validates generated geometry (bbox, STEP, STL, dimensional) |
| `RefinerAgent` | 3 | Analyzes failures, produces refinement instructions |
| `AssemblyAgent` | 1-5 | Detects multi-part goals, decomposes, generates all parts |
| `DFMAgent` | 4 | Manufacturability analysis (machinability, thin walls, undercuts) |
| `QuoteAgent` | 4 | Cost estimation (material + machining time) |
| `OnshapeBridge` | 4 | STEP upload, translation, metadata, BOM, drawing in Onshape |

### Generation Layer

| Module | Role |
|---|---|
| `generators/cadquery_generator.py` | 49 CadQuery templates + fuzzy matching (205 aliases, 59 keyword entries) |
| `zoo_bridge.py` | Zoo.dev text-to-STEP API integration |
| `llm_client.py` | Unified LLM client: Anthropic, Gemini, Gemma 4, Ollama |
| `cad_operations_reference.py` | 25 tested CadQuery operation snippets injected into LLM prompts |
| `spec_extractor.py` | Regex-based dimensional extraction from natural language |
| `visual_verifier.py` | Render 3 views, send to vision AI, parse feature-level results |

### Validation Layer

| Module | Role |
|---|---|
| `post_gen_validator.py` | Bbox check, STEP re-import, mesh integrity, bore detection, repair |
| `validator.py` | Bbox check, STEP solid count, housing spec validation |
| `clearance_checker.py` | Post-assembly interpenetration and tight-clearance detection |
| `cem_checks.py` | Per-part physics safety factor checks (SF < 1.5 = hard fail) |

### Output Layer

| Module | Role |
|---|---|
| `drawing_generator.py` | A3 landscape SVG: 3 ortho views, GD&T symbols, title block |
| `cam_generator.py` | Fusion 360 CAM Python script (adaptive clearing, parallel finish, contour, drill) |
| `cam_validator.py` | Machinability checks: radii, cavity depth, thin walls, undercuts |
| `cam_setup.py` | CNC operator setup sheet (markdown + JSON) |
| `cam_physics.py` | Feed/speed validation: MRR, power, surface finish, deflection |
| `exporter.py` | STEP + STL export to `outputs/cad/` |

### ECAD Domain (`aria_os/ecad/`)

KiCad PCB generation from natural language board descriptions.

```
"ESP32 sensor board, 80x60mm, 12V, UART, BLE, HX711"
  → parse board dims + select components (11 types)
    → place components on board (auto-layout)
      → wire MCU GPIOs to peripherals (30 nets, 29 traces)
        → validate (ERC + DRC + SPICE DC check)
          → outputs: pcbnew.py script + BOM JSON + validation.json
```

| Feature | Details |
|---|---|
| Component types | ESP32-S3, STM32-LQFP64, AMS1117, barrel jack, USB-C, JST-XH, HX711, passives |
| Pad generation | Real pads per component (38 on ESP32, 65 on STM32, PTH + SMD) |
| Net routing | Star topology per net, power 0.5mm / signal 0.25mm traces |
| Ground pour | B.Cu zone with thermal relief |
| Firmware pins | Auto-extracted from `#define PIN_*` in STM32/ESP32 source |
| Validation | ERC (electrical rules), DRC (design rules), SPICE DC + power-on |
| Variant study | Compare multiple board configurations side-by-side |

### Civil Engineering Domain (`aria_os/autocad/`)

Headless DXF generation for civil engineering disciplines. No AutoCAD needed — uses ezdxf.

```
"storm drainage plan for 25-acre subdivision" --state TX --discipline drainage
  → LLM interprets plan description → extract parameters
    → load state DOT standards (all 50 states + AASHTO national)
      → generate discipline-specific plan (manholes, pipes, inlets)
        → outputs: .dxf file + .json sidecar with standards applied
```

| Discipline | What It Generates |
|---|---|
| Transportation | Road plans, lane markings, intersections, sidewalks, bike lanes |
| Drainage | Manholes, trunk/branch pipes, curb inlets, detention basins, HGL profiles |
| Grading | Contour lines, cut/fill, retaining walls, FFE annotations |
| Utilities | Water/sewer/gas/electric corridors, fire hydrants, meter vaults |
| Site | Lot layout, building footprint, parking, ADA stalls, loading zones |

| Feature | Details |
|---|---|
| State standards | All 50 states + DC: frost depth, seismic category, wind speed, min pipe cover |
| Layer system | 50+ NCS-compliant layers per discipline |
| CEM integration | Manning's pipe sizing, Bishop slope stability, Coulomb retaining wall analysis |
| Text scaling | Plot-scale-aware (1"=40' default) with 4 size constants |

---

## Data Flow

```
goal (string)
  |
  v
spec_extractor.extract_spec(goal)
  -> { od_mm: 120, bore_mm: 30, n_bolts: 4, part_type: "bracket", ... }
  |
  v
cadquery_generator._find_template_fuzzy(part_type, goal, spec)
  -> (template_fn, match_type)  -- "exact" | "keyword" | "goal" | "fuzzy"
  |
  v
template_fn(spec)  -- or LLM code generation with operations reference
  -> CadQuery Python script (string)
  |
  v
exec(script)  -- in-process CadQuery execution
  -> result = cq.Workplane(...)
  -> STEP file, STL file, bbox
  |
  v
post_gen_validator.check_geometry(stl_path, spec)
  -> { passed: true, failures: [], bore_detected: true, ... }
  |
  v
visual_verifier.verify_visual(step_path, stl_path, goal, spec)
  -> { verified: true, confidence: 0.92, checks: [...] }
  |
  v
[Phase 4 parallel outputs]
  -> drawing.svg, cam_script.py, setup_sheet.md, dfm_report.json, quote.json, onshape_url
```

---

## Template Matching Flow

The template engine uses a 4-tier matching strategy to maximize hit rate:

```
Input: part_id="motor_mount", goal="NEMA 23 motor mount 8mm thick", spec={...}
  |
  v
Tier 1: EXACT — Is "motor_mount" a key in _CQ_TEMPLATE_MAP?
  -> Yes: _cq_flange (motor_mount maps to flange template)
  -> Return (fn, "exact")
  |
  v (if no exact match)
Tier 2: KEYWORD — Does part_id appear in any _KEYWORD_TO_TEMPLATE entry?
  -> Scans 59 keyword lists: ["motor_mount", "motor mount", "servo_mount", ...]
  -> Return (fn, "keyword")
  |
  v (if no keyword match)
Tier 3: GOAL — Does the full goal text match any keyword list entry?
  -> "NEMA 23 motor mount" contains "motor_mount"
  -> Return (fn, "goal")
  |
  v (if no goal match)
Tier 4: FUZZY — Word-overlap scoring between goal tokens and keyword lists
  -> Best overlap score wins
  -> Used as LLM reference template (not executed directly)
  -> Return (fn, "fuzzy")
```

> **Tip:** Tier 4 (fuzzy) matches store the template as a code reference for the LLM prompt rather than executing it directly. This prevents incorrect geometry from a poor match while still giving the LLM a tested starting point.

---

## API Surface

### CLI (`run_aria_os.py`)

The primary interface. See [08 Operations](./08-operations.md) for full command reference.

### REST API (`aria_os/api_server.py`)

```
POST /api/generate     { "description": "...", "dry_run": false }
GET  /api/health       -> { backends: { cadquery, grasshopper, blender, fusion360 } }
GET  /api/runs?limit=N -> last N run log entries
```

Run with: `uvicorn aria_os.api_server:app`

### Python API

```python
from aria_os.agents.coordinator import CoordinatorAgent
import asyncio

agent = CoordinatorAgent(repo_root=Path("."))
ctx = asyncio.run(agent.run("aluminium bracket 120x60x8mm, 4x M6 holes"))

print(ctx.geometry_path)        # outputs/cad/step/aluminium_bracket_120x60x8mm.step
print(ctx.validation_passed)    # True
print(ctx.validation_report)    # { converged, iterations, failures, bbox }
```

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Vision](./02-the-vision.md) | [Next: The Foundation -->](./04-the-foundation.md)
