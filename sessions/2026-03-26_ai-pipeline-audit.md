## Session 2026-03-26T00:00:00
**Status:** Complete (research + write)
**Goal:** Audit the ARIA-OS LLM-driven CAD generation pipeline and identify concrete improvements.

---

# ARIA-OS AI/ML Pipeline Audit

## Files Reviewed

- `aria_os/llm_client.py` (589 lines) -- multi-backend routing
- `aria_os/llm_generator.py` (358 lines) -- RhinoCommon code generation prompts
- `aria_os/cad_prompt_builder.py` (274 lines) -- engineering brief construction
- `aria_os/cad_learner.py` (170 lines) -- few-shot learning log
- `aria_os/cadquery_generator.py` (941 lines) -- 16+ templates + LLM fallback
- `aria_os/post_gen_validator.py` (804 lines) -- validation with failure injection
- `aria_os/orchestrator.py` (500 lines) -- pipeline controller

---

## 1. Prompt Quality

### Strengths
- The system prompts are well-structured with clear role assignment ("You are a CadQuery Python expert" / "You are a Grasshopper/RhinoCommon Python expert").
- Strong output format enforcement: exact variable names (`result`), exact BBOX print format, exact export footer structure.
- Mechanical constraints are injected from `context/aria_mechanical.md` via `context_loader.py` -- this is a solid single-source-of-truth pattern.
- CEM-derived geometry values are injected with a `*** MANDATORY ***` marker, explicitly telling the LLM not to recalculate.
- The "avoid these patterns" block in `llm_generator.py` (lines 61-79) is excellent -- it lists specific wrong/correct API patterns with concrete examples.

### Issues Found

**I-1: Dual system prompt paths with divergent quality.** `llm_generator.py` builds a ~180-line system prompt for the Grasshopper/RhinoCommon path. `cadquery_generator.py::_llm_cadquery()` builds a minimal ~15-line system prompt (lines 870-885). The CadQuery system prompt lacks:
- The "avoid these patterns" block (known CadQuery failure patterns from `context/aria_failures.md`).
- CEM context injection.
- Few-shot examples in the system prompt (they are injected into the user prompt instead, which is less effective for steering output format).
- Failure pattern injection from `cad_learner.py`.

**Recommendation:** Unify the CadQuery LLM system prompt to match the depth of the Grasshopper one. Inject `context/aria_failures.md` CadQuery-specific patterns, CEM context, and move few-shot examples into the system prompt.

**I-2: No structured output schema enforcement.** Both generators extract code via regex (````python...````) with a loose fallback (any text containing `import cadquery`). There is no JSON-mode or tool-use constraint. The LLM could return code with explanation text interleaved, and the regex would miss it.

**Recommendation:** Use a structured extraction marker. Add to the system prompt: "Wrap your entire response in a single ```python block. No text before or after the block." Consider using Anthropic's `tool_use` with a schema `{code: string}` for guaranteed extraction.

**I-3: max_tokens=2000 for Anthropic is tight.** Complex parts (ratchet ring with N teeth, housing with features) can easily require 150+ lines of CadQuery code. At ~4 tokens/line, that is 600 tokens for code alone, plus the LLM's reasoning overhead.

**Recommendation:** Raise to 4096 for code generation calls (vision calls at 512 are fine). The Gemini path already uses 4096.

---

## 2. Model Routing

### Strengths
- The Anthropic -> Gemini -> Ollama -> None fallback chain is robust and never raises.
- Each backend has independent try/except isolation.
- Gemini has rate-limit-aware fallback across model tiers (gemini-2.0-flash -> gemini-2.0-flash-lite -> gemini-2.5-flash).
- Ollama gets a `_LOCAL_MODEL_NOTE` injected to constrain its output.
- The `call_llm()` function has a clean contract: returns `str | None`, never raises.

### Issues Found

**I-4: `llm_generator.py` bypasses `call_llm()` entirely.** The Grasshopper generator calls `_call_anthropic()` directly (line 294), which:
- Only tries Anthropic. If ANTHROPIC_API_KEY is unset, it raises `RuntimeError` (line 37) instead of falling back to Gemini/Ollama.
- Duplicates API key resolution logic (lines 16-38 are a copy of `llm_client.get_anthropic_key`).
- Uses `claude-sonnet-4-6` hardcoded (line 249), not the dual-model fallback in `llm_client._try_anthropic`.

