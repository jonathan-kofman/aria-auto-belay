# ARIA-OS Arbitrary Part Generation — 2026-03-09

## Summary

The system was upgraded so that **any** mechanical part description (not in the known template set) is routed to an LLM (Anthropic Claude) to generate CadQuery code. Known parts (housing, spool, cam collar, rope guide, motor mount) still use validated templates. Retry loop includes previous code and validation error in the prompt so the LLM can fix issues.

---

## What Was Built

### Phase 1 — aria_os/llm_generator.py

- **_get_api_key()**: Reads `ANTHROPIC_API_KEY` from `os.environ` or from `.env` in repo root (simple key=value parse). Raises clear error if missing.
- **_build_system_prompt(context)**: CadQuery expert instructions; mechanical constants from aria_mechanical as comments; aria_failures patterns as "avoid these"; build order (base → shell → additive → subtractive); required ending:
  - `bb = result.val().BoundingBox()`
  - `print(f"BBOX:{bb.xlen:.3f},...")`
  - `exporters.export(result, STEP_PATH, exporters.ExportTypes.STEP)`
  - `exporters.export(result, STL_PATH, exporters.ExportTypes.STL)`
- Common patterns: Box, Cylinder, Hole, Blind hole, Slot, Fillet, Bolt circle (polarArray or manual).
- **_build_user_prompt(plan, previous_code, previous_error)**: Plan text + build order; optional "Previous attempt failed with: ..." and previous code snippet for retries.
- **generate()**: Calls Anthropic API (model claude-sonnet-4-20250514 or fallback claude-3-5-sonnet), max_tokens=2000, temperature=0; extracts code from ```python block or full response.
- **save_generated_code(code, part_name, repo_root)**: Writes to `outputs/cad/generated_code/YYYY-MM-DD_HH-MM_partname.py`.

### Phase 2 — generator.py dispatch

- **FORCE_LLM = False** at top. When True, every part goes through LLM (for testing).
- **KNOWN_PART_IDS** = aria_housing, aria_spool, aria_cam_collar, aria_rope_guide, aria_motor_mount.
- If **part_id not in KNOWN_PART_IDS** (or FORCE_LLM): call **llm_generator.generate()** with plan, context, repo_root, previous_code, previous_error. On exception, raise RuntimeError with clear message. Save returned code via save_generated_code(goal/part_name).
- Otherwise: existing template path unchanged; BBOX print appended if missing.

### Phase 3 — API key and .env

- Key from **os.environ["ANTHROPIC_API_KEY"]** or **.env** in repo root (line by line, KEY=value).
- **.env.example** created: `ANTHROPIC_API_KEY=your_key_here`.
- **.gitignore** already contained `.env` — no change.

### Phase 4 — Test 3 arbitrary parts

- **Test 1**: "generate a rectangular spacer: 50mm x 30mm x 8mm, center hole 10mm diameter through all"
- **Test 2**: "generate the ARIA pawl lever: 60mm long, 12mm wide, 6mm thick aluminum plate, pivot hole 6mm diameter centered 8mm from one end, nose end has a 6mm radius rounded tip, fillet all edges 0.5mm"
- **Test 3**: "generate a motor adapter flange: cylindrical, 80mm outer diameter, 20mm tall, 6mm wall thickness, 4 bolt holes on 65mm bolt circle diameter, each 5.5mm diameter, center bore 42mm diameter"

**Result**: All three require **ANTHROPIC_API_KEY**. In this session the key was not set, so:
- Run 1 of Test 1 was attempted; orchestrator correctly routed to LLM, then failed with: "Set ANTHROPIC_API_KEY in environment or in a .env file in the repo root."
- Retry loop ran 3 times with the same error (no code to retry with).
- **Did all 3 test parts generate valid geometry?** Not run (API key not set). To run: set ANTHROPIC_API_KEY, then execute the three `run_aria_os.py "..."` commands above.

### Phase 5 — Retry loop with error feedback

- **Orchestrator** keeps **last_code** and **last_error** when validation fails.
- On next attempt, **generator_generate(..., previous_code=last_code, previous_error=last_error)**.
- **llm_generator._build_user_prompt** appends: "Previous attempt failed with: [error]. Previous code was: [snippet]. Fix the specific issue and regenerate."
- So the LLM sees the failure and the code it produced and can correct it.

### Phase 6 — Save generated code

- **llm_generator.save_generated_code(code, part_name, repo_root)** writes to `outputs/cad/generated_code/YYYY-MM-DD_HH-MM_partname.py`.
- Called from **generator.generate()** after every successful LLM return (before returning code). Part name is from goal or part_id (slugged).

### Other changes

- **validator.validate()**: New arg **inject_namespace** (e.g. STEP_PATH, STL_PATH) merged into exec() namespace so LLM-generated code can export to the chosen paths.
- **exporter.get_output_paths(goal_or_part_id, repo_root)**: Returns step_path and stl_path without writing files. Used by orchestrator for LLM path to set inject_namespace.
- **exporter._goal_to_part_name**: For unknown goals, returns slug like `llm_rectangular_spacer` from goal text.
- **orchestrator**: For **use_llm** (part_id not in KNOWN_PART_IDS): get paths via get_output_paths, inject STEP_PATH/STL_PATH into validate(), do not call export() (LLM code writes files). For template path: unchanged (export after validate).
- **Planner _plan_generic**: Uses **goal** as plan text so the LLM sees the full user description.

---

## Did all 3 test parts generate valid geometry?

**Not run** in this session (ANTHROPIC_API_KEY not set). With the key set:
- Test 1 (spacer) is simple and likely to work on first try.
- Test 2 (pawl lever) and Test 3 (flange) may need retries (fillet/rounded tip and cylindrical hollow + bolt circle are more involved).

---

## What the LLM would get right on first try (expected)

- Box + through hole (spacer): straightforward with .box() and .faces(">Z").workplane().hole().
- Correct use of STEP_PATH/STL_PATH and BBOX print when instructed in the system prompt.

---

## What would require retries and why

- **Pawl lever**: Rounded tip (6mm radius) and fillets (0.5mm) need correct face/edge selection; pivot at 8mm from end can be off on first try.
- **Motor adapter flange**: Cylinder with wall thickness (inner cut), center bore, and 4 holes on BCD — wrong order (e.g. hole before shell) or wrong coordinates can fail validation or produce wrong geometry.

---

## What failed completely and why

- **LLM generation** failed in this session only because **ANTHROPIC_API_KEY** was not set. No code was generated, so no validation or export was run.

---

## Honest assessment: is this now a general-purpose part generator?

- **Architecturally yes.** Any goal that does not match a known part_id is sent to the LLM with the full goal text, constants, and failure patterns. No new templates or part_ids are required for new part types.
- **Practically it depends on the LLM.** Quality of the first attempt and success after retries depend on Claude following the build order and CadQuery patterns. The system is general-purpose in the sense that no code changes are needed to "add" a new part; the same pipeline handles it.
- **Gaps**: (1) No expected_bbox for generic plans (validator can’t check dimensions for arbitrary parts unless we add heuristics or a second LLM call to infer expected bbox). (2) Complex features (helical ramps, sweeps) may need multiple retries or prompt tuning. (3) API key and network are required for arbitrary parts.

---

## Next capability gap to close

1. **Infer expected_bbox for generic plans** (e.g. from goal text or a lightweight LLM call) so validation can reject clearly wrong size.
2. **Stronger system prompt examples** for cylindrical hollow parts and bolt circles to reduce retries.
3. **Optional local fallback**: If no API key, fall back to a small local model or to a non-LLM “best effort” from goal parsing (current _code_generic is minimal).
4. **Generated code regression**: Keep a small set of “golden” arbitrary descriptions and run them in CI when the API is available, to catch prompt/API drift.
