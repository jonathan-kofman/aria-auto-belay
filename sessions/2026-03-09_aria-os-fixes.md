# ARIA-OS Four Fixes — 2026-03-09

## Scope
1. **FIX 1** — Template routing override (planner: has_dimensional_overrides → LLM)
2. **FIX 2** — Blocker bar: chamfer + fillet ordering (llm_generator prompt)
3. **FIX 3** — Bearing retainer: holes before raised features (llm_generator prompt)
4. **FIX 4** — Route logging in CLI output

---

## Implementation Summary

### FIX 1 — Template Override Detector
- **planner.py**: Added `has_dimensional_overrides(goal, template_dims, part_id)` — extracts dimension keywords + numbers from goal, compares to `TEMPLATE_DIMS`; if any differs >5% or goal mentions `OVERRIDE_FEATURE_KEYWORDS` (flange, keyway, helical, ramp, set screw), returns True.
- **planner.py**: For spool and cam collar branches: if `has_dimensional_overrides()` → return `_plan_generic(goal, constants, route_reason="...")` so part_id becomes "aria_part" and generator uses LLM.
- **generator.py**: `use_llm = FORCE_LLM or is_generic or force_llm` where `force_llm = plan.get("route_reason")`.

### FIX 2 — Chamfer + Fillet Ordering
- **llm_generator.py** "avoid" section: chamfer BEFORE fillet; use `.faces(">X").chamfer(depth)` for end chamfers; `.edges("|Z").fillet(r)` for vertical edges only.
- **llm_generator.py** patterns: added Chamfer on end face example with box → faces chamfer → edges fillet.

### FIX 3 — Holes Before Raised Features
- **llm_generator.py** "avoid" section: add holes BEFORE raised features (bosses, shoulders, rings).
- **llm_generator.py** patterns: added "Holes on plate with raised boss" example — center bore + bolt holes first, shoulder union last.

### FIX 4 — Route Logging
- **orchestrator.py**: Before printing plan, print `[TEMPLATE] Using validated template: {part_id}` or `[LLM] {route_reason}` / `[LLM] Unknown part → LLM route`.

---

## Test Results

### FIX 1 — Template Override (Rope Spool, Cam Collar)
- **Rope spool:** `[LLM] Dimensional overrides detected (e.g. 120mm/160mm vs 600mm template) -> LLM route` — Passed. Output: aria_spool.step (45.7 KB). BBOX expected ~160×160×96 (flange dia 160mm, length 96mm).
- **Cam collar with helical ramp:** `[LLM] Dimensional/feature overrides (helical ramp, set screw) -> LLM route` — Passed. Output: aria_cam_collar.step (4.5 MB — helical geometry). Helical ramp and set screws attempted.

### FIX 2 — Blocker Bar
- **Blocker bar:** `[LLM] Unknown part -> LLM route` — Passed. Output: llm_aria_blocker_bar_tall_chamfer.step (96.1 KB). Chamfer-before-fillet prompt worked; no BRep_API error.

### FIX 3 — Bearing Retainer
- **Bearing retainer:** `[LLM] Unknown part -> LLM route` — Passed. Output: llm_aria_bearing_retainer_plate_circular.step (40.6 KB). Holes-before-shoulder prompt worked; no "Shape could not be reduced to a circle" error.

### FIX 4 — Route Logging
- All runs now print `[TEMPLATE] Using validated template: {part_id}` or `[LLM] {reason}` before the plan. No silent template overrides.

### --list Output (post-fix)
```
aria_cam_collar             4482.2 KB      298.1 KB   OK
aria_spool                    44.7 KB      195.6 KB   OK
llm_aria_bearing_retainer_plate_circular     40.6 KB     3248.9 KB   OK
llm_aria_blocker_bar_tall_chamfer     96.1 KB       79.2 KB   OK
...
```

---

## Honest Assessment

| Fix | Pass/Fail | Notes |
|-----|-----------|-------|
| FIX 1 | **Pass** | Spool and cam collar correctly route to LLM when goal has dimension/feature overrides. aria_spool and aria_cam_collar overwritten with new geometry (exporter uses goal keywords). |
| FIX 2 | **Pass** | Blocker bar generates and validates. Chamfer/fillet ordering in prompt resolved BRep_API error. |
| FIX 3 | **Pass** | Bearing retainer generates and validates. Holes-before-shoulder pattern resolved circle-reduction error. |
| FIX 4 | **Pass** | Route logging visible on every run. |

### Geometry Challenges That Remain
- **Helical ramp:** Cam collar STEP is 4.5 MB — LLM may have used a faceted/approximate helical; verify geometry in viewer.
- **Keyway:** Rope spool spec included keyway; BBOX/size suggest it was attempted; verify in CAD.
- **Exporter naming:** When goal contains "spool" or "cam collar", output overwrites aria_spool/aria_cam_collar. Consider distinct names for LLM-generated variants (e.g. llm_aria_spool_120mm) to avoid overwriting template outputs.
