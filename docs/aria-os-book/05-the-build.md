[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Foundation](./04-the-foundation.md) | [Next: Integrations -->](./06-integrations.md)

---

# The Build

## Development Environment Setup

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| pip | latest | Package management |
| Git | 2.30+ | Version control |
| Ollama | latest (optional) | Local LLM inference |

### First-Time Setup

```bash
# Clone the repository
git clone <repo-url> aria-auto-belay
cd aria-auto-belay

# Install ARIA-OS dependencies
pip install -r requirements_aria_os.txt

# (Optional) Create .env with API keys
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
ZOO_API_TOKEN=zoo-...
ONSHAPE_ACCESS_KEY=...
ONSHAPE_SECRET_KEY=...
EOF

# (Optional) Install and pull Ollama models for local inference
# Download from https://ollama.com
ollama pull qwen2.5-coder:7b    # spec extraction, routing (7B, ~4GB)
ollama pull gemma4:31b           # code generation (31B, ~18GB, needs GPU)
```

> **Tip:** You can run ARIA-OS with zero API keys. The pipeline will use templates for known parts and Ollama for LLM tasks. Set at least `GOOGLE_API_KEY` (free tier) for the best experience without cost.

### Verify Installation

```bash
# Quick test: generate a bracket using a template (no API key needed)
python run_aria_os.py "bracket 100x60x8mm"

# Should output:
#   [SPEC] part_type=bracket, width_mm=100, height_mm=60, thickness_mm=8
#   [DesignerAgent[cad]] Using template for 'bracket' with agent params
#   [DesignerAgent[cad]] Generated STEP (12KB) bbox: {'x': 100.0, 'y': 60.0, 'z': 8.0}
```

---

## First Run Walkthrough

### Generate a single part (template path)

```bash
python run_aria_os.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
```

This will:
1. Extract spec: `od_mm=213, n_teeth=24, thickness_mm=21, part_type=ratchet_ring`
2. Match template: `_cq_ratchet_ring` (exact match)
3. Generate CadQuery script with computed tooth geometry
4. Execute the script, export STEP + STL
5. Validate: bbox check, STEP readability, mesh integrity

### Generate with full pipeline (all outputs)

```bash
python run_aria_os.py --full "aluminium bracket 120x60x8mm with 4x M6 holes"
```

This adds Phase 4 manufacturing outputs: FEA, drawing, DFM, Fusion 360 script, cost estimate, Onshape upload, and visual verification.

### Generate from an image

```bash
python run_aria_os.py --image photo_of_bracket.jpg "it's a mounting bracket"
```

Vision AI extracts a goal description from the photo, then the standard pipeline runs.

### Run the coordinator (5-phase agent pipeline)

```bash
python run_aria_os.py --coordinator "titanium flange 80mm OD, 6x M5 bolt circle"
```

This runs the full CoordinatorAgent pipeline with web research, synthesis, multi-iteration generation, and parallel manufacturing outputs.

---

## Project Structure

