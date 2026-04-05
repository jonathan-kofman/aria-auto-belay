[<-- Back to Table of Contents](./README.md) | [<-- Previous: Integrations](./06-integrations.md) | [Next: Operations -->](./08-operations.md)

---

# Gotchas

## CadQuery Failure Patterns

These are the most common CadQuery errors encountered during LLM code generation. All are documented in `context/aria_failures.md` and injected into LLM prompts to prevent recurrence.

| Error | Cause | Fix |
|---|---|---|
| `ChFi3d_Builder: only 2 faces` | Fillet on thin body | Remove fillet; add only after solid validates cleanly |
| `BRep_API: command not done` | Invalid face references in compound boolean | Simplify to extrude + cut only |
| `Nothing to loft` | Non-coplanar loft profiles | Use revolve for axisymmetric profiles instead |
| `StdFail_NotDone` | Boolean operation on degenerate geometry | Ensure minimum wall thickness > 1mm |
| Bbox axis mismatch | CadQuery extrudes along Z, expected height on wrong axis | Verify extrude direction matches plan |
| `.cylinder()` called | Does not exist in CadQuery API | Use `.circle(r).extrude(h)` |
| Missing `result` variable | LLM generates code but never assigns to `result` | Post-processor scans for last CadQuery variable and aliases it |

> **Warning:** Never add fillets or chamfers on the first generation attempt. Always validate the solid shape first, then add edge treatments in a second pass.

---

## LLM Hallucination Patterns

### Code Hallucinations

| Pattern | Frequency | Mitigation |
|---|---|---|
| `.cylinder(r, h)` | Very common (Gemini, Gemma) | Operations reference explicitly bans this; post-processor catches it |
| `.fillet()` on first op | Common | `_NEEDS_LLM_FEATURES` list in DesignerAgent detects fillet in goal and routes to LLM with caution notes |
| Invented method names | Occasional (local models) | `_LOCAL_MODEL_NOTE` injected into system prompt warns against this |
| Define function but never call it | Common (Gemini/Gemma) | Post-processor detects missing `result` and patches the code |
| JSON wrapped in markdown fences | Common | `_extract_code()` has 5-tier parsing: JSON structured, JSON embedded, markdown fence, raw code, import scan |

### Geometry Hallucinations

| Pattern | Mitigation |
|---|---|
| Dimensions wildly wrong (10x expected) | Spec extraction provides authoritative dimensions; validator checks bbox against spec |
| Features described but not modeled | Visual verification catches missing features (bore, holes, slots) |
| Solid looks correct but is not watertight | `check_and_repair_stl()` runs trimesh repair (fill holes, fix normals, fix winding) |
| Tooth geometry self-intersecting | Ratchet ring template repairs tooth brep before/after transform, retries with tol=0.01 |

---

## Template Matching Edge Cases

### False Positive Matches

| Input | Matched Template | Problem | Solution |
|---|---|---|---|
| "motor housing with cooling fins" | `_cq_housing` | Ignores "cooling fins" | `_NEEDS_LLM_FEATURES` list includes "fin" --- routes to LLM |
| "custom bracket with sweep path" | `_cq_bracket` | Template cannot do sweeps | Feature keyword detection skips template when goal contains "sweep" |
| "hollow sphere" | `_cq_housing` (via "hollow") | Housing is a box, not a sphere | Fuzzy match returns as reference only, not executed |

### False Negative Matches

| Input | Expected Template | Problem | Solution |
|---|---|---|---|
| "NEMA 17 stepper motor mount" | `_cq_flange` | "NEMA 17" not in keyword list | Added `nema_mount`, `stepper_mount` to keyword entries |
| "6061 aluminum plate" | `_cq_flat_plate` | "plate" alone is ambiguous | Added `flat_plate`, `plate`, `base_plate`, `mounting_plate` aliases |

