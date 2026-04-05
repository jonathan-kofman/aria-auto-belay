[<-- Back to Table of Contents](./README.md) | [Next: The Why -->](./01-the-why.md)

---

# Elevator Pitch

## What Is ARIA-OS?

ARIA-OS is an AI-driven CAD pipeline that generates production-ready 3D mechanical parts from plain English descriptions. You type a sentence. You get a STEP file, an engineering drawing, a CNC setup sheet, and a live parametric model in Onshape.

```
Input:  "aluminium bracket 120x60x8mm with 4x M6 holes on 80mm bolt circle"
Output: STEP + STL + GD&T drawing + Fusion 360 CAM script + operator setup sheet
Time:   8-45 seconds (depending on LLM backend)
```

ARIA-OS is not a chatbot that writes CadQuery code. It is a multi-agent pipeline with five phases: research, specification synthesis, geometry generation with validation, manufacturing outputs, and Onshape integration. Every generated part goes through dimensional verification, visual inspection by a vision model, and physics checks before export.

---

## Who Is It For?

| Audience | What They Get |
|---|---|
| **Mechanical engineers** | Skip the first 80% of CAD work. Describe a part, refine the output. |
| **Hardware startups** | Rapid prototyping without a full-time CAD operator. |
| **Manufacturers** | Automated quoting: STEP + DFM analysis + cost estimate from a text description. |
| **Developers** | Extensible pipeline: add templates, plug in new backends, customize validation. |

---

## What Does It Replace?

Today, going from "I need a bracket" to a machinable STEP file takes 15-60 minutes of manual CAD work. ARIA-OS replaces that manual loop with a pipeline that:

1. Parses the description into structured specs (49 templates, 205 aliases)
2. Generates CadQuery geometry (template or LLM-generated)
3. Validates dimensions, bore placement, bolt spacing, watertight mesh
4. Renders 3 views and sends them to a vision model for feature-level verification
5. Exports to STEP, STL, Onshape, Fusion 360, and GD&T engineering drawing

---

## Key Metrics

| Metric | Value |
|---|---|
| Templates | 49 CadQuery templates covering common mechanical parts |
| Template aliases | 205 (map natural language to the right template) |
| Keyword entries | 59 (fuzzy matching for slug-based part IDs) |
| CadQuery operations | 25 tested operations (sweep, loft, revolve, shell, fillet, chamfer, etc.) |
| Stress test pass rate | 8/10 (10/10 with Claude API credits) |
| Generation time | 2-8s (template), 15-45s (LLM), 30-120s (Zoo.dev) |
| Dimensional accuracy | Bore: +/-0.0%, Bolt circle: +/-0.0%, Bolt spacing uniformity: +/-0.0% |
| Validation layers | 4 (spec extraction, bbox check, mesh integrity, visual verification) |
| LLM fallback chain | 6 levels (Template, Zoo.dev, Claude, Gemini Flash, Gemma 4, Deterministic) |
| External integrations | 6 (Onshape, Zoo.dev, Anthropic, Google, Lightning AI, MillForge) |

---

## The Pipeline at a Glance

```
"aluminium bracket 120x60mm, 4x M6 holes"
            |
     [Phase 1: Research]         4 parallel web searches (materials, shape, dims, CAD refs)
            |
     [Phase 2: Synthesis]        SpecAgent extracts params, LLM builds step-by-step recipe
            |
     [Phase 3: Geometry]         Template -> Zoo.dev -> Claude -> Gemini -> Gemma 4 -> Deterministic
            |                    Validation loop: up to 10 refinement iterations
            |
     [Phase 4: Manufacturing]    7 parallel outputs: FEA, Drawing, DFM, Fusion, Quote, Onshape, Visual
            |
     [Phase 5: Finalize]         Memory record, MillForge bridge, summary report
            |
     STEP + STL + SVG drawing + CAM script + setup sheet + Onshape URL
```

---

## One-Liner

ARIA-OS turns English into STEP files, verified by AI vision and physics simulation, with zero manual CAD interaction.

---

[<-- Back to Table of Contents](./README.md) | [Next: The Why -->](./01-the-why.md)
