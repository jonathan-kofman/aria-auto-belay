# ARIA Project Status Tracker

> **Single source of truth for version, phase, and next steps.**
> Update this file at the start/end of every significant session.

---

## Current Version

| Component | Version | Phase | Status |
|---|---|---|---|
| ARIA-OS (CAD pipeline) | 0.9.0-beta | Q2 2026 — Expansion | Active development |
| Hardware (STM32 + ESP32) | 0.1.0-pre | Pre-hardware | Firmware written, hardware not arrived |
| aria-climb (mobile app) | 1.0.0 | Pre-hardware | Fully implemented, awaiting device + google-services.json |
| Streamlit Dashboard | 1.0.0 | Stable | Operational |

**Overall project phase: PRE-HARDWARE / SOFTWARE COMPLETE**

---

## What Is Done

### ARIA-OS v0.9.0-beta (March 2026)
- [x] 5-phase coordinator pipeline (research -> synthesis -> geometry -> manufacturing -> finalize)
- [x] 49 CadQuery templates, 205 aliases, 59 keyword entries
- [x] Multi-tier LLM fallback: Template -> Zoo.dev -> Claude -> Gemini -> Gemma 4 -> Deterministic
- [x] Visual verification (3-view render -> vision AI -> feature-level PASS/FAIL)
- [x] Post-gen validation + repair (up to 10 iterations, failure context injection)
- [x] Assembly detection + multi-part generation
- [x] GD&T engineering drawings (SVG)
- [x] Fusion 360 CAM scripts + CNC setup sheets
- [x] Machinability analysis + DFM scoring + cost estimation
- [x] FEA/CFD screening
- [x] Onshape bridge, Zoo.dev text-to-STEP
- [x] ECAD (KiCad PCB generation + variant studies)
- [x] Civil engineering DXF (50-state DOT standards, 5 disciplines)
- [x] Blender lattice generation
- [x] CEM physics (ARIA + LRE domains)
- [x] FastAPI server (/api/generate, /api/health, /api/runs)
- [x] 57 parts generated on disk with meta tracking

### Hardware v0.1.0-pre (March 2026)
- [x] STM32 firmware: SimpleFOC, HX711, state machine, PID tension loop (525 lines)
- [x] Safety layer: watchdog, fault recovery, power-on boot sequence (404 lines)
- [x] ESP32 firmware: voice (Edge Impulse), CV, BLE, UART bridge (743 lines)
- [x] Wearable companion firmware
- [x] Python state machine mirror + simulator
- [x] Constants sync tool + PID tuner
- [ ] Hardware arrived
- [ ] Tested on real hardware

### aria-climb v1.0.0 (March 2026)
- [x] Full auth flow (Login, Signup, RoleSelect, ClaimGym)
- [x] Climber screens (Home, LiveSession, GymOnboarding, Sessions, Leaderboard, Profile)
- [x] Gym owner screens (Dashboard, DeviceDetail, Provisioning, Alerts, Sessions, Routes)
- [x] BLE stack + Firebase integration + provisioning
- [x] i18n (en, de, es, fr, ja)
- [ ] google-services.json configured
- [ ] First Android build (EAS or local)
- [ ] Real device connection test

---

## What Is Next

### Immediate (April 2026)

| Task | Priority | Component | Status |
|---|---|---|---|
| Template expansion (49 -> 80) | HIGH | ARIA-OS | Done (80 templates, 290 aliases) |
| Dimensional visual verification | HIGH | ARIA-OS | Done (trimesh bbox + cross-section bore measurement) |
| Cloud API deployment (auth, rate limiting) | HIGH | ARIA-OS | Done (v2.0.0: API keys, rate limiting, webhooks, async jobs) |
| Assembly v2 (constraint-based) | MEDIUM | ARIA-OS | Not started |

### Integration Sprint (from claude_task.md, pre-YC May 4)

| Task | Priority | Status |
|---|---|---|
| QMD install + integration | 1 (do first) | Done (was already set up) |
| McKinsey agentic patterns research | 2 | Done (docs/mckinsey-agentic-patterns.md) |
| PentAGI clone + review | 3 (curiosity) | Not started |

### Q3 2026
- Manufacturer API integrations (MillForge, Xometry, Protolabs)
- G-code post-processing (direct, not just Fusion CAM scripts)
- Template learning from successful LLM generations

### Q4 2026
- CI/CD + template regression tests
- Multi-body parts, sheet metal, surface modeling
- Part library + version history + team workspace

---

## Metrics

| Metric | Mar 2026 (actual) | Jun 2026 (target) | Sep 2026 (target) |
|---|---|---|---|
| Templates | **80** (was 49) | 80 | 120 |
| Template aliases | **290** (was 205) | 350 | 500 |
| First-attempt pass (template) | 100% | 100% | 100% |
| First-attempt pass (LLM) | ~60% | ~70% | ~80% |
| Pass after refinement | ~80% | ~90% | ~93% |
| Avg pipeline time | 30-90s | 20-60s | 15-40s |
| Visual verification accuracy | ~85% | ~90% | ~93% |
| Active API users | 0 | 10 | 50 |

---

## Key Dates

| Date | Event |
|---|---|
| 2026-03-27 | Firmware merged (all three layers) |
| 2026-04-03 | Last pipeline test session |
| 2026-05-04 | YC S26 application deadline |
| TBD | Hardware arrives |
| TBD | First real-device test |

---

*Last updated: 2026-04-06 (All Q2 HIGH priorities complete: 80 templates, dimensional verification, API v2.0.0)*