> **Tip:** When adding new part types, add entries to both `_CQ_TEMPLATE_MAP` (exact lookup) and `_KEYWORD_TO_TEMPLATE` (keyword scan). Test with `_find_template_fuzzy()` to verify matching.

---

## Bbox Validation False Positives

The bbox validator compares generated geometry dimensions against the spec. False positives occur when:

| Scenario | Why It Fails | Workaround |
|---|---|---|
| Part has protruding features | Bbox is larger than the base dimensions | Tolerance band (default +/-10%) accounts for this |
| Circular part (OD defines bbox) | Bbox diagonal != OD | Validator uses `max(xlen, ylen)` for circular parts |
| Part extrudes along X instead of Z | Height and width swap in bbox | CadQuery convention: extrude along Z; validator checks both orientations |

---

## Visual Verification Limitations

### When It Works Well

- Checking presence/absence of features (holes, bore, teeth, slots)
- Detecting obviously wrong shapes (cube when ring was requested)
- Confirming feature count (4 holes, 24 teeth)

### When It Struggles

- Dimensional accuracy (cannot measure mm from a rendered image)
- Internal features (hidden by outer geometry in all 3 views)
- Subtle defects (thin wall too thin, fillet radius wrong)
- High face count meshes (rendering caps at 6000 faces for 2D, 3000 for 3D)

### Common False Results

| False Positive | Cause | Impact |
|---|---|---|
| "bore visible" when there is no bore | Shadow or rendering artifact looks like a hole | Low --- dimensional validator catches missing bore |
| "PASS" on clearly wrong geometry | Vision model confidence threshold too low | Set `confidence` threshold at 0.7 to reject low-confidence passes |

| False Negative | Cause | Impact |
|---|---|---|
| "teeth not visible" on valid ratchet ring | 3D rendering angle hides teeth profile | Low --- bbox validator already confirms OD/tooth geometry |
| "bore not detected" in top view | Bore is on the bottom face, occluded | Use isometric view as backup; spec validator has bore detection |

---

## Onshape Integration Edge Cases

| Issue | Cause | Workaround |
|---|---|---|
| Translation fails on complex STEP | Onshape importer rejects certain OpenCascade constructions | Simplify geometry (fewer booleans, no compound solids) |
| Drawing element blank | Part Studio translation not complete when drawing is created | Bridge waits for translation completion before creating drawing |
| Rate limiting | Too many API calls in burst | 90-second timeout in Phase 4; bridge has built-in retry |

---

## Performance Gotchas

| Scenario | Impact | Mitigation |
|---|---|---|
| Gemma 4 31B on CPU | ~5 minutes per generation | Use Lightning AI GPU or skip to Gemini |
| Large STL mesh render | Matplotlib render slow for >50k faces | Face cap at 6000 (2D) / 3000 (3D) for rendering |
| 4 parallel research queries | 10-20s latency from web search | Skip research when >=4 dimensions already specified |
| Ollama cold start | First inference ~30s as model loads into VRAM | Keep Ollama running; `ollama serve` as a daemon |

---

## Common Developer Mistakes

1. **Calling `CADRouter()` as an instance.** `CADRouter.route(goal)` is a class method. Never instantiate.

2. **Using `cam_result` as a string.** `cam_generator` returns a `Path` object. Callers must not cast to `str` before using `.parent`.

3. **Adding templates without keyword entries.** A template in `_CQ_TEMPLATE_MAP` with no `_KEYWORD_TO_TEMPLATE` entry will only match on exact `part_id` --- fuzzy matching will miss it.

4. **Hardcoding geometry constants.** All dimensions come from `context/aria_mechanical.md`. Templates read from the spec dict, not hardcoded values.

5. **Adding LLM calls to `cem_to_geometry.py`.** The CEM geometry path must be deterministic (no LLM). This is a hard architectural rule.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: Integrations](./06-integrations.md) | [Next: Operations -->](./08-operations.md)
