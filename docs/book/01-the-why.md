# The Why

## The Problem

Mechanical CAD is the bottleneck of hardware development. A skilled engineer spends 2-8 hours modeling a single part in SolidWorks or Fusion 360. A junior engineer takes longer and makes more mistakes. The process is manual, error-prone, and expensive:

- **Time**: A bracket with 4 bolt holes takes 30 minutes in Fusion. A ratchet ring with 24 asymmetric teeth takes hours. An assembly of 12 parts takes days.
- **Expertise**: CAD software has a 6-month learning curve. Most startups cannot afford a full-time mechanical engineer in the first year.
- **Iteration cost**: Every design change means re-modeling, re-validating, re-exporting. The feedback loop between "I want this shape" and "this file is machinable" is measured in days.
- **Error propagation**: Dimensional mistakes in CAD propagate silently through manufacturing. A misplaced bore or wrong wall thickness becomes a $2,000 scrap part.

## The Insight

LLMs can generate parametric geometry code (CadQuery, Fusion API, Grasshopper), but raw LLM output is unreliable. Models hallucinate non-existent API calls (CadQuery has no `.cylinder()` method), produce geometry that fails boolean operations, and ignore manufacturing constraints. The solution is not better prompts -- it is engineering guardrails:

1. **Templates over generation**: For known part families (gears, brackets, flanges, housings), a parametric template with spec-extracted dimensions is faster and more reliable than LLM generation. ARIA-OS maintains 39 templates with 172+ keyword aliases. The LLM is only invoked when no template matches.

2. **Structured spec extraction**: Before any geometry is generated, `spec_extractor.py` parses the natural language description into a typed dict: `od_mm`, `bore_mm`, `n_teeth`, `material`, `part_type`. This eliminates ambiguity before it reaches the generator.

3. **Validation loops with failure injection**: When generation fails, the system retries up to 3 times, injecting the previous failure messages into the LLM prompt. Each retry is smarter than the last. The system tracks the best attempt (fewest failures) and returns that if all retries fail.

4. **Visual verification**: After geometry is generated, three orthographic views (top, front, isometric) are rendered via matplotlib and sent to a vision LLM (Gemini Flash or Claude) with a feature checklist. The vision model confirms that the bore is visible, the teeth are present, the L-bracket has two plates at 90 degrees.

5. **Physics before export**: CEM (Computational Engineering Model) checks enforce minimum safety factors (SF >= 2.0) before any STEP file is exported. A ratchet ring with tooth shear SF < 8.0 will not pass.

## The Market

Every hardware company needs CAD. The market segments that benefit most from text-to-part generation:

- **Machine shops** (~15,000 in the US): customers send napkin sketches and verbal descriptions. Shops spend hours converting these into machinable files. ARIA-OS collapses that to seconds.
- **Hardware startups** (~5,000 funded annually in the US): early-stage teams prototype 10-50 parts before finding product-market fit. Each part iteration costs time and engineering salary.
- **Product designers**: industrial designers who can describe what they want but cannot operate parametric CAD software.
- **Climbing gyms** (~300 with lead walls in the US, zero with a certified lead auto-belay): the specific use case that spawned ARIA-OS. The ARIA auto-belay device itself is designed and manufactured through this pipeline.

## Why Now

Three capabilities converged in 2025-2026 that make this possible:

1. **CadQuery maturity**: CadQuery 2.7 (built on OpenCascade) provides a headless, scriptable, Python-native CAD kernel that runs on any server. No GUI required.
2. **LLM code generation**: Claude, Gemini, and DeepSeek can generate syntactically valid CadQuery scripts when given proper constraints and failure context.
3. **Vision verification**: Gemini 2.5 Flash and Claude can visually inspect rendered geometry and confirm feature presence, closing the loop that previously required a human engineer.
