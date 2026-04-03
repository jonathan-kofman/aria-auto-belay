# Roadmap

## What Has Been Built

### Completed (as of March 2026)

- 39 parametric CadQuery templates covering ARIA structural parts, generic mechanical components, standard hardware (NEMA motors, MGN rails, ball bearings), and specialized parts (nozzles, escape wheels, spoked wheels)
- 172+ keyword aliases for automatic template matching from natural language
- Structured spec extraction with 40+ regex patterns for dimensions, materials, and part types
- Multi-retry validation loop (up to 3 attempts) with failure-context injection
- Visual verification via rendered views + vision LLM feature checklist
- Onshape integration: document creation, STEP upload, metadata, BOM, drawing generation
- CEM physics for ARIA auto-belay parts (tooth shear, hoop stress, bending) and liquid rocket engines (nozzle geometry from thrust + Pc)
- 5-phase coordinator agent with parallel research, spec synthesis, geometry generation, DFM analysis
- CAM toolpath generation for Fusion 360 (adaptive clearing, parallel finish, contour, drill)
- Machinability validation (undercut detection, axis classification: 3/4/5-axis)
- CNC operator setup sheets (markdown + JSON, schema-validated)
- GD&T engineering drawing SVG generation (A3 landscape, 3 orthographic views)
- Civil engineering DXF generation (50+ NCS layers, all 50 US state DOT standards)
- ECAD PCB generation for KiCad (component placement, BOM, firmware pin extraction)
- FastAPI server for programmatic access
- Companion app (React Native/Expo) with BLE, Firebase, gym mode, climber mode
- Full firmware: STM32 safety layer (524 lines), ESP32 intelligence layer, wearable BLE

### In Progress

- Hardware procurement and first power-on (firmware written but untested on real hardware)
- CEM calibration via hardware drop tests
- MillForge production API integration (agents built, awaiting API access)

## What Is Next

### Q2 2026: Template Expansion and Stress Testing

**Target: 50+ templates.** Priority additions:
- Threaded fasteners (bolts, nuts, set screws)
- Spring types (compression, extension, torsion)
- Pneumatic fittings
- Welding fixtures
- Jigs and work-holding

**10-part stress test validation.** Run 10 diverse parts through the full pipeline (generate -> validate -> Onshape upload -> visual verify -> DFM -> quote) and confirm 10/10 pass rate. Document exact dimensional accuracy and visual verification results.

### Q3 2026: TRELLIS.2 Image-to-Mesh Integration

Microsoft TRELLIS.2 generates 3D meshes from single images. Integration plan:

1. User uploads a photo of a mechanical part
2. TRELLIS.2 generates a textured mesh
3. ARIA-OS converts the mesh to a feature-recognized STEP file (edge detection, face classification)
4. The STEP file enters the standard validation + Onshape pipeline

This replaces the current image path (vision LLM extracts text description -> generate from text) with a direct geometric path.

### Q3 2026: DeepSeek-R1 for Local Code Generation

Current local models (deepseek-coder 6.7B) cannot reliably generate CadQuery code. DeepSeek-R1 (and successors) with reasoning capabilities may close this gap. The goal is a fully local pipeline for:

- Air-gapped defense/aerospace environments
- Cost-sensitive users who cannot afford cloud API calls
- Privacy-sensitive designs

### Q4 2026: Gemini Flash Sub-5-Second Visual Verification

Visual verification currently takes 3-8 seconds (render 3 views + send to vision LLM + parse response). As Gemini Flash inference speeds improve:

- Target: < 2 seconds for visual verification
- Enable visual verification on every generation, not just `--full` runs
- Use visual feedback as an input to the refinement loop (not just pass/fail)

### Q4 2026: Assembly-Level Generation

Current state: individual parts are generated independently. Assemblies are composed from existing parts via JSON configs (`assemble.py`).

Target: generate an assembly from a single description. "Design a 2-stage planetary gearbox, 5:1 ratio per stage, NEMA 23 input" should produce all gears, shafts, bearings, housing, and a constrained assembly with correct clearances.

Requirements:
- Joint type inference (revolute, prismatic, fixed)
- Clearance calculation between mating parts
- Constraint solving for assembly positions
- Bill of materials with fastener selection

### 2027: MillForge Production Integration

End-to-end: text description -> validated STEP -> automated CNC quote -> production scheduling -> part delivery tracking.

The DFM agent and quote agent are built. The coordinator's Phase 5 is reserved. What remains is connecting to MillForge's production API and handling the feedback loop (quote rejected -> modify geometry -> re-quote).

### 2027: Multi-User Collaborative Design

Onshape provides the collaborative layer. The extension:
- Multiple users can submit part requests to a shared ARIA-OS workspace
- Version control on generated parts (already tracked via `outputs/cad/meta/` with git SHA)
- Design review workflow: generate -> review in Onshape -> approve -> manufacture
- Team-level template libraries and material preferences