**Recommendation:** Refactor `llm_generator.py` to use `call_llm()` from `llm_client.py`. If the Grasshopper path needs Anthropic specifically (e.g., for quality reasons), add a `preferred_backend` parameter to `call_llm()` but still fall back gracefully.

**I-5: Gemini model fallback order is inverted.** In `_try_gemini()` (line 229), the fallback order is `gemini-2.0-flash -> gemini-2.0-flash-lite -> gemini-2.5-flash`. The `2.5-flash` model is more capable than `2.0-flash-lite` but is tried last. This means on quota exhaustion of the primary model, the pipeline downgrades to the weakest model before trying the stronger one.

**Recommendation:** Reorder to `gemini-2.0-flash -> gemini-2.5-flash -> gemini-2.0-flash-lite`.

**I-6: Ollama timeout of 300 seconds.** The `_try_ollama()` function uses a 300-second timeout (line 303). For a local model generating ~100 lines of CadQuery code, this is reasonable, but there is no progress feedback. If Ollama hangs, the pipeline is blocked for 5 minutes silently.

**Recommendation:** Add a print statement before the Ollama call: `print("[LLM] calling ollama (may take up to 5 min)...")` and consider reducing to 120s for code generation.

---

## 3. Few-Shot Learning

### Current Implementation
`cad_learner.py` maintains a JSON log of up to 500 entries. Each entry records goal, plan_text, code (truncated to 4000 chars), bbox, validation booleans, and a composite quality_score (0-100).

Retrieval in `get_few_shot_examples()` uses a scoring function:
```python
score = (quality_score, pid_match, word_overlap, recency)
```

This is a **keyword-based** approach with lexicographic tuple sorting.

### Issues Found

**I-7: The scoring function has a ranking bug.** The tuple `(quality_score, pid_match, overlap, recency)` sorts primarily by `quality_score` (0-100 int), then by `pid_match` (0 or 1), then word overlap, then recency (ISO timestamp string). This means a low-quality example for the exact same part_id (quality=40, pid_match=1) will rank below a high-quality example for an unrelated part (quality=80, pid_match=0). For few-shot learning, part_id match should dominate.

**Recommendation:** Reweight the tuple to `(pid_match, quality_score, overlap, recency)` so exact part_id matches always rank first.

**I-8: Only successful examples are retrieved, but all attempts are stored.** `get_few_shot_examples()` iterates all entries sorted by score. Failed attempts (passed=False, quality_score=0) will always rank last and be excluded by the top-3 limit. This is correct but wastes storage. Separately, `get_failure_patterns()` only returns error messages, not the failing code -- so the LLM cannot learn *what code pattern* caused the failure.

**Recommendation:** In `get_failure_patterns()`, return `(error, code_snippet)` tuples. Inject a "DO NOT repeat this pattern:" block into the prompt with the failing code fragment (first 20 lines).

**I-9: Word overlap is trivially gameable.** `goal_words` uses `re.findall(r"\w+", ...)` which matches numbers, articles, and common words. A goal like "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick" produces words `{aria, ratchet, ring, 213mm, od, 24, teeth, 21mm, thick}`, and a past example about an unrelated "213mm flange with 24 bolts" would score high overlap on the numbers alone.

**Recommendation:** Filter out numeric-only tokens and stopwords from the overlap computation. Better yet, compute overlap on engineering-meaningful tokens only (part types, feature names, material names).

**I-10: Code truncation at 4000 chars loses export footers.** The `record_attempt()` function truncates code to 4000 chars (line 74). Since the export footer is appended at the end of the script, it is the most likely to be truncated. When this truncated code is used as a few-shot example, the LLM sees code that never exports -- potentially teaching it to omit the export.

**Recommendation:** Store code without the auto-generated export footer (strip everything after `# === AUTO-GENERATED EXPORT ===`). This reduces size and avoids the truncation problem.

---

## 4. Failure Injection

### Current Implementation
The pipeline has two failure injection paths:

**Path A (post_gen_validator.py):** `run_validation_loop()` accumulates failures across attempts. On retry, `_inject_failure_context()` deep-copies the plan and appends failure messages to `build_order` and `text`. The `_call_generate_fn()` also passes `previous_failures` as a kwarg if the generator's signature accepts it.

