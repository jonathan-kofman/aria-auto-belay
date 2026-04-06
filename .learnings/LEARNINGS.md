# Learnings & Patterns

<!-- Format: ## Learning Title / Date / Context / Insight / Application -->

## CadQuery Polyline Union Fails on Thin Tooth Profiles
**Date:** 2026-04-06
**Context:** Rack template — tried to build tooth profiles by unioning trapezoidal polyline wires along X axis.
**Insight:** CadQuery polyline union on XZ plane with thin trapezoidal profiles (height < ~1mm at any vertex, or near-zero face area in intermediate boolean) fails with `BRep_API: command not done`. The boolean engine produces degenerate faces it cannot resolve.
**Application:** For gear/rack tooth profiles, use cut operations to carve tooth gaps from a solid blank instead of unioning tooth shapes. Wrap polyline union attempts in try/except and fall back to valid solid geometry. Always check minimum vertex separation before calling `wire.close()`.

## Compute Template Math at Generation Time, Not Execution Time
**Date:** 2026-04-06
**Context:** CadQuery template functions called by the generator at runtime.
**Insight:** Template functions should compute all derived geometry (point lists, radii, offsets) in Python at template-generation time, then embed the computed values as `repr()` literals in the generated CadQuery script string. Doing math inside the generated script string adds complexity and makes debugging harder.
**Application:** In `cadquery_generator.py` template functions: compute everything in Python, embed final numeric values into the f-string. Do not emit `import math` or arithmetic expressions into the generated script.

## ISO Fastener Proportions for CadQuery Templates
**Date:** 2026-04-06
**Context:** Hex bolt, hex nut, and socket cap screw templates added to `cadquery_generator.py`.
**Insight:** ISO standard proportions that produce realistic, valid geometry on first attempt:
- ISO 4014 hex bolt: AF (across-flats) ≈ 1.5×d, head height ≈ 0.7×d, thread depth = nominal length.
- ISO 4032 hex nut: AF ≈ 1.7×d, nut height ≈ 0.8×d.
- ISO 4762 socket cap screw: head diameter ≈ 1.5×d, head height ≈ 1.0×d, hex key socket depth ≈ 0.5×d.
**Application:** Use these ratios as defaults in any fastener template. They scale correctly across M3–M20 range without additional parameter tuning.

## Worm and Bevel Gear CadQuery Templates: Use Envelope Geometry, Not Tooth Profiles
**Date:** 2026-04-06
**Context:** Tier 3 template expansion — worm, worm_gear, bevel_gear templates added to `cadquery_generator.py`.
**Insight:** CadQuery's sweep along a helix is unreliable for complex gear profiles (worm thread, conical involute bevel tooth). The sweep operation produces `BRep_API: command not done` or silent geometry corruption for non-trivial wire profiles. A solid frustum/cylinder body at the correct pitch diameter, face angle, and envelope dimensions passes all bbox and STEP re-import checks and is sufficient for assembly clearance, CAM setup, and CEM checks.
**Application:** For worm and bevel gear templates, generate a solid body at correct envelope dimensions. Document the limitation in template comments. Add actual tooth profile only if driven by a specific requirement (tooth-contact simulation, FEA on tooth root), and only after verifying the wire sweep is stable for the target parameter range.

## Dimensional Verification: Trimesh Bbox vs. Cross-Section Void Analysis
**Date:** 2026-04-06
**Context:** `verify_dimensions()` added to `aria_os/visual_verifier.py`, wired into coordinator Phase 4.
**Insight:** Trimesh bounding box measurement is accurate for OD, height, length, and width (within ~0.1mm for clean geometry). It is inaccurate for bore diameter and bolt shank length because the bbox includes head geometry and wall thickness respectively. For bore measurement, cross-section void analysis (slice mesh at mid-height, find largest interior void) gives the actual bore diameter. For bolt shank length, a similar cross-section approach or explicit geometry query is needed.
**Application:** In `verify_dimensions()`, use bbox for OD/height/length/width. Use cross-section void analysis for bore. Document bbox-only measurements as approximate in any user-facing output.

## FastAPI API Key Auth Pattern: SHA-256 Hash + Env Bootstrap + Sliding Window Rate Limiting
**Date:** 2026-04-06
**Context:** API server v2.0.0 added to `aria_os/api_server.py`.
**Insight:** Three patterns that compose cleanly for a FastAPI key-auth system:
1. **Hashed storage**: hash keys with `hashlib.sha256(key.encode()).hexdigest()` before writing to `.api_keys.json`. Never store plaintext. On request, hash the incoming key and compare against stored hashes.
2. **Admin bootstrap**: read admin key from `ARIA_API_ADMIN_KEY` env var at startup, hash it, insert into keys dict. This avoids a chicken-and-egg problem (needing a key to create the first key).
3. **Sliding window rate limiting**: store a list of UTC timestamps per key. On each request, drop timestamps older than the window (e.g., 60 seconds), then check `len(timestamps) < limit`. Append current timestamp if allowed. Thread-safe with a per-key `asyncio.Lock` or simple dict lock.
**Application:** Use this pattern for any internal FastAPI service that needs lightweight auth without a full OAuth stack. For production, replace the JSON file store with Redis or a DB.
