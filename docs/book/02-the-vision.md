# The Vision

## Where ARIA-OS Is Going

### Near-term (Q2-Q3 2026)

**Text-to-machinable-part in under 60 seconds.** The current pipeline generates a validated STEP file in 10-45 seconds for template-matched parts and 30-90 seconds for LLM-generated parts. The target is sub-60 seconds end-to-end including validation, Onshape upload, visual verification, and DFM analysis.

**Photo-to-CNC-ready geometry.** The `--image` flag already accepts a photo and uses vision AI (Anthropic or Gemini) to extract a part description, then runs the full pipeline. The next step is integrating TRELLIS.2 (Microsoft's image-to-3D foundation model) to generate mesh geometry directly from photos, then converting that mesh to a parametric STEP file via feature recognition.

**Onshape as the collaborative layer.** The `OnshapeBridge` (`aria_os/agents/onshape_bridge.py`) already creates documents, uploads STEP files, adds metadata custom properties, generates BOMs, and creates engineering drawings. The vision: a user types a part description, ARIA-OS generates it, uploads it to their Onshape workspace, and they can immediately edit it parametrically in the browser -- then push changes back through validation.

### Mid-term (Q4 2026 - Q1 2027)

**MillForge integration for instant quoting.** The coordinator agent (`aria_os/agents/coordinator.py`) already has Phase 5 reserved for MillForge bridge -- taking a validated STEP file and submitting it for automated CNC quoting and production scheduling. The DFM agent (`aria_os/agents/dfm_agent.py`) and quote agent (`aria_os/agents/quote_agent.py`) are built and ready to connect.

**Assembly-level generation.** Currently ARIA-OS generates individual parts. The `--system` flag decomposes a high-level machine description ("design a desktop CNC router 300x300x100mm") into subsystems and parts, but assembly-level constraint solving (joint types, clearances, motion) is the next frontier. The assembly pipeline (`assemble.py`, `assemble_constrain.py`) handles static assemblies today.

**50+ templates.** The template library currently covers 39 unique parametric functions with 172+ keyword aliases. Target: 50+ templates covering every common mechanical component family, with automatic template selection from spec extraction.

### Long-term (2027+)

**Full-stack hardware development platform.** A user describes a product ("a wall-mounted auto-belay device for lead climbing"). ARIA-OS decomposes it into subsystems (mechanical, electrical, firmware), generates all parts, runs physics validation, produces PCB layouts (ECAD generator already exists), generates CNC toolpaths, and submits the complete BOM for manufacturing. The companion app (`aria-climb/`) provides the operator interface.

**DeepSeek-R1 for local generation.** The LLM fallback chain (Anthropic -> Gemini -> Ollama -> heuristic) already supports local models via Ollama. As reasoning-capable local models improve, the dependency on cloud APIs decreases. The goal is a fully local pipeline for air-gapped environments (defense, classified hardware).

**Gemini Flash for sub-5-second visual verification.** Visual verification currently takes 3-8 seconds per part. Gemini 2.5 Flash is already the default (faster and cheaper than Claude for vision). As inference speeds improve, visual verification becomes instantaneous.

## The Flywheel

Each part generated through ARIA-OS improves the system:

1. **Template expansion**: Every LLM-generated part that passes validation is a candidate for a new template.
2. **Failure learning**: Every generation failure is logged to `outputs/cad/learning_log.json` with the error and fix. These patterns are injected into `context/aria_failures.md` and fed back into future LLM prompts.
3. **Spec extraction improvement**: Every new part description that fails to parse adds a new regex pattern to `spec_extractor.py`.
4. **CEM calibration**: Hardware drop tests on the ARIA auto-belay will calibrate the physics models, improving safety factor accuracy for all future parts.
