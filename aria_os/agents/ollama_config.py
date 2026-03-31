"""Per-agent Ollama model configuration."""
from __future__ import annotations

import os

# Models per agent role. Override via env vars:
#   ARIA_AGENT_DESIGNER_MODEL=qwen2.5-coder:32b
#   ARIA_AGENT_SPEC_MODEL=llama3.1:8b

# llama3.1:8b for reasoning (spec, refiner, domain routing)
# qwen2.5-coder:14b for code generation (designer — best quality)
# qwen2.5-coder:7b for eval (lightweight)
AGENT_MODELS: dict[str, str] = {
    "spec":     os.environ.get("ARIA_AGENT_SPEC_MODEL",     "llama3.1:8b"),
    "designer": os.environ.get("ARIA_AGENT_DESIGNER_MODEL", "qwen2.5-coder:14b"),
    "eval":     os.environ.get("ARIA_AGENT_EVAL_MODEL",     "qwen2.5-coder:7b"),
    "refiner":  os.environ.get("ARIA_AGENT_REFINER_MODEL",  "llama3.1:8b"),
}

# Per-domain designer model overrides
DESIGNER_MODELS: dict[str, str] = {
    "cad":      os.environ.get("ARIA_AGENT_DESIGNER_MODEL", "qwen2.5-coder:14b"),
    "cam":      os.environ.get("ARIA_AGENT_DESIGNER_MODEL", "qwen2.5-coder:14b"),
    "ecad":     os.environ.get("ARIA_AGENT_DESIGNER_MODEL", "qwen2.5-coder:14b"),
    "civil":    "qwen2.5-coder:7b",
    "drawing":  "qwen2.5-coder:7b",
    "assembly": "llama3.1:8b",
    "dfm":      os.environ.get("ARIA_AGENT_DFM_MODEL", "llama3.1:8b"),
}

# Context window limits per agent (tokens, estimated as words * 1.3)
CONTEXT_LIMITS: dict[str, int] = {
    "spec":     4000,
    "designer": 8000,
    "eval":     3000,
    "refiner":  4000,
}

# Ollama connection
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
