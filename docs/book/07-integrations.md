# Integrations

## External Services and APIs

### Onshape REST API

**File:** `aria_os/agents/onshape_bridge.py`
**Auth:** `ONSHAPE_ACCESS_KEY` + `ONSHAPE_SECRET_KEY` (Basic auth over HTTPS)
**API version:** v6

The Onshape bridge turns ARIA-OS from a local CAD generator into a collaborative design tool. After geometry is generated and validated locally, the bridge:

1. **Creates a document** in the user's Onshape workspace with a descriptive name
2. **Uploads the STEP file** as a blob, which Onshape translates into a parametric Part Studio
3. **Sets custom properties** on the part: material, dimensions, CEM safety factors, generation timestamp
4. **Generates a BOM** from the part metadata
5. **Creates an engineering drawing** element linked to the generated part
6. **Verifies the upload** by re-reading the document and confirming the part exists

This means a user can type a part description in the terminal and immediately open it in Onshape's browser-based CAD editor, share it with teammates, add manual features, and export for manufacturing -- all without installing any desktop CAD software.

### Anthropic Claude API

**File:** `aria_os/llm_client.py`
**Auth:** `ANTHROPIC_API_KEY` in `.env`

Primary LLM backend. Used for:

- **CadQuery code generation**: When no template matches, Claude generates a complete CadQuery script from an engineering brief that includes CEM physics outputs, mechanical constants, and known failure patterns.
- **Visual verification**: Three rendered views of the generated part (top, front, isometric) are sent to Claude with a feature checklist. Claude confirms that expected features (bore, teeth, bolt holes, L-shape, fins) are visible.
- **Failure diagnosis**: When generation fails, Claude analyzes the error traceback and suggests fixes, which are injected into the retry prompt.
- **Spec synthesis** (coordinator path): In Phase 2, Claude synthesizes a geometry spec from web research results + user description.

### Google Gemini API

**File:** `aria_os/llm_client.py`
**Auth:** `GOOGLE_API_KEY` in `.env`
**Default model:** `gemini-2.0-flash` (override with `GEMINI_MODEL`)

First fallback LLM. Supports both the new `google-genai` SDK and the legacy `google-generativeai` SDK. Used for:

- **Code generation**: Same capability as Claude, lower priority in the chain
- **Vision verification**: Gemini 2.5 Flash is actually the preferred vision backend (faster and cheaper than Claude for visual checks)
- **Image-to-CAD**: `analyze_image_for_cad(image_path, hint)` uses Gemini vision to extract a part description from a photo

### Ollama (Local Inference)

**File:** `aria_os/llm_client.py`
**Config:** `OLLAMA_HOST` (default: `http://localhost:11434`), `OLLAMA_MODEL` (default: `deepseek-coder`)

Local LLM inference for air-gapped or cost-sensitive environments. Install Ollama, pull a model (`ollama pull deepseek-coder`), and ARIA-OS auto-detects it via the `/api/health` endpoint.

Limitations: Ollama 7B models cannot reliably generate valid CadQuery code. Best used for spec extraction and simple modifications. A `_LOCAL_MODEL_NOTE` is injected into the system prompt warning the model about CadQuery API constraints.

The `aria_os/agents/ollama_config.py` file manages Ollama configuration for the agent pipeline.

### MillForge AI (CNC Quoting Bridge)

**Files:** `aria_os/agents/quote_agent.py`, `aria_os/agents/coordinator.py` (Phase 5)

MillForge integration is built into the coordinator pipeline but awaits production API access. The quote agent:

1. Takes a validated STEP file + material + quantity
2. Analyzes machinability (axis count, tool requirements, setup complexity)
3. Submits to MillForge for automated CNC quoting
4. Returns estimated cost, lead time, and recommended machine

The DFM agent (`aria_os/agents/dfm_agent.py`) runs first, flagging manufacturability issues (thin walls, deep cavities, undercuts) before the quote is requested.

### Web Search (Research Agent)

**File:** `aria_os/agents/search_chain.py`

The coordinator's Phase 1 runs 4 parallel web searches to gather context:
- Material properties and yield strength
- Part shape and geometry description
- Real-world dimensions and measurements
- Existing CAD references and 3D models

Results are saved to the job scratchpad (`workspace/scratchpad/<job_id>/`) and used by Phase 2 to synthesize a geometry spec when the user's description is incomplete.

### Firebase (Companion App)

**Files:** `aria-climb/src/services/firebase/`

The companion app uses Firebase for:
- **Authentication**: Email/password + role selection (climber vs gym owner)
- **Firestore**: Device state, telemetry, sessions, incidents, maintenance actions
- **Cloud Messaging**: Push notifications for alerts

Firebase config requires `google-services.json` in `aria-climb/android/app/` before building.

### Edge Impulse (Voice AI)

**Files:** `firmware/esp32/aria_esp32_firmware.ino`, `tools/aria_collect_audio.py`

Edge Impulse hosts the trained voice classification model that recognizes climber commands: "take", "slack", "lower", "rest", "watch me", "up". The trained model is exported as a C++ library and compiled into the ESP32 firmware. Audio dataset collection is done via `tools/aria_collect_audio.py` or `RECORD_EDGE_IMPULSE_AUDIO.bat`.
