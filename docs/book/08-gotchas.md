# Gotchas

## Known Failure Patterns and How They Are Handled

This chapter documents the real failure modes we have encountered and fixed. These patterns are also maintained in `context/aria_failures.md`, which is injected into every LLM prompt so the model avoids known traps.

### CadQuery API Hallucinations

**Problem:** LLMs (especially smaller models) generate CadQuery code that calls methods that do not exist.

| Hallucinated Call | Reality | Fix |
|-------------------|---------|-----|
| `cq.Workplane().cylinder(r, h)` | CadQuery has no `.cylinder()` method | Use `.circle(r).extrude(h)` |
| `cq.Workplane().box(x, y, z)` | `.box()` exists but behaves unexpectedly with centering | Use `.rect(x, y).extrude(z)` for predictable results |
| `.fillet(r)` on thin bodies | `ChFi3d_Builder: only 2 faces` | Never fillet on first attempt. Add fillets only after the solid validates. |
| `.loft()` with non-coplanar profiles | `Nothing to loft` | Use `.revolve()` for axisymmetric profiles instead |

**Mitigation:** The template system avoids LLM generation entirely for known parts. When LLM is required, `context/aria_failures.md` is injected into the system prompt with explicit "DO NOT use .cylinder()" instructions.

### Fillet Failures on Thin Bodies

**Error:** `ChFi3d_Builder: only 2 faces`

This is the most common CadQuery failure. It occurs when a fillet radius approaches or exceeds the thickness of an edge. OpenCascade cannot compute the blend.

**Rule:** No fillets or chamfers on the first generation attempt. The validation loop confirms the solid is valid, then fillets can be added in a second pass if needed. This rule is enforced in `context/aria_failures.md` and documented as CAD Rule #4 in CLAUDE.md.

### Bounding Box Axis Mismatch

**Problem:** CadQuery extrudes along Z by default. If the planner expects height along Y (e.g., "100mm tall bracket"), the bbox check fails because the part is 100mm in Z, not Y.

**Fix:** The orchestrator syncs user-specified dimensional keys (`od_mm`, `bore_mm`, `thickness_mm`, `height_mm`, etc.) back into `plan["base_shape"]` after spec extraction, ensuring validation checks against what the user asked for, not planner template defaults.

### Template vs LLM Routing

**Problem:** The planner must decide whether to use a template (fast, reliable) or invoke the LLM (slow, flexible). Early versions over-routed to LLM.

**Solution:** `planner.py` uses `has_dimensional_overrides(goal, template_dims, part_id)` to check if the user's requested dimensions deviate more than 25% from template defaults. Below 25%, the template is used with spec-injected params. Above 25% or when feature keywords are present (keyway, involute, spline, etc.), the LLM is invoked.

### Ollama 7B Cannot Generate CadQuery

**Problem:** Local 7B models (deepseek-coder 6.7B, codellama 7B) generate syntactically valid Python but semantically broken CadQuery. They hallucinate methods, miss boolean operations, and produce non-watertight geometry.

**Mitigation:** When Ollama is the active backend, `_LOCAL_MODEL_NOTE` is injected into the system prompt with extra constraints. In practice, Ollama is best used for spec extraction (parsing dimensions from text) rather than code generation. The template system handles the geometry.

### Thickness vs Bbox Dimension Confusion

**Problem:** For L-brackets, heat sinks, and other non-prismatic parts, "thickness" in the user's description may refer to plate thickness (e.g., 5mm), but the bounding box dimension is much larger (the overall part height might be 80mm). Validation fails because it expects the bbox to match "5mm thick".

**Fix:** `spec_extractor.py` distinguishes between `thickness_mm` (plate/wall thickness) and `height_mm` (overall bounding box height). The `_cq_l_bracket` and `_cq_heat_sink` templates correctly map these to separate parameters. `post_gen_validator.py` uses the `height_mm` value for bbox checks, not `thickness_mm`.

### Bore Detection False Positives/Negatives

**Problem:** The post-generation validator checks for a central bore by analyzing the mesh cross-section area ratio. Parts with large bores (bore_mm close to od_mm) triggered false negatives. Parts with thin walls triggered false positives.

**Fix:** `post_gen_validator._detect_bore()` now uses a spec-derived threshold: when `bore_mm` and `od_mm` are both known, the threshold is `1 - (bore_mm/od_mm)^2 * 0.5`. This adapts to the part's actual geometry rather than using a fixed 0.65 cutoff.

### Fusion 360 Script Failures (Historical)

These failures are documented in `context/aria_failures.md` (FAILURE 001-006) from the early Fusion 360 scripting phase. Key lessons:

1. **Always force Direct Design mode** -- Parametric mode causes timeline conflicts with programmatic operations.
2. **Build solid box FIRST** -- Never use annular/donut profiles for the initial extrusion. Build solid, then cut.
3. **Select faces by normal direction, not index** -- Face indices are not stable across topology changes.
4. **Delete existing components before re-running** -- Scripts create new components; they do not replace existing ones.

### CEM Safety Factor False Fails

**Problem (FAILURE 099):** All 13 catch mechanism parts showed SF < 2.0 at 16 kN proof load in the closed-form static model. The model assumed worst-case single-tooth loading, not distributed contact.

**Status:** Open. Requires hardware drop tests for calibration. Interim fix: `cem_checks._enrich_meta_with_cem()` pre-fills meta dimensions from CEM physics before static checks, replacing placeholder values with CEM-correct geometry.

### Grasshopper Retry on Template Missing

**Problem:** `write_grasshopper_artifacts` raises `RuntimeError` when no GH template exists and LLM is unavailable. This previously caused unhandled tracebacks.

**Fix:** The orchestrator wraps the Grasshopper call in a retry loop (up to `max_attempts`). `RuntimeError` is caught, logged, and retried. Script size < 500 bytes is a hard failure that triggers retry.
