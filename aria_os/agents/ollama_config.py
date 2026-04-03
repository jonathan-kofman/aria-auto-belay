"""Per-agent Ollama model configuration."""
from __future__ import annotations

import os

# Models per agent role. Override via env vars:
#   ARIA_AGENT_DESIGNER_MODEL=qwen2.5-coder:32b
#   ARIA_AGENT_SPEC_MODEL=llama3.1:8b
#   ARIA_AGENT_MODEL=gemma4:31b  (use Gemma 4 for all agents)

# Single model for all agents to avoid VRAM context-switching crashes.
# On 12-16GB VRAM, loading multiple models causes HTTP 500 errors.
# qwen2.5-coder:14b is the best single model for both code gen AND reasoning.
# Override per-agent via env vars if you have 24GB+ VRAM.
_DEFAULT_MODEL = os.environ.get("ARIA_AGENT_MODEL", "qwen2.5-coder:7b")

# Gemma 4 31B (Apache 2.0) — strong local model for code gen + reasoning.
# Competitive with much larger models on coding benchmarks.
# Supports function calling + structured JSON output.
# Install: ollama pull gemma4:31b
# Override model tag: GEMMA_MODEL=gemma4:latest
_GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma4:31b")

AGENT_MODELS: dict[str, str] = {
    "spec":     os.environ.get("ARIA_AGENT_SPEC_MODEL",     _DEFAULT_MODEL),
    "designer": os.environ.get("ARIA_AGENT_DESIGNER_MODEL", _DEFAULT_MODEL),
    "eval":     os.environ.get("ARIA_AGENT_EVAL_MODEL",     _DEFAULT_MODEL),
    "refiner":  os.environ.get("ARIA_AGENT_REFINER_MODEL",  _DEFAULT_MODEL),
}

# Per-domain designer model overrides (all use same model to avoid swapping)
DESIGNER_MODELS: dict[str, str] = {
    "cad":      os.environ.get("ARIA_AGENT_DESIGNER_MODEL", _DEFAULT_MODEL),
    "cam":      os.environ.get("ARIA_AGENT_DESIGNER_MODEL", _DEFAULT_MODEL),
    "ecad":     os.environ.get("ARIA_AGENT_DESIGNER_MODEL", _DEFAULT_MODEL),
    "civil":    _DEFAULT_MODEL,
    "drawing":  _DEFAULT_MODEL,
    "assembly": _DEFAULT_MODEL,
    "dfm":      os.environ.get("ARIA_AGENT_DFM_MODEL",      _DEFAULT_MODEL),
}

# Gemma 4 model configurations per agent role.
# When Gemma 4 is available in Ollama, it is preferred over the default
# qwen2.5-coder:7b for most tasks due to its larger parameter count (31B).
# The designer agent uses Gemma 4 as a fallback between cloud LLMs and
# template generation (see designer_agent.py _call_llm).
GEMMA_MODELS: dict[str, str] = {
    "spec":     _GEMMA_MODEL,   # spec extraction, structured output
    "designer": _GEMMA_MODEL,   # CadQuery code generation (31B >> 7B quality)
    "eval":     _GEMMA_MODEL,   # geometry validation reasoning
    "refiner":  _GEMMA_MODEL,   # code fix suggestions
}

# Context window limits per agent (tokens, estimated as words * 1.3)
# Gemma 4 supports 128k context — designer limit can be raised when using it.
CONTEXT_LIMITS: dict[str, int] = {
    "spec":     4000,
    "designer": 8000,
    "eval":     3000,
    "refiner":  4000,
}

# Ollama connection
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "600"))  # 10 min for 14b model
