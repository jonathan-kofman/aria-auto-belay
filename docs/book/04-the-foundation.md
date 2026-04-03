# The Foundation

## Tech Stack and Dependencies

### Core Geometry Engine

| Package | Version | Role |
|---------|---------|------|
| CadQuery | 2.7.0 | Parametric 3D modeling kernel (built on OpenCascade). All template geometry is CadQuery code. Headless -- no GUI required. |
| cadquery-ocp | 7.8.1.1 | OpenCascade Python bindings for CadQuery |
| trimesh | >= 4.0 | Mesh analysis: watertight checks, bore detection, bounding box validation, STL repair |
| scipy | >= 1.11.0 | FEA beam bending, interpolation for physics analyzer |
| numpy | 2.4.3 | Array operations for geometry and physics |

### LLM Backends (Priority Chain)

ARIA-OS uses a cascading LLM chain. The pipeline never crashes due to a missing API key.

| Backend | Config | Use Case |
|---------|--------|----------|
| **Anthropic Claude** | `ANTHROPIC_API_KEY` in `.env` | Primary: code generation, visual verification, failure diagnosis |
| **Google Gemini** | `GOOGLE_API_KEY` in `.env` | Fallback: code generation + vision. Default model: `gemini-2.0-flash` (override with `GEMINI_MODEL`) |
| **Ollama (local)** | `ollama pull deepseek-coder` | Local inference: spec extraction, simple generation. Set `OLLAMA_HOST` / `OLLAMA_MODEL` if non-default |
| **Heuristic templates** | None required | Zero-network fallback: 39 templates work with no API keys at all |

The unified client lives in `aria_os/llm_client.py`. `call_llm(prompt, system, *, repo_root)` is the single entry point. `analyze_image_for_cad(image_path, hint)` handles vision tasks.

### Cloud CAD Integration

| Service | Authentication | Capability |
|---------|---------------|------------|
| **Onshape REST API** | `ONSHAPE_ACCESS_KEY` + `ONSHAPE_SECRET_KEY` in `.env` | Create documents, upload STEP, add metadata properties, generate BOMs, create engineering drawings, verify uploads |

The Onshape bridge (`aria_os/agents/onshape_bridge.py`) uses Basic auth over the v6 REST API. Generate keys at https://cad.onshape.com/appstore/dev-portal.

### Rendering and Visualization

| Package | Role |
|---------|------|
| matplotlib | Headless STL rendering for visual verification (Agg backend, no display server) |
| Streamlit | Dashboard: CEM parameter tuning, design history, state machine visualization |
| plotly | Interactive charts in the dashboard (drop sim, PID response) |
| Three.js | Browser-based 3D STL preview (embedded in `preview_ui.py`, no server) |

### CAD Pipeline Dependencies (`requirements_aria_os.txt`)

```
cadquery==2.7.0
cadquery-ocp==7.8.1.1.post1
numpy==2.4.3
rich==14.3.3
anthropic>=0.39.0
pandas==3.0.1
trimesh>=4.0.0
requests>=2.31.0
scipy>=1.11.0
```

### Dashboard Dependencies (`requirements.txt`)

```
pyserial
plotly
firebase-admin    # optional -- only for Firebase session push
```

The dashboard also requires Streamlit (installed via `START_DASHBOARD.bat` or `pip install streamlit`).

### Companion App (`aria-climb/`)

| Technology | Role |
|------------|------|
| React Native / Expo | Cross-platform mobile app (iOS + Android) |
| Firebase | Auth, Firestore (device state, sessions, incidents), Cloud Messaging |
| react-native-ble-plx | BLE communication with ARIA hardware (native build only, not Expo Go) |
| Zustand | State management (authStore, bleStore, sessionStore, alertStore) |
| i18n | Localization: English, German, Spanish, French, Japanese |

### Firmware Toolchain

| Component | Role |
|-----------|------|
| Arduino IDE 2.x + STM32 board package | STM32F411 safety layer firmware |
| Arduino IDE 2.x + ESP32 board package | XIAO ESP32-S3 intelligence layer firmware |
| Edge Impulse | Wake word model training (voice commands) |
| SimpleFOC | Motor control library (VESC UART) |
| ST-Link V2 | STM32 programming/debugging |

### Development Tools

| Tool | Role |
|------|------|
| pytest | Test suite (`tests/`) covering GH scripts, validators, router, spec extractor, API server |
| FastAPI | API server (`aria_os/api_server.py`) for programmatic access |
| ezdxf | Civil engineering DXF generation (AutoCAD module) |
| KiCad scripting | ECAD PCB generation target |
| Blender Python API | Lattice generation (gyroid, voronoi, honeycomb) |
