[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Build](./05-the-build.md) | [Next: Gotchas -->](./07-gotchas.md)

---

# Integrations

## Overview

ARIA-OS integrates with 6 external services. All are optional --- the pipeline degrades gracefully without any of them.

| Service | Purpose | Cost | Module |
|---|---|---|---|
| **Anthropic Claude** | Best-quality CadQuery code generation | ~$3/1M tokens | `llm_client.py` |
| **Google Gemini** | Fast code gen + vision verification | Free tier generous | `llm_client.py`, `visual_verifier.py` |
| **Zoo.dev (KittyCAD)** | ML-native text-to-STEP | $10/month free (~50 parts) | `zoo_bridge.py` |
| **Onshape** | Live parametric models, BOM, drawings | Free edu/startup | `agents/onshape_bridge.py` |
| **Lightning AI** | Free GPU for Gemma 4 (Ollama) | 22 hrs/month free (T4) | `llm_client.py` |
| **MillForge** | CNC quoting + ordering | Per-quote | `agents/coordinator.py` Phase 5 |

---

## Anthropic Claude

### What It Does

Claude generates CadQuery Python code from natural language descriptions. It is the highest-quality code generation backend in the pipeline.

### How It Works

```
DesignerAgent._call_llm(prompt)
  -> llm_client._try_anthropic(prompt, system_prompt)
    -> anthropic.Anthropic(api_key=...).messages.create(
         model="claude-sonnet-4-6",
         max_tokens=4096,
         temperature=0,
         messages=[{role: "user", content: prompt}],
         system=system_prompt
       )
```

The system prompt includes:
- CadQuery operations reference (goal-specific subset of 25 operations)
- Reference template code (closest matching template to the requested part)
- CEM physics parameters (if applicable)
- Previous failure context (on retry iterations)

### Configuration

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Fallback Behavior

Models tried in order: `claude-sonnet-4-6`, then `claude-3-5-sonnet-20241022`. Retries up to 3 times on overload (529) with exponential backoff (5s, 10s, 20s).

---

## Google Gemini

### What It Does

Gemini serves two roles:
1. **Code generation** --- fast LLM fallback after Anthropic
2. **Visual verification** --- renders 3 views of the part, sends images to Gemini vision, gets feature-level PASS/FAIL

### Visual Verification Flow

```
visual_verifier.verify_visual(step_path, stl_path, goal, spec)
  |
  v
1. Render 3 views (top XY, front XZ, isometric 3D) via matplotlib
  |
  v
2. Build feature checklist from goal keywords + spec
   e.g. "center bore (~30mm) visible", "4 bolt holes visible in circular pattern"
  |
  v
3. Send images + checklist to Gemini 2.5 Flash
  |
  v
4. Parse JSON response: { checks: [{feature, found, notes}], overall_match, confidence }
  |
  v
5. Return: { verified: true, confidence: 0.92, checks: [...], issues: [] }
```

### Configuration

```
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash    # override default
```

### Fallback Models

Code generation: `gemini-2.0-flash` -> `gemini-2.0-flash-lite` -> `gemini-2.5-flash`
Visual verification: `gemini-2.5-flash` -> configured model -> `gemini-2.0-flash`

Both support the new `google-genai` SDK and fall back to the legacy `google-generativeai` SDK.

---

## Zoo.dev (KittyCAD)

### What It Does

Zoo.dev provides ML-native text-to-STEP generation. Unlike the LLM path (which generates CadQuery code that is then executed), Zoo.dev generates STEP geometry directly from the ML model.

### How It Works

```
zoo_bridge.generate_step_from_zoo(goal, output_dir, timeout=120)
  -> kittycad.Client(api_key=token).text_to_cad(goal)
  -> Polls for completion (up to 120s)
  -> Downloads STEP file to output_dir
  -> Returns { step_path, status, ... }
```

### Position in the Fallback Chain

```
1. Template match?         -> use template (instant, 100% reliable)
2. Zoo.dev available?      -> text-to-STEP API (30-120s, black-box geometry)
3. Anthropic Claude?       -> LLM generates CadQuery code
4. Gemini Flash?           -> LLM generates CadQuery code
5. Gemma 4 31B?            -> local LLM generates CadQuery code
6. Deterministic fallback  -> error or simplified geometry
```

### Configuration

