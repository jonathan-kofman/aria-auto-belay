# CHANGELOG

## 2026-03-23 — Grasshopper migration + agentic UI

### PART 1: Grasshopper pipeline migration

- **`aria_os/grasshopper_generator.py`** — full rewrite with real RhinoCommon geometry templates:
  - `_script_cam_collar`: outer cylinder + bore hollow + 90° helical ramp (RevSurface) + radial set-screw
  - `_script_ratchet_ring`: annular ring + N asymmetric teeth (drive 8°, back 60°) via Extrusion + polar BooleanUnion
  - `_script_housing`: outer box - inner void - bearing bores - ratchet pocket - rope slot
  - `_script_catch_pawl`: box body - pivot bore - tip bevel
  - `_script_generic_llm`: LLM fallback via `generate_rhino_python()`
  - All scripts emit `BBOX:x,y,z` + export STEP/STL via `rs.Command`
  - `emit()` calls throughout; prints `[GRASSHOPPER] Script ready:` with size

- **`aria_os/orchestrator.py`** — rewritten to Grasshopper-only route:
  - Removed dead CadQuery retry loop (lines 129–369)
  - Added `validate_grasshopper_script()` check after artifact write
  - Logs `session["script_path"]`; emits step/complete/error events

- **`aria_os/llm_generator.py`** — added `generate_rhino_python(plan, goal, step_path, stl_path, repo_root)`:
  - Injects concrete `STEP_PATH`/`STL_PATH` into user prompt
  - Refactored shared `_call_anthropic()` helper
  - `emit("llm_output", ...)` before every API call

- **`aria_os/validator.py`** — added `validate_grasshopper_script(script_path)`:
  - Checks: file exists, >500 bytes, syntax (ast.parse), rhinoscriptsyntax/Rhino.Geometry import,
    `sc.doc.Objects.AddBrep`, `rs.Command`, `BBOX:` print

### PART 2: Agentic UI

- **`aria_os/event_bus.py`** — new synchronous pub/sub queue (maxsize=500, never raises)
- **`aria_os/planner.py`** — `emit("step", f"Planning: {goal}")` at start of `plan()`
- **`aria_os/cem_checks.py`** — `emit("cem", summary, {sf, passed})` at end of `run_cem_checks()`
- **`aria_server.py`** — new FastAPI backend:
  - `POST /api/generate` — starts pipeline in background thread
  - `GET  /api/log/stream` — SSE stream of all `event_bus` events
  - `GET  /api/parts` — learning log entries
  - `GET  /api/parts/{id}/stl` — STL file download
  - `GET  /api/sessions` — session log list
  - `GET  /api/cem` — latest CEM results
- **`aria-ui/`** — React + Vite + Tailwind SPA:
  - `GoalInput.jsx` — goal submission form
  - `AgentLog.jsx` — real-time SSE event stream with colour-coded type badges
  - `PartsList.jsx` — auto-refreshing parts table (pass/fail + CEM status)
  - `App.jsx` — main layout wiring all components
- **`START_ARIA_UI.bat`** / **`start_aria_ui.sh`** — one-click launchers (server + UI, auto npm install)
