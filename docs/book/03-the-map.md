# The Map

## Architecture Overview

ARIA-OS is a multi-stage pipeline that converts a natural language part description into validated, machinable geometry. The pipeline has two modes: the **classic orchestrator** (serial, deterministic) and the **coordinator agent** (parallel, research-augmented).

### Classic Pipeline (orchestrator.py)

```
Goal string
    |
    v
[1] Spec Extraction ---- aria_os/spec_extractor.py
    |   Parses "213mm OD, 24 teeth" into {od_mm: 213, n_teeth: 24}
    v
[2] Planning ----------- aria_os/planner.py
    |   Goal -> structured plan dict (part_id, params, base_shape)
    |   Detects dimensional overrides vs template defaults
    v
[3] Tool Routing ------- aria_os/tool_router.py
    |   Routes to cadquery / grasshopper / blender / fusion360 / autocad
    |   Based on goal keywords, part_id, and feature detection
    v
[4] CEM Physics -------- cem/cem_registry.py -> cem/cem_aria.py or cem/cem_lre.py
    |   Physics-derived geometry: tooth shear SF, hoop stress, bending
    |   Deterministic -- no LLM in this path
    v
[5] Template Match ----- aria_os/generators/cadquery_generator.py
    |   39 templates, 172+ aliases
    |   Falls back to LLM if no template matches
    v
[6] Code Generation ---- CadQuery script (or Fusion/GH/Blender script)
    |   Templates inject exact dimensions from spec + CEM
    |   LLM gets engineering brief with CEM outputs + failure patterns
    v
[7] Execution ---------- CadQuery in-process, STEP + STL export
    |
    v
[8] Validation Loop ---- aria_os/post_gen_validator.py
    |   Bbox check, solid count, bore detection, watertight mesh
    |   Up to 3 retries with failure-context injection
    v
[9] Visual Verification  aria_os/visual_verifier.py
    |   3 rendered views -> vision LLM -> feature checklist pass/fail
    v
[10] Onshape Upload ---- aria_os/agents/onshape_bridge.py
    |   Create document, upload STEP, add metadata, generate drawing
    v
[11] DFM + Quote ------- aria_os/agents/dfm_agent.py, quote_agent.py
    |   Wall thickness, undercut detection, material compatibility
    v
[12] Export + Log ------ outputs/cad/step/, outputs/cad/meta/
```

### Coordinator Agent Pipeline (agents/coordinator.py)

The coordinator decomposes requests into 5 parallel phases:

```
Phase 1 (parallel):  Research -- materials, shape, dimensions, CAD references
Phase 2 (serial):    Synthesize spec from research + user description
Phase 3 (serial):    GeometryAgent -> EvalAgent (with refinement loop)
Phase 4 (parallel):  Onshape upload + DFM analysis + Quote (if geometry exists)
Phase 5 (serial):    Final assembly, MillForge bridge
```

### Key Files and Their Roles

| File | Role |
|------|------|
| `run_aria_os.py` | CLI entry point -- all flags route through here |
| `aria_os/orchestrator.py` | Classic pipeline controller with checkpoint system |
| `aria_os/agents/coordinator.py` | Parallel agent pipeline with 5-phase decomposition |
| `aria_os/spec_extractor.py` | NL description -> typed dimension dict (od_mm, bore_mm, etc.) |
| `aria_os/planner.py` | Goal -> plan dict; template vs LLM routing decision |
| `aria_os/tool_router.py` | Backend selection: cadquery / grasshopper / blender / fusion / autocad |
| `aria_os/generators/cadquery_generator.py` | 3,473-line file: 39 template functions + LLM fallback (the workhorse) |
| `aria_os/llm_client.py` | Unified LLM client: Anthropic -> Gemini -> Ollama -> None |
| `aria_os/post_gen_validator.py` | Validation loop: bbox, solid count, bore, watertight, up to 3 retries |
| `aria_os/visual_verifier.py` | Headless STL render -> vision LLM -> feature checklist verification |
| `aria_os/agents/onshape_bridge.py` | Onshape REST API: create doc, upload STEP, metadata, BOM, drawings |
| `aria_os/agents/eval_agent.py` | Domain validators: solid count, geometry, CEM physics, DFM |
| `aria_os/agents/designer_agent.py` | LLM-driven CadQuery code generation with constraint injection |
| `aria_os/agents/refinement_loop.py` | Multi-attempt refinement: eval -> diagnose -> refine -> re-eval |
| `aria_os/agents/dfm_agent.py` | Design for manufacturability analysis |
| `aria_os/agents/quote_agent.py` | Manufacturing cost estimation |
| `aria_os/cad_prompt_builder.py` | Builds engineering brief for LLM from CEM + context |
| `aria_os/context_loader.py` | Loads context/*.md into every LLM prompt |
| `cem/cem_registry.py` | Maps goal keywords to CEM physics modules |
| `cem/cem_aria.py` | ARIA auto-belay CEM: tooth shear, hoop stress, bending |
| `cem/cem_lre.py` | Liquid rocket engine CEM: nozzle geometry from thrust + Pc |
| `cem/cem_to_geometry.py` | CEM scalars -> deterministic CadQuery scripts (no LLM) |

### Template Matching Flow

The template resolver in `cadquery_generator.py` uses 4 levels of progressively looser matching:

1. **Exact map lookup**: `_CQ_TEMPLATE_MAP[part_id]` -- 172+ entries mapping part IDs and aliases to 39 template functions.
2. **Keyword scan of part_id**: `_KEYWORD_TO_TEMPLATE` list -- checks if any keyword substring appears in the part_id.
3. **Spec part_type lookup**: If `spec_extractor` identified a `part_type`, look that up in the template map.
4. **Fuzzy word-overlap**: Tokenize the goal string and score overlap against keyword lists. Best match wins if score exceeds threshold.

If all 4 levels fail, the system falls back to LLM generation via `aria_os/llm_client.py`.

### Backend Routing Priority

`tool_router.py` checks backends in this order:
1. **AutoCAD** (highest priority): road plan, drainage, grading, site plan, dxf keywords
2. **Grasshopper**: 6 core ARIA parts (spool, cam collar, housing, ratchet ring, brake drum, rope guide)
3. **Blender**: lattice, gyroid, voronoi, organic shapes
4. **Fusion 360**: motor housing, complex assemblies (requires Fusion desktop)
5. **CadQuery** (default): everything else -- headless, no external software needed
