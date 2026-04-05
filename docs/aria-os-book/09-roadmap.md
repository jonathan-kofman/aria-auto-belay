[<-- Back to Table of Contents](./README.md) | [<-- Previous: Operations](./08-operations.md) | [Next: Appendix -->](./10-appendix.md)

---

# Roadmap

## What Is Done (March 2026)

### Core Pipeline

| Feature | Status | Notes |
|---|---|---|
| 5-phase coordinator pipeline | Complete | Research, synthesis, geometry, manufacturing, finalize |
| 49 CadQuery templates | Complete | Covers structural, fastener, enclosure, drivetrain, fluid parts |
| 205 template aliases | Complete | Natural language -> template mapping |
| 59 keyword entries | Complete | Fuzzy matching for slug-based part IDs |
| 25 CadQuery operations reference | Complete | Injected into LLM prompts for code generation |
| Spec extraction (regex-based) | Complete | 40 test cases, handles WxHxD, NxM bolt shorthand, radius->diameter |
| Multi-tier fallback chain | Complete | Template -> Zoo.dev -> Claude -> Gemini -> Gemma 4 -> Deterministic |
| Visual verification | Complete | 3-view render -> Gemini/Claude vision -> feature-level PASS/FAIL |
| Post-gen validation + repair | Complete | Bbox, STEP readability, mesh integrity, bore detection, STL repair |
| Refinement loop | Complete | Up to 10 iterations with failure context injection |
| Assembly detection | Complete | Multi-part goals decomposed and generated individually |

### Manufacturing Outputs

| Feature | Status | Notes |
|---|---|---|
| GD&T engineering drawings (SVG) | Complete | A3 landscape, 3 ortho views, title block |
| Fusion 360 CAM scripts | Complete | Adaptive clearing, parallel finish, contour, drill |
| CNC setup sheets (MD + JSON) | Complete | Material, fixturing, tool list, operation sequence |
| Machinability analysis | Complete | Undercut detection, axis classification, thin wall check |
| DFM scoring | Complete | Score/100 + process recommendation |
| Cost estimation (QuoteAgent) | Complete | Material + machining time estimate |
| FEA screening | Complete | Beam bending, hoop stress, gear tooth, bolt shear |

### Integrations

| Feature | Status | Notes |
|---|---|---|
| Onshape bridge | Complete | STEP upload, translation, BOM, mass properties, drawing |
| Zoo.dev text-to-STEP | Complete | Fallback after templates |
| Anthropic Claude | Complete | Primary cloud LLM for code gen |
| Google Gemini (code + vision) | Complete | Fast fallback + visual verification |
| Gemma 4 via Ollama | Complete | Free local LLM, Lightning AI tunnel support |
| Lightning AI auto-reconnect | Complete | SSH tunnel re-establishment |
| FastAPI server | Complete | `/api/generate`, `/api/health`, `/api/runs` |
| Streamlit dashboard | Complete | Generation UI, CEM tuning, log viewer |

### Specialized Domains

| Feature | Status | Notes |
|---|---|---|
| ECAD (KiCad PCB) | Complete | Component matching, BOM, ERC validation |
| Civil engineering DXF | Complete | 50-state DOT standards, 5 disciplines, NCS layers |
| Lattice generation (Blender) | Complete | Honeycomb, gyroid, voronoi patterns |
| CEM physics (ARIA + LRE) | Complete | Deterministic geometry from physics parameters |

---

## What Is Next (Q2 2026)

### Template Expansion (Priority: HIGH)

- Target: 80 templates (from 49)
- Focus areas: fasteners (hex bolt, socket cap, set screw), drivetrain (bevel gear, worm gear, timing pulley), fluid (pipe tee, pipe elbow, valve body)
- Each new template needs: function, map entries, keyword entries, spec extractor keywords, test case

### Improved Visual Verification (Priority: HIGH)

- Move from feature presence/absence to dimensional verification
- Measure bore diameter, bolt spacing, overall dimensions from rendered views
- Train a lightweight dimension extraction model or use Gemini's spatial reasoning

### Cloud API (Priority: HIGH)

- Deploy FastAPI server as a hosted endpoint
- Authentication (API keys per user)
- Rate limiting and usage tracking
- Webhook callbacks for long-running generation

### Assembly v2 (Priority: MEDIUM)

- Constraint-based assembly (not just positioning)
- Automatic mate detection from part geometry
- Interference checking during assembly, not just post-assembly

---

## Q3 2026

### Manufacturer Integration

- MillForge direct quoting and ordering
- Xometry API integration for instant quotes
- Export to Protolabs and similar services
- Quote comparison across manufacturers

### G-Code Post-Processing

- Generate G-code directly (not just Fusion 360 CAM scripts)
- Post-processor for Tormach, HAAS, Fanuc, Grbl
- Toolpath simulation and verification

### Template Learning

- Analyze successful LLM generations and extract new templates automatically
- Clustering of generated parts to identify common patterns
- User feedback loop: "this part was correct" -> template candidate

---

## Q4 2026

### Production Hardening

- CI/CD pipeline with template regression tests
- STEP file golden-set comparison (geometry diff)
- Automated stress testing: generate 1000 random parts, measure pass rate
- Performance optimization: target <10s for full pipeline on template path

### Advanced Geometry

- Multi-body parts (e.g., bearing assembly with inner/outer race + balls)
- Sheet metal support (bend lines, k-factor, flat pattern export)
- Surface modeling for organic shapes (consumer products)

### Collaboration Features

- Part library: save/share generated parts with parameters
- Version history: track parameter changes per part
- Team workspace: shared Onshape project with auto-generated parts

---

## Post-YC Vision

### Platform Play

ARIA-OS becomes a platform API that other tools build on:
- Slack bot: `/cad bracket 100x60mm` -> STEP file in thread
- ERP integration: BOM line items -> 3D models generated automatically
- Quoting platforms: submit text description, receive model + quote instantly

### Enterprise Features

- SOC 2 compliance for hosted API
- Custom template libraries per organization
- On-premise deployment option
- ITAR-compliant data handling for defense manufacturing

### Market Expansion

- Consumer product design (cases, enclosures, fixtures)
- Architecture (structural steel details, connection plates)
- Robotics (joints, links, end effectors, sensor mounts)
- Aerospace (brackets, fittings, structural members)

---

## Metrics Dashboard (Monthly Tracking)

| Metric | Mar 2026 | Jun Target | Sep Target | Dec Target |
|---|---|---|---|---|
| Templates | 49 | 80 | 120 | 150 |
| Template aliases | 205 | 350 | 500 | 650 |
| First-attempt pass (template) | 100% | 100% | 100% | 100% |
| First-attempt pass (LLM) | ~60% | ~70% | ~80% | ~85% |
| Pass after refinement | ~80% | ~90% | ~93% | ~95% |
| Avg time (full pipeline) | 30-90s | 20-60s | 15-40s | 10-30s |
| Visual verification accuracy | ~85% | ~90% | ~93% | ~95% |
| Active API users | 0 | 10 | 50 | 200 |

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: Operations](./08-operations.md) | [Next: Appendix -->](./10-appendix.md)
