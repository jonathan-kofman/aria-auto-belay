# ARIA-OS Upgrade Audit — 2026-03-09

## PHASE 1 — Brutally Honest Audit

### What's hardcoded vs actually reasoned

| Module | Hardcoded | Reasoned |
|--------|-----------|----------|
| **planner.py** | Exact keyword branches: `"housing"` + `"shell"`/`"box"`/`"aria housing"` → housing plan; `"spool"` → spool plan. Fallback is a one-line generic string. No parsing of the goal. | Constants (w, h, d, bore, etc.) are read from `get_mechanical_constants()` — that part is data-driven. |
| **generator.py** | Entire code paths are template choice: `"housing shell"`/`"aria housing"` → `_code_housing_shell()`, `"spool"` → `_code_spool()`, else `_code_generic_box()` (100×100×100 box). Plan text is only used for the if/else; no extraction of dimensions or features from the plan. | Numbers inside the chosen template come from `get_mechanical_constants()`; the *structure* of the code is fixed per template. |
| **validator.py** | Only checks: (1) exec(code) runs, (2) `result` exists, (3) bbox is read from the solid. No parsing of printed output, no file checks. | None. |
| **orchestrator.py** | Housing/shell validation is gated by `"housing" in goal.lower() or "shell" in goal.lower()`. Export filename is hardcoded in exporter by goal keywords (housing vs spool). | Retry loop and context loading are generic. |
| **exporter.py** | Output name is `aria_housing` or `aria_spool` from goal keywords; no other part names supported. | Path layout (outputs/cad/step, stl) is generic. |
| **context_loader.py** | Table parsing is regex on `aria_mechanical`; key aliases (width→housing_width, etc.) are a fixed dict. Non-table constants (e.g. from prose) are not extracted. | Which file to read is generic; constant *values* are from the file. |

**Verdict:** The system is **template-based**. "Reasoning" is limited to: pick one of two part templates from keywords, then fill numbers from context. There is no interpretation of arbitrary part descriptions.

---

### What breaks if I ask for a part that isn't housing or spool

1. **Planner:** Returns the generic fallback: `"Generic plan for: <goal>\n1. Create main solid...\n2. Apply cuts..."` — no dimensions, no build order, no features.
2. **Generator:** Hits `_code_generic_box()` and outputs a **100×100×100 mm solid box**. No hollow, no bores, no slots, no reference to the goal or plan.
3. **Validator:** Will pass (code runs, result exists, bbox is (100,100,100)). No check that the part matches the request.
4. **Exporter:** Uses default name `aria_housing` (first branch is `"spool"`; everything else falls through to `name = "aria_housing"`). So "cam collar" → file overwrites `aria_housing.step`.
5. **Orchestrator:** No part-specific validation for unknown parts; export and log still run with wrong geometry and wrong filename.

So: **wrong geometry (generic box), wrong filename, validation gives false positive.**

---

### What the validator actually checks vs what it should check

| Current | Should |
|---------|--------|
| exec(code) doesn't raise | Same |
| `result` is defined | Same |
| bbox from `result.val().BoundingBox()` | Also parse BBOX line from stdout for comparison |
| Nothing about file | STEP/STL written, size reasonable (e.g. STEP > 50 KB for complex parts) |
| No file validity | Re-import STEP with CadQuery and confirm ≥1 solid |
| No expected dimensions | Compare bbox to expected from aria_mechanical (or plan) with tolerance |
| Single `passed` flag | Structured: bbox_match, file_valid, solid_count, errors[] |

---

### Summary

- **Hardcoded:** Part selection (housing vs spool vs box), code structure per part, export name, validation gate.
- **Data-driven only:** Numeric constants from aria_mechanical.md.
- **Missing:** Structured plan (base shape, hollow, features, build order), generic code generation from plan, BBOX in generated code for validation, file checks, STEP re-import check, and support for any part name/description.

---

## Post-Upgrade Summary (Phases 2–6)

### What changed in each module

