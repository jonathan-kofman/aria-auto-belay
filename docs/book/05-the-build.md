# The Build

## Setup and First Run

### Prerequisites

- Python 3.10+ (3.11 or 3.12 recommended)
- Git
- An Anthropic API key (recommended) OR Google API key OR Ollama installed locally. The pipeline works with zero API keys using template-only mode.

### Installation

```bash
git clone https://github.com/jonathan-kofman/aria-auto-belay
cd aria-auto-belay

# Create a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install CAD pipeline dependencies
pip install -r requirements_aria_os.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# LLM backends (all optional -- priority: Anthropic > Gemini > Ollama > heuristic)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash          # optional, this is the default

# Ollama (if running locally)
OLLAMA_HOST=http://localhost:11434      # default
OLLAMA_MODEL=deepseek-coder            # default

# Onshape (optional -- for cloud CAD upload)
ONSHAPE_ACCESS_KEY=...
ONSHAPE_SECRET_KEY=...
```

### First Run: Generate a Part

```bash
# Generate a simple bracket (uses template -- no API key needed)
python run_aria_os.py "mounting bracket, 100x60x8mm, 4 bolt holes"

# Generate with full pipeline (FEA + drawing + render + CAM)
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
```

Output appears in:
- `outputs/cad/step/<part_id>.step` -- STEP file (import into any CAD software)
- `outputs/cad/stl/<part_id>.stl` -- STL mesh
- `outputs/cad/meta/<part_id>.json` -- version metadata (goal, params, CEM SF, git SHA)
- `outputs/drawings/<part_id>.svg` -- GD&T engineering drawing (if `--full` or `--draw`)
- `outputs/cam/<part_id>/` -- CNC toolpath script + setup sheet (if `--full` or `--cam`)

### Common Operations

**List all generated parts with status:**
```bash
python run_aria_os.py --list
```

**Batch generation from a parts list:**
```bash
python batch.py parts/clock_parts.json
python batch.py parts/clock_parts.json --skip-existing --render --workers 4
```

**Assembly from JSON config:**
```bash
python assemble.py assembly_configs/aria_clutch_assembly.json
```

**Generate from a photo:**
```bash
python run_aria_os.py --image photo.jpg "it's a bracket"
```

**3D preview before export:**
```bash
python run_aria_os.py --preview "ARIA ratchet ring, 213mm OD"
```

**Civil engineering DXF:**
```bash
python run_aria_os.py --autocad "drainage plan" --state TX --discipline drainage
```

**ECAD PCB generation:**
```bash
python run_aria_os.py --ecad "ESP32 sensor board, 80x60mm, 12V, UART, BLE, HX711"
```

### Running the Dashboard

```bash
# Windows (one-click -- sets up local Python automatically)
scripts\START_DASHBOARD.bat

# Manual
pip install -r requirements.txt
pip install streamlit
streamlit run aria_dashboard.py
```

The dashboard provides: CEM parameter tuning, design history viewer, state machine simulation, materials library, certification package generator, and drop-test protocol tools.

### Running the Companion App

```bash
cd aria-climb
npm install --legacy-peer-deps

# Add Firebase config
# Copy google-services.json to aria-climb/android/app/

# Development build (required for BLE)
npx expo run:android

# JS-only preview (no BLE, no native features)
npx expo start
```

### Running Tests

```bash
# Full test suite
python -m pytest tests/ -q

# Individual test modules
python -m pytest tests/test_cad_router.py -q          # 14 template smoke tests
python -m pytest tests/test_spec_extractor.py -q       # 40 spec extraction tests
python -m pytest tests/test_post_gen_validator.py -q    # validation loop tests
python -m pytest tests/test_api_server.py -q            # FastAPI endpoint tests

# Physics and state machine
python aria_models/static_tests.py
python tools/aria_test_harness.py
```

### API Server

```bash
pip install uvicorn fastapi
uvicorn aria_os.api_server:app

# POST /api/generate  -- generate a part
# GET  /api/health     -- backend status
# GET  /api/runs       -- recent generation log
```
