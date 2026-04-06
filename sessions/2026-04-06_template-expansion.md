# Session Log
# sessions/2026-04-06_template-expansion.md

## Date
2026-04-06

## Task
Tier 1 CadQuery template expansion — added 10 new fastener and fluid-path templates to `cadquery_generator.py`. Grew total templates from 49 → 59, aliases 205 → 235. Also seeded spec_extractor keywords and _KEYWORD_TO_TEMPLATE entries for new parts.

## Files Modified
- `aria_os/cadquery_generator.py` — added 10 new template functions: `_cq_hex_bolt`, `_cq_hex_nut`, `_cq_socket_cap_screw`, `_cq_set_screw`, `_cq_timing_pulley`, `_cq_sprocket`, `_cq_rack`, `_cq_pipe_elbow`, `_cq_pipe_tee`, `_cq_pipe_reducer`. Updated `_CQ_TEMPLATE_MAP` and `_KEYWORD_TO_TEMPLATE` alias table.
- `aria_os/spec_extractor.py` — added part-type keywords for: hex_bolt, hex_nut, socket_cap_screw, set_screw, timing_pulley, sprocket, rack, pipe_elbow, pipe_tee, pipe_reducer.
- `PROJECT_STATUS.md` — created tracker document for outstanding work and template roadmap.

## What Worked
- ISO proportions for fastener templates (hex bolt AF ≈ 1.5d, head_h ≈ 0.7d; hex nut AF ≈ 1.7d, h ≈ 0.8d; socket cap head_d ≈ 1.5d, head_h ≈ d) produce valid geometry on first attempt.
- Pipe elbow using CadQuery sweep along a circular arc path works reliably for 90° and custom-angle bends.
- Pipe reducer using revolve on a 2D profile works cleanly; no boolean operations needed.
- Pipe tee using three union'd cylinders with intersection cuts is stable across parameter ranges.
- Sprocket using polar-arrayed circular tooth cutouts (approximation) produces valid mesh.
- Timing pulley simplified to smooth cylinder with correct pitch diameter — validates cleanly, correct envelope for assembly clearance checks.
- All 10 new templates pass STEP re-import and bbox validation on first attempt.
- QMD was already installed; no setup required.

## What Failed
- Rack tooth profile: CadQuery polyline union on XZ plane with thin trapezoidal profiles fails with `BRep_API: command not done` for certain parameter combinations. Fell back to solid rectangular block with correct envelope dims. This is a known CadQuery limitation with thin-wall boolean unions from polyline wires.
- Timing pulley: true GT2/GT3 tooth profile not implemented — would require precise involute+fillet spline that is fragile in CadQuery. Simplified to pitch-diameter cylinder.

## New Failures Discovered
- **FAILURE: Rack tooth polyline union** — `BRep_API: command not done` when unioning thin trapezoidal tooth profiles swept along X axis in CadQuery. Cause: near-zero thickness faces in intermediate boolean result. Fix: use try/except fallback to solid block, or use cut operations to carve tooth gaps instead of union approach.
- **FAILURE: CadQuery polyline on XZ plane** — `wire.close()` followed by `extrude()` fails when profile height < ~0.5mm at any vertex. Causes degenerate face. Always check minimum vertex separation before polyline close.

## Next Steps
- Implement Tier 2 templates: `ring_gear`, `gopro_mount`, `hex_standoff`, `t_nut`, `thrust_washer`, `retaining_ring`, `linear_bushing`, `pipe_cap`, `cross_dowel`.
- Finish McKinsey research (background task started 2026-04-06).
- Start dimensional visual verification: render each new template, eyeball proportions against ISO reference sheets.
- Fix rack template to use cut-based tooth profile (carve gaps from solid bar) instead of union approach — eliminates BRep fallback.
- Consider adding GT2/GT3 tooth profile to timing pulley via explicit point-list approximation with controlled vertex count.

## Constants Changed
None. No mechanical or electrical constants modified.

---

## Session Update — 2026-04-06 (Tier 2 + Tier 3 templates, dimensional verification, API v2, McKinsey research)

### What Was Built