| Module | Changes |
|--------|--------|
| **planner.py** | Returns a **structured plan dict** (text, part_id, base_shape, hollow, wall_mm, features[], build_order[], expected_bbox, material, export_formats). Keyword branches extended to: housing, spool, **cam collar**, **rope guide**, **motor mount**. Generic fallback returns same structure with inferred base_shape. ARIA parts pull dimensions from aria_mechanical via get_mechanical_constants(). |
| **generator.py** | **System prompt** builder added: mechanical constants + aria_failures patterns + CadQuery best practices + plan text/build order. **Structured code generation**: accepts plan dict (or legacy plan string); dispatches by part_id to _code_housing, _code_spool, _code_cam_collar, _code_rope_guide, _code_motor_mount, or _code_generic(base, hollow, features). All generated code ends with **BBOX print** for validator. Legacy string plan still supported via _plan_text_to_struct(). |
| **validator.py** | **Stdout capture** during exec(); **parse BBOX** line (regex). **expected_bbox** from plan with ±0.5 mm tolerance → **bbox_match**. Optional **step_path**: **file size** (min 50 KB for complex, 10 KB in orchestrator), **re-import STEP** via cq.importers.importStep, **solid_count** ≥ 1. **ValidationResult** extended: bbox_match, file_valid, solid_count, errors[]. **validate_step_file(step_path, min_size_kb)** added for post-export check. |
| **orchestrator.py** | Uses **plan dict**: prints plan["text"], passes plan to generator, **expected_bbox** from plan to validate(). Export uses **part_id** from plan. **Post-export** calls validate_step_file(); fails only if solid_count < 1. |
| **exporter.py** | **part_id** support: export(geometry, goal_or_part_id); _goal_to_part_name() extended for cam_collar, rope_guide, motor_mount. |
| **run_aria_os.py** | **--list**: list all .step in outputs/cad/step with STEP/STL sizes and validation status. **--validate**: re-validate all STEP files (size + re-import), exit 1 if any fail. |

### Which of the 3 new parts succeeded/failed validation

| Part | Validation | STEP size | STL size | Solids on re-import |
|------|------------|-----------|----------|----------------------|
| **ARIA Cam Collar** | Passed | 10.4 KB | 49.3 KB | 1 |
| **ARIA Rope Guide** | Passed | 41.2 KB | 50.9 KB | 2 |
| **ARIA Motor Mount Plate** | Passed | 43.1 KB | 128.2 KB | 1 |

All three new parts **succeeded**. Rope guide reports 2 solids (likely compound from slot cut); still valid.

### Actual bbox results vs expected

- **Housing:** Expected 700×680×344 mm. Generated code prints BBOX; validator compares with ±0.5 mm — passed.
- **Cam collar:** Expected (55, 55, 40) — cylinder OD 55 mm, length 40 mm. Passed.
- **Rope guide:** Expected (80, 40, 10). Passed.
- **Motor mount:** Expected (120, 120, 8). Passed.

(Exact printed BBOX values are in run stdout; not persisted per part in session. Validator uses expected_bbox from plan for pass/fail.)

### Honest assessment: reasoning vs templating

- **Still templating per part_id.** The planner has one branch per known part (housing, spool, cam collar, rope guide, motor mount); the generator has one code path per part_id. There is no single “interpret any description” path that builds CadQuery from a free-form plan.
- **Structured plan is a step toward reasoning.** The plan is now a dict with base_shape, features, build_order, expected_bbox. A future LLM or richer parser could fill that structure from an arbitrary goal; the generator’s _code_generic() can emit code from base_shape + features but is minimal (box/cylinder, optional hollow, no feature parsing).
- **System prompt is ready for LLM.** build_system_prompt(plan, context) produces a full spec (constants, failures, best practices, plan). If generator called an API (e.g. Claude) with that prompt and parsed code from the response, that would be true reasoning; currently it is not wired.
- **CadQuery best practices and failure patterns** are encoded in the prompt and in the hand-written code paths (solid first, cut on existing faces, BBOX print).

### What needs to happen for truly arbitrary part descriptions

1. **Planner:** Parse arbitrary goal into structured plan (base_shape, hollow, features[], build_order) without keyword branches — e.g. LLM or robust NER for dimensions and feature types from natural language.
2. **Generator:** Either (a) call LLM with build_system_prompt() and execute returned code, or (b) implement a **generic feature interpreter** that turns features[] (bore, slot, pocket, bolt_circle, etc.) into CadQuery calls from base_shape, so any plan dict produces code without a new template per part.
3. **Validator:** Already supports expected_bbox and STEP re-import; optional: semantic checks (e.g. “has a through bore”, “has 4 holes”) from plan.
4. **Constants:** Keep aria_mechanical as source of truth; planner/generator resolve named constants (e.g. “bearing shoulder OD”) from context for any part that references them.