**Path B (orchestrator.py):** For CadQuery, the orchestrator has its own retry loop (lines 224-253) that collects `_cq_previous_failures` and passes them to `write_cadquery_artifacts()`.

### Issues Found

**I-11: Double retry loop, neither fully effective.** The orchestrator runs its own retry loop for CadQuery (lines 224-253), AND then runs `run_validation_loop()` below (lines 282-316) -- but with `max_attempts=1` (one-shot validation, no regeneration). The validation loop was designed for retry-with-regeneration but is used here only for checking. This means:
- CadQuery retries are based only on execution errors (exceptions), not on geometric validation failures.
- Geometric validation failures (wrong bbox, not watertight, no bore) are detected but never trigger regeneration.

**Recommendation:** Wire the CadQuery generator into `run_validation_loop()` as the `generate_fn` with `max_attempts=3` and `check_quality=True`. Remove the manual retry loop in the orchestrator. This unifies the retry/validation/regeneration cycle.

**I-12: Failure context injection is append-only and accumulates noise.** `_inject_failure_context()` appends to `build_order` and `text` on each retry. By attempt 3, the plan text contains failures from attempts 1 and 2 concatenated, plus the original plan text. This can confuse the LLM with contradictory instructions.

**Recommendation:** Replace the accumulated failure text with a structured, deduplicated block. On each retry, inject only the latest attempt's failures plus a count of how many previous attempts failed.

**I-13: The noop generate function defeats the validation loop.** In `orchestrator.py` line 289, `_noop_generate()` is used in the validation loop. It just checks if files exist -- it cannot regenerate. Combined with `max_attempts=1`, this makes the validation loop a pure checker, not a feedback loop.

**Recommendation:** See I-11. Use the actual generator function.

---

## 5. Token Budget

### Estimates

**Grasshopper path (llm_generator.py):**
- System prompt: ~3,500 tokens (constants block + CEM block + avoid patterns + required code structure + common patterns)
- Few-shot examples: up to 3 x 30 lines x 4 tokens/line = ~360 tokens
- Learned failures: up to 5 x 50 tokens = ~250 tokens
- Engineering brief (user prompt): ~1,000-2,000 tokens
- Previous code (on retry): up to 4000 chars = ~1,000 tokens
- **Total input: ~6,000-7,000 tokens** -- well within all models' context windows.

**CadQuery path (cadquery_generator.py::_llm_cadquery):**
- System prompt: ~200 tokens (minimal)
- User prompt: ~300-600 tokens
- Few-shot block: ~360 tokens
- Failure block: ~200 tokens
- **Total input: ~1,000-1,400 tokens** -- extremely lean, no risk of overflow.

### Issues Found

**I-14: CEM block can grow unboundedly.** `format_cem_block()` serializes the full CEM geometry dict. For complex parts with many CEM parameters, this could be 500+ tokens. Combined with the engineering brief's dimension hints and the constants block, the Grasshopper system prompt could approach 5,000 tokens.

**Recommendation:** Cap the CEM block to the top 20 most relevant parameters. Add a `max_params` argument to `format_cem_block()`.

**I-15: Constants block includes ALL constants from aria_mechanical.md.** If this file grows, every LLM call pays the token cost. Currently manageable, but the pattern does not scale.

**Recommendation:** Filter constants to only those relevant to the current part_id. A simple approach: maintain a `PART_ID_RELEVANT_CONSTANTS` mapping.

---

## 6. Vision Pipeline

### Current Implementation
`analyze_image_for_cad()` in `llm_client.py` loads an image, sends it to Anthropic or Gemini with a well-crafted system prompt (`_IMAGE_ANALYSIS_SYSTEM`), and returns a goal string. The goal string then enters the normal pipeline.

`check_visual()` in `post_gen_validator.py` renders the generated STL to a 3-view PNG (isometric + top + front), sends it to Claude with the spec, and asks YES/NO.

### Strengths
- The vision system prompt is focused and well-constrained: "Output ONLY the goal string -- no preamble, no explanation, no JSON."
- Dimension estimation guidance is practical: "use context clues: standard bolt sizes, hand scale, grid markings."
- The 3-view render approach (isometric + top + front) gives the vision model enough geometric context.

### Issues Found

