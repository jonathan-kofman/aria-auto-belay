[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Map](./03-the-map.md) | [Next: The Build -->](./05-the-build.md)

---

# The Foundation

## Tech Stack Decisions

| Layer | We Chose | Over | Because |
|---|---|---|---|
| **CAD kernel** | CadQuery 2.7 (OpenCascade) | FreeCAD, OpenSCAD | Headless Python API, STEP+STL export, solid boolean ops, runs on any OS without GUI |
| **Primary LLM** | Anthropic Claude (Sonnet) | GPT-4o, Gemini Pro | Best CadQuery code generation quality, structured output, lowest hallucination rate for geometry |
| **Fast LLM** | Google Gemini 2.0 Flash | GPT-4o-mini | Free tier generous, fast inference, good code quality, vision API for verification |
| **Local LLM** | Gemma 4 31B via Ollama | DeepSeek Coder 33B, CodeLlama | Apache 2.0 license, strong code gen at 31B params, runs on T4 GPU (free Lightning AI tier) |
| **Small local LLM** | Qwen 2.5 Coder 7B | CodeLlama 7B | Better code quality at 7B, used for non-code tasks (spec extraction, routing) |
| **Text-to-CAD** | Zoo.dev (KittyCAD) | N/A | ML-native STEP generation, $10/month free tier, complements template+LLM approach |
| **Cloud CAD** | Onshape (REST API) | Fusion 360 API | REST-based (no desktop app needed), free edu/startup plan, parametric features via API |
| **Vision verification** | Gemini 2.5 Flash | Claude Vision, GPT-4V | Cheapest per-image cost, fast inference, adequate accuracy for feature checklist |
| **Web framework** | FastAPI | Flask, Django | Async support, Pydantic validation, auto-generated OpenAPI docs |
| **Dashboard** | Streamlit | React, Gradio | Rapid prototyping, built-in plotting, minimal frontend code for internal tool |
| **ECAD** | KiCad (via pcbnew API) | Eagle, Altium | Open-source, scriptable Python API, widely adopted |
| **Civil CAD** | ezdxf | AutoCAD SDK | Pure Python, no AutoCAD license needed, DXF read/write |
| **3D preview** | Three.js (embedded HTML) | VTK, OpenGL | Zero-install browser preview, STL viewer, works headless |

---

## Core Dependencies

### ARIA-OS Pipeline (`requirements_aria_os.txt`)

| Package | Version | Purpose |
|---|---|---|
| `cadquery` | 2.7.0 | CAD kernel: solid modeling, STEP/STL export |
| `anthropic` | >=0.39.0 | Claude API client |
| `google-genai` | latest | Gemini API client (new SDK) |
| `trimesh` | latest | STL mesh analysis, bore detection, repair |
| `matplotlib` | latest | Headless rendering for visual verification |
| `fastapi` | latest | REST API server |
| `uvicorn` | latest | ASGI server for FastAPI |
| `ezdxf` | latest | DXF file generation for civil engineering |
| `kittycad` | latest | Zoo.dev text-to-STEP SDK (optional) |
| `streamlit` | latest | Dashboard UI |

### Optional Dependencies

| Package | Purpose | Required For |
|---|---|---|
| `kittycad` | Zoo.dev API | `zoo_bridge.py` text-to-STEP |
| `google-generativeai` | Legacy Gemini SDK | Fallback if `google-genai` not installed |
| `Pillow` | Image handling | Legacy Gemini vision path |
| `ollama` | Not needed | Ollama uses raw HTTP, no Python SDK required |

---

## Infrastructure

### LLM Priority Chain

ARIA-OS never crashes due to a missing API key. The fallback chain degrades gracefully:

```
Code Generation Tasks (call_llm):
  1. Anthropic Claude    -- ANTHROPIC_API_KEY (best code quality)
  2. Google Gemini       -- GOOGLE_API_KEY (fast, good code gen)
  3. Gemma 4 31B         -- Ollama local (free, strong at 31B)
  4. Ollama default      -- Any pulled model (fallback)
  5. None                -- Caller falls back to templates/heuristics

Non-Code Tasks (call_llm_local_first):
  1. Gemma 4 31B         -- Ollama local (free, fast reasoning)
  2. Google Gemini       -- Conserves Anthropic quota
  3. Anthropic Claude    -- Last resort for non-code tasks
  4. Ollama default      -- Fallback
  5. None
```

> **Tip:** For code generation (DesignerAgent), the 7B default Ollama model is explicitly skipped --- it produces broken CadQuery geometry too often. Only Gemma 4 31B or cloud models are used for geometry code.

### Lightning AI Integration

Gemma 4 31B requires a GPU. For developers without local GPU hardware, ARIA-OS integrates with Lightning AI:

- 22 free GPU hours/month on T4 instances
- SSH tunnel auto-reconnects if dropped (`.lightning_session` file)
- Ollama runs on the remote GPU, tunnel maps `localhost:11435`
- `_ensure_lightning_tunnel()` in `llm_client.py` handles reconnection

### Onshape Authentication

Onshape uses API key authentication (not OAuth):

1. Generate keys at `https://cad.onshape.com/appstore/dev-portal`
2. Set `ONSHAPE_ACCESS_KEY` and `ONSHAPE_SECRET_KEY` in `.env`
3. The bridge uses Basic auth over HTTPS

---

## Design Principles

### 1. Templates First, LLM Second

The most important architectural decision: known part types use deterministic CadQuery templates. LLMs are only used when no template matches or when the goal requires advanced operations (sweep, loft, fillet, shell).

This gives 100% reliability for common parts and LLM flexibility for novel geometry.

### 2. Never Crash on Missing Backend

Every external service call is wrapped in try/except. Missing API keys, network failures, and model errors all degrade gracefully. The pipeline always produces the best output it can with the backends available.

### 3. Validation Before Export

No STEP file is exported without validation. At minimum: bbox check, STEP readability (solid count >= 1). With full pipeline: dimensional accuracy, mesh integrity, bore detection, visual verification.

### 4. Parallel Where Possible

Phase 1 (4 research queries) and Phase 4 (7 manufacturing outputs) run in parallel via `asyncio.gather`. Each task has a 90-second timeout to prevent one slow backend from blocking the pipeline.

### 5. Failure Context Injection

When generation fails, the failure message is injected into the next iteration's LLM prompt. The RefinerAgent analyzes the error and produces specific parameter overrides. This is more effective than blind retry.

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | No | (none) | Anthropic Claude API access |
| `GOOGLE_API_KEY` | No | (none) | Google Gemini API access |
| `ZOO_API_TOKEN` | No | (none) | Zoo.dev text-to-STEP API |
| `ONSHAPE_ACCESS_KEY` | No | (none) | Onshape REST API |
| `ONSHAPE_SECRET_KEY` | No | (none) | Onshape REST API |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Override Gemini model name |
| `GEMMA_MODEL` | No | `gemma4:31b` | Override Gemma model for Ollama |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `qwen2.5-coder:7b` | Default Ollama model |

All variables can be set in a `.env` file at the repository root. The `llm_client.py` module reads both `os.environ` and `.env` with a consistent fallback pattern.

> **Warning:** Never commit `.env` to version control. It contains API keys.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Map](./03-the-map.md) | [Next: The Build -->](./05-the-build.md)
