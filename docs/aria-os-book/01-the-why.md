[<-- Back to Table of Contents](./README.md) | [<-- Previous: Elevator Pitch](./00-elevator-pitch.md) | [Next: The Vision -->](./02-the-vision.md)

---

# The Why

## The Problem

Mechanical CAD is slow. An experienced engineer spends 15-60 minutes modeling a bracket, flange, or housing that could be fully described in a single sentence. The bottleneck is not design thinking --- it is translating a known shape into mouse clicks inside SolidWorks, Fusion 360, or Onshape.

This matters because:

- **Hardware startups** burn engineering hours on CAD grunt work instead of design iteration
- **Job shops** manually model customer parts before they can quote them
- **Solo builders** stall on CAD skills when they already know what they want to build

The CAD-to-manufacture pipeline has additional manual steps: writing CAM programs, creating setup sheets, running FEA, producing engineering drawings. Each step is a separate tool, separate skill, separate bottleneck.

---

## What Exists Today

| Tool | What It Does | Limitation |
|---|---|---|
| **MecAgent** (Onshape) | AI-generated Onshape FeatureScript from text | Closed-source. Onshape-only. No validation loop. No manufacturing outputs. |
| **Zoo.dev** (KittyCAD) | Text-to-STEP via ML model | $10/month free tier (~50 parts). Black box geometry --- no template reliability. No dimensional verification. |
| **Backflip** | AI agent for SolidWorks | Requires SolidWorks license. Desktop-only. No headless pipeline. |
| **ChatCAD / CadQuery + GPT** | LLM writes CadQuery code | Raw LLM output fails ~40% of the time. No validation, no retry loop, no manufacturing outputs. |
| **Traditional CAD** (Fusion, SolidWorks) | Manual modeling | Fast for experts. Slow for everyone else. No programmatic pipeline. |

---

## The Gap

No existing tool provides the complete pipeline:

```
Text description
  --> Structured spec extraction
    --> Reliable geometry generation (template + LLM fallback)
      --> Multi-layer validation (dimensional, mesh, visual)
        --> Manufacturing outputs (CAM, DFM, drawing, setup sheet)
          --> Live parametric model in Onshape
```

**MecAgent** stops at the Onshape model. **Zoo.dev** stops at the STEP file. **Backflip** requires a desktop application. None of them combine template reliability with LLM flexibility, and none of them produce manufacturing-ready outputs.

The specific gaps ARIA-OS fills:

| Gap | ARIA-OS Solution |
|---|---|
| LLM geometry fails ~40% of the time | 49 templates handle common parts deterministically; LLM only used for novel geometry |
| No dimensional verification | SpecAgent extracts dimensions, validator checks bbox/bore/bolt patterns |
| No visual sanity check | Vision AI (Gemini/Claude) inspects 3 rendered views against feature checklist |
| No manufacturing outputs | Phase 4 runs FEA, DFM, CAM, drawing, quote, Onshape in parallel |
| No refinement loop | Up to 10 iterations: failure context injected back into the LLM prompt |
| Cloud API costs | 6-level fallback chain includes free local models (Gemma 4 via Ollama) |

---

## Why Now

Three things changed in 2025-2026 that make this possible:

1. **CadQuery matured.** CadQuery 2.7 provides a headless, scriptable CAD kernel (OpenCascade) that runs on any machine without a GUI. This is the enabling technology for template-based generation.

2. **Vision models got cheap.** Gemini 2.5 Flash can inspect 3 rendered views of a part and report feature-level pass/fail for fractions of a cent. This closes the validation gap that makes raw LLM generation unreliable.

3. **Local LLMs hit the threshold.** Gemma 4 31B (Apache 2.0, free) running on a Lightning AI T4 GPU (22 free hours/month) can generate working CadQuery geometry. The pipeline no longer requires paid API access to function.

---

## Why Not Just Use an LLM Directly?

Raw LLM code generation for CadQuery produces valid geometry about 60% of the time. The failure modes are predictable:

- `.cylinder()` calls (does not exist in CadQuery API)
- Fillet on thin bodies (`ChFi3d_Builder: only 2 faces`)
- Invalid face references in compound booleans
- Missing `result` variable assignment
- Incorrect extrude direction causing bbox axis mismatch

ARIA-OS solves this with a layered approach: templates for known shapes, reference template injection for LLM-generated code, a 25-operation reference library, and a refinement loop that injects failure context back into the prompt. The template path has a 100% success rate. The LLM path with refinement reaches 80-100% depending on the backend.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: Elevator Pitch](./00-elevator-pitch.md) | [Next: The Vision -->](./02-the-vision.md)