**I-16: Vision validation (`check_visual`) only runs when `skip_visual=False` and is skipped by default in the orchestrator.** Looking at orchestrator.py line 306: `skip_visual=True`. This means the visual validation check -- arguably the most powerful quality gate -- never runs in the standard pipeline.

**Recommendation:** Enable visual validation by default when ANTHROPIC_API_KEY is set. Add a cost-awareness flag: `skip_visual=not bool(get_anthropic_key())`. The vision call costs ~0.01 USD per check, which is negligible compared to the generation call.

**I-17: Ambiguous YES/NO parsing in `check_visual()`.** Lines 543-551: if the first line contains neither "YES" nor "NO", the check defaults to `passed=True`. This silent pass-through means any LLM response parsing failure is treated as validation success.

**Recommendation:** Default to `passed=False` when the answer is ambiguous. Add the instruction "You MUST start your response with exactly YES or NO on its own line" to the prompt.

**I-18: No Ollama vision fallback.** The image analysis path only tries Anthropic and Gemini. Ollama with multimodal models (e.g., llava) is not attempted. This is reasonable given local model vision quality, but should be documented.

**I-19: Image-to-CAD prompt loses spatial precision.** The vision prompt asks the model to "estimate visible dimensions in mm." For most photos without a ruler or known-size reference, dimension estimates will be wildly inaccurate. The pipeline then treats these estimates as ground truth.

**Recommendation:** Add a confidence qualifier to the vision prompt output: "prefix uncertain dimensions with ~ (e.g., ~120mm)." Then in `spec_extractor.py`, parse the tilde as a signal to widen tolerances for those dimensions.

---

## Summary of Recommendations (Priority Order)

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| **P0** | I-11: Wire CadQuery into validation loop properly | Geometric failures never trigger regeneration | Medium |
| **P0** | I-4: llm_generator.py bypasses call_llm() | Grasshopper path crashes without Anthropic key | Low |
| **P1** | I-1: CadQuery LLM prompt lacks depth | Lower quality LLM-generated CadQuery code | Medium |
| **P1** | I-16: Visual validation disabled by default | Strongest quality gate is unused | Low |
| **P1** | I-7: Few-shot scoring ranks quality over part_id match | Wrong examples selected | Low |
| **P2** | I-3: max_tokens=2000 too low for complex parts | Truncated code generation | Trivial |
| **P2** | I-5: Gemini fallback order suboptimal | Worse model selected on quota exhaustion | Trivial |
| **P2** | I-12: Failure context accumulates noise | LLM confused on retry 3 | Low |
| **P2** | I-17: Ambiguous vision check defaults to pass | False positive validations | Trivial |
| **P3** | I-10: Code truncation loses export footers | Bad few-shot examples | Low |
| **P3** | I-9: Word overlap matches on numbers | Irrelevant few-shot examples selected | Low |
| **P3** | I-8: Failure patterns lack code context | LLM cannot learn from specific code mistakes | Low |
| **P3** | I-14: CEM block unbounded growth | Token waste on complex parts | Low |
| **P3** | I-15: Constants block not filtered by part | Minor token waste | Low |
| **P3** | I-19: Vision dimension estimates treated as exact | Overly tight validation on photo-sourced parts | Medium |
| **P3** | I-6: Ollama 300s timeout with no feedback | User experience issue | Trivial |
| **P3** | I-18: No Ollama vision fallback | Documentation gap | Trivial |

---

## Architectural Observation

The pipeline has two parallel LLM code generation paths that have diverged significantly:

1. **Grasshopper path** (`llm_generator.py`): Rich system prompt, CEM injection, few-shot from learner, direct Anthropic call, generates RhinoCommon Python.
2. **CadQuery path** (`cadquery_generator.py::_llm_cadquery`): Minimal system prompt, separate few-shot injection, uses `call_llm()`, generates CadQuery Python.

These should be unified into a single `generate_cad_code(plan, goal, backend="cadquery"|"grasshopper", ...)` function that:
- Uses `call_llm()` for all backends.
- Injects backend-specific API patterns into a shared prompt template.
- Centralizes few-shot, CEM, and failure context injection.
- Returns structured output (code + metadata) rather than raw text.

This refactor would eliminate issues I-1, I-4, and reduce the surface area for future divergence.