```
aria-auto-belay/
  aria_os/                    # Main pipeline package
    agents/                   # Agent system (coordinator, designer, spec, eval, refiner)
      coordinator.py          # 5-phase pipeline orchestrator
      designer_agent.py       # Template + LLM code generation
      spec_agent.py           # Structured spec extraction agent
      eval_agent.py           # Geometry validation agent
      refiner_agent.py        # Failure analysis + refinement
      assembly_agent.py       # Multi-part assembly decomposition
      onshape_bridge.py       # Onshape API integration
      dfm_agent.py            # DFM manufacturability analysis
      quote_agent.py          # Cost estimation
    generators/
      cadquery_generator.py   # 49 templates, 205 aliases, 59 keyword entries
      fusion_generator.py     # Fusion 360 API script generation
    autocad/                  # Civil engineering DXF generation
    ecad/                     # KiCad PCB generation
    gh_integration/           # Grasshopper/Rhino integration
    llm_client.py             # Unified LLM client (6-level fallback)
    zoo_bridge.py             # Zoo.dev text-to-STEP
    visual_verifier.py        # Vision AI geometry verification
    spec_extractor.py         # Regex spec extraction
    cad_operations_reference.py  # 25 tested CadQuery operations
    drawing_generator.py      # GD&T SVG engineering drawings
    cam_generator.py          # Fusion 360 CAM scripts
    cam_validator.py          # Machinability checks
    cam_setup.py              # CNC setup sheets
    cam_physics.py            # Feed/speed validation
    physics_analyzer.py       # FEA + CFD screening
    exporter.py               # STEP + STL export
    validator.py              # Bbox + STEP validation
    post_gen_validator.py     # Deep geometry validation + repair
    clearance_checker.py      # Assembly clearance analysis
    api_server.py             # FastAPI REST API
  cem/                        # Computational Engineering Models
  context/                    # Mechanical constants + failure patterns
  contracts/                  # JSON Schema for output validation
  outputs/                    # Generated artifacts (STEP, STL, drawings, CAM)
  tests/                      # Test suite
  run_aria_os.py              # CLI entry point
  batch.py                    # Batch generation from JSON part lists
  assemble.py                 # Assembly from JSON config
```

---

## Testing

### Unit Tests

```bash
# Full test suite
python -m pytest tests/ -q

# Specific test files
python -m pytest tests/test_cad_router.py -q         # Multi-backend routing + 14 template smoke tests
python -m pytest tests/test_spec_extractor.py -q      # 40 spec extraction tests
python -m pytest tests/test_post_gen_validator.py -q   # Validation loop + STEP/STL quality
python -m pytest tests/test_api_server.py -q           # FastAPI: 422 validation, health, run log
python -m pytest tests/test_output_contracts.py -q     # 20 JSON Schema contract tests
python -m pytest tests/test_e2e_pipeline.py -q         # 5 end-to-end descriptions, one per backend
```

### Static Tests

```bash
python aria_models/static_tests.py        # State machine + physics unit tests
```

### Integration Tests

```bash
python tools/aria_test_harness.py         # Automated scenario PASS/FAIL
```

### What the Tests Cover

| Test File | Count | What It Validates |
|---|---|---|
| `test_spec_extractor.py` | 40 | Dimension patterns, material keywords, part type detection, WxHxD notation |
| `test_cad_router.py` | 14+ | Template routing for all backends, smoke tests for template output |
| `test_post_gen_validator.py` | varies | Validation loop retries, STEP readability, STL repair, bore detection |
| `test_api_server.py` | varies | Pydantic 422 rejection, health endpoint, run log persistence |
| `test_output_contracts.py` | 20 | JSON Schema validation for setup sheets and BOM outputs |
| `test_e2e_pipeline.py` | 5 | End-to-end: cadquery (bracket, ratchet), grasshopper (cam collar), blender (lattice), fusion (motor housing) |

---

## Dashboard

The Streamlit dashboard provides a web UI for generation, visualization, and CEM parameter tuning.

```bash
# Windows (auto-setup)
scripts/START_DASHBOARD.bat

# Manual
pip install -r requirements.txt
streamlit run aria_dashboard.py
```

The dashboard includes:
- Part generation from text input
- 3D STL preview (Three.js embedded)
- CEM parameter tuning with CSV export for Fusion 360
- Generation log viewer
- Validation status per part

---

## Session Logging

Every pipeline run appends to `sessions/YYYY-MM-DD_task.md`:

```markdown
## Session 2026-03-31T14:22:00
**Status:** Success
**Goal:** aluminium bracket 120x60x8mm with 4x M6 holes
**Attempts:** 1
**Output STEP:** outputs/cad/step/aluminium_bracket.step
```

On failure after 3 attempts, diagnosis is written to the session file and `context/aria_failures.md` is updated with the new failure pattern.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Foundation](./04-the-foundation.md) | [Next: Integrations -->](./06-integrations.md)