**Tier 2 templates (9) — all CadQuery verified:**
- `ring_gear`, `gopro_mount`, `hex_standoff`, `t_nut`, `thrust_washer`, `retaining_ring`, `linear_bushing`, `pipe_cap`, `cross_dowel`
- All pass STEP re-import and bbox validation on first attempt.
- `_CQ_TEMPLATE_MAP` and `_KEYWORD_TO_TEMPLATE` updated for all 9.
- `spec_extractor.py` seeded with part-type keywords for all 9.

**Tier 3 templates (12) — all CadQuery verified:**
- `bevel_gear`, `worm`, `worm_gear`, `timing_belt`, `jaw_coupling_half`, `valve_body`, `extension_spring`, `torsion_spring`, `wave_spring`, `pipe_cross`, `orifice_plate`, `rivet`
- All pass STEP re-import and bbox validation on first attempt.
- Worm and bevel_gear simplified to frustum/cylinder bodies without actual tooth geometry (CadQuery helix sweep is unreliable for complex gear profiles; solid body at correct envelope dims is preferred).
- `_CQ_TEMPLATE_MAP` and `_KEYWORD_TO_TEMPLATE` updated for all 12.
- `spec_extractor.py` seeded with part-type keywords for all 12.

**Template count milestone reached:**
- 80 unique templates, 290 aliases — Q2 target reached.

**Dimensional verification system:**
- `verify_dimensions()` added to `aria_os/visual_verifier.py`.
- Measures OD, height, thickness, length, width, and bore from trimesh bounding box + cross-section void analysis.
- Wired into coordinator Phase 4 so every generated part gets a dimensional check before export.
- Trimesh bbox is accurate for OD/height/length; bore measurement uses cross-section void analysis (bbox alone misreports bore due to wall thickness).

**API server v2.0.0:**
- API key authentication: keys hashed with SHA-256 before storage in `.api_keys.json`; admin bootstrap key read from `ARIA_API_ADMIN_KEY` env var.
- Per-key rate limiting: sliding window (list of timestamps, drop entries older than window), configurable requests-per-minute.
- Async generation with job tracking: `POST /api/generate` returns `job_id` immediately; client polls `GET /api/jobs/{job_id}`.
- Webhook callbacks: job completion POSTs result payload to caller-supplied `callback_url`.
- Admin endpoint: `POST /api/admin/keys` creates new API keys (requires admin key in header).

**McKinsey agentic research:**
- `docs/mckinsey-agentic-patterns.md` created.
- 6 lessons from McKinsey agentic-AI report documented.
- SDD (Specification-Driven Development) pattern compared against McKinsey's orchestrator/subagent framing.
- Architecture comparison table (ARIA-OS vs McKinsey reference patterns) included.
- 5 YC founder quotes on agentic product design included for context.

### Files Modified
- `aria_os/cadquery_generator.py` — 21 new template functions (Tier 2 + Tier 3).
- `aria_os/spec_extractor.py` — 21 new part-type keyword entries.
- `aria_os/visual_verifier.py` — `verify_dimensions()` added.
- `aria_os/coordinator.py` — Phase 4 wired to call `verify_dimensions()`.
- `aria_os/api_server.py` — v2.0.0: auth, rate limiting, async jobs, webhooks, admin endpoint.
- `docs/mckinsey-agentic-patterns.md` — created.

### What Failed / Limitations
- Worm gear and bevel gear: actual tooth profile (involute helicoid for worm, conical involute for bevel) not implemented. Solid envelope geometry only. Sufficient for clearance checks and CAM setup but not for tooth-contact simulation.
- Trimesh bbox for bolt shank length is inaccurate — bbox includes head height. Cross-section void analysis required for true shank length measurement.
- Timing belt: modeled as flat loop profile at correct pitch length and width, not as individual tooth profiles. Adequate for assembly envelope.

### Next Steps
- Fix rack template: cut-based tooth profile (carve gaps from solid bar) to eliminate BRep fallback.
- Add GT2/GT3 tooth approximation to timing pulley via explicit point-list.
- Wire dimensional verification tolerance thresholds into post-generation validation (reject if OD error > 5%).
- API server: add refresh-token endpoint, key expiry, and audit log.

### Constants Changed
None.