```
ZOO_API_TOKEN=zoo-...
```

### Limitations

- Free tier: $10/month credit, roughly 50 parts
- Black-box geometry: no control over construction approach
- No dimensional verification built into the API
- ARIA-OS validates the output STEP the same way it validates LLM-generated STEP

---

## Onshape

### What It Does

After generating a STEP file locally, ARIA-OS uploads it to Onshape as a live parametric model. The user gets a URL to an editable part in their Onshape workspace.

### Integration Flow

```
OnshapeBridge.create_part(name, spec, goal, step_path)
  |
  v
1. Create new Document in Onshape
  |
  v
2. Upload STEP file as a blob
  |
  v
3. Translate STEP -> Onshape Part Studio
  |
  v
4. Wait for translation to complete
  |
  v
5. Read back:
   - Part metadata (mass, volume, surface area)
   - BOM (bill of materials)
   - Mass properties
  |
  v
6. Create Drawing element linked to the Part Studio
  |
  v
7. Return Onshape document URL
```

### Configuration

```
ONSHAPE_ACCESS_KEY=...
ONSHAPE_SECRET_KEY=...
```

Generate keys at: `https://cad.onshape.com/appstore/dev-portal`

> **Tip:** Onshape offers free plans for education and open-source projects. The ARIA-OS integration works with any plan tier.

### What You Get in Onshape

- Live parametric part (editable features, history tree)
- Automatic drawing with views
- BOM metadata attached to the document
- Mass properties computed from the imported geometry

---

## Lightning AI (Ollama Remote GPU)

### What It Does

Provides free T4 GPU hours for running Gemma 4 31B via Ollama. Developers without a local GPU can use this to get local-quality LLM inference at zero cost.

### How It Works

1. Start a Lightning AI Studio session (T4 GPU, 22 free hrs/month)
2. Install Ollama on the remote instance, pull `gemma4:31b`
3. The session ID is saved to `.lightning_session`
4. SSH tunnel maps remote `localhost:11434` to local `localhost:11435`
5. `OLLAMA_HOST=http://localhost:11435` routes Ollama calls through the tunnel

### Auto-Reconnection

`_ensure_lightning_tunnel()` in `llm_client.py`:
- Checks if the tunnel is alive by hitting `/api/tags`
- If dead, reads `.lightning_session` file
- Re-establishes SSH tunnel with the stored session ID
- Verifies connectivity after reconnection

### Configuration

```
OLLAMA_HOST=http://localhost:11435    # Remote tunnel port
GEMMA_MODEL=gemma4:31b
```

Plus `.lightning_session` file and `~/.ssh/lightning_rsa` key.

---

## MillForge

### What It Does

MillForge is a CNC manufacturing bridge for instant quoting and ordering. Phase 5 of the coordinator creates a MillForge job when the feature flag is enabled.

### Current Status

The MillForge bridge is implemented but behind a feature flag (`MILLFORGE_BRIDGE` in `agents/features.py`). The bridge creates a job JSON with:
- STEP file path
- Material specification
- DFM report (from Phase 4)
- Cost estimate (from QuoteAgent)
- Setup sheet (from cam_setup.py)

### Configuration

Feature flag must be enabled. Specific MillForge API credentials TBD.

---

## Integration Availability Matrix

| Integration | No API Key | Free Tier | Paid |
|---|---|---|---|
| Template generation | Full | Full | Full |
| Zoo.dev text-to-STEP | Unavailable | ~50 parts/month | Unlimited |
| Claude code gen | Unavailable | N/A | Per-token |
| Gemini code gen + vision | Unavailable | Generous | Per-token |
| Gemma 4 (local GPU) | Full (if GPU) | Via Lightning AI | N/A |
| Gemma 4 (no GPU) | Unavailable | Via Lightning AI | N/A |
| Ollama 7B | Full (if Ollama) | Full | N/A |
| Onshape | Unavailable | Full (edu/open-source) | Full |
| MillForge | Unavailable | TBD | Per-job |

> **Tip:** The recommended zero-cost setup is: `GOOGLE_API_KEY` (free Gemini tier) + Ollama with `qwen2.5-coder:7b` (local). This gives you template generation, Gemini code gen fallback, visual verification, and local spec extraction.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Build](./05-the-build.md) | [Next: Gotchas -->](./07-gotchas.md)
