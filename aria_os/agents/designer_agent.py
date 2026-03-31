"""DesignerAgent — generates domain-specific code (CadQuery, CAM, ECAD, etc.)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .base_agent import BaseAgent
from .design_state import DesignState
from .domains import DESIGNER_PROMPTS
from .ollama_config import DESIGNER_MODELS, CONTEXT_LIMITS


class DesignerAgent(BaseAgent):
    """Generates code for the target domain using Ollama."""

    def __init__(self, domain: str, repo_root: Path, tools: dict | None = None):
        self.domain = domain
        self.repo_root = repo_root
        super().__init__(
            name=f"DesignerAgent[{domain}]",
            system_prompt=DESIGNER_PROMPTS.get(domain, DESIGNER_PROMPTS["cad"]),
            model=DESIGNER_MODELS.get(domain, "qwen2.5-coder:14b"),
            tools=tools or {},
            max_context_tokens=CONTEXT_LIMITS["designer"],
            fallback_to_cloud=True,  # designer is the most critical agent
        )

    def generate(self, state: DesignState) -> None:
        """Generate code and populate state.code, state.output_path, state.bbox.

        Strategy:
        1. Check if a CadQuery template exists for this part type — if so, use it
           directly with the agent-extracted params (instant, reliable).
        2. If no template or template output fails eval, fall back to LLM generation.
        The agent is still agentic: SpecAgent extracts params, EvalAgent validates.
        """
        if self.domain == "cad":
            # Try template-based generation first (fast path)
            template_used = self._try_template(state)
            if template_used:
                return

        # LLM-based generation
        # Build the user prompt from state
        prompt_parts = [
            f"## Design Request\n{state.goal}\n",
            f"## Specifications\n{json.dumps(state.spec, indent=2, default=str)}\n",
        ]

        # Include web research context if available
        research = state.plan.get("research_context", "")
        if research:
            prompt_parts.append(
                f"## Reference Information (from web research)\n"
                f"Use these real-world specs and design features as guidance:\n"
                f"{research[:2000]}\n"
            )

        if state.cem_params:
            prompt_parts.append(
                f"## Physics Parameters (CEM)\n{json.dumps(state.cem_params, indent=2, default=str)}\n"
            )

        if state.refinement_instructions:
            prompt_parts.append(
                f"## REFINEMENT FROM PREVIOUS ATTEMPT\n"
                f"The previous attempt had these failures. Fix them:\n"
                f"{state.refinement_instructions}\n"
            )
            if state.parameter_overrides:
                prompt_parts.append(
                    f"## Parameter Overrides\n"
                    f"Apply these specific changes:\n"
                    f"{json.dumps(state.parameter_overrides, indent=2, default=str)}\n"
                )

        prompt = "\n".join(prompt_parts)

        # Call the LLM
        response = self.run(prompt, state)

        if not response:
            state.generation_error = "DesignerAgent returned empty response"
            return

        # Extract code from response (JSON-first, then markdown, then raw)
        code = _extract_code(response)
        if not code:
            state.generation_error = f"No code block found in DesignerAgent response"
            state.code = response  # store raw for debugging
            return

        state.code = code
        state.generation_error = ""

        # For CAD domain: execute the code to produce STEP/STL
        if self.domain == "cad":
            self._execute_cad(state, code)

    def _try_template(self, state: DesignState) -> bool:
        """Try to generate using a CadQuery template with agent-extracted params.
        Returns True if successful (state populated), False to fall back to LLM."""
        try:
            from ..generators.cadquery_generator import _find_template_fn

            # Check if a template matches the part type from spec
            part_type = state.spec.get("part_type", "")
            part_id = state.part_id or ""

            print(f"  [{self.name}] Template check: part_id='{part_id}', part_type='{part_type}'")

            # Try part_type first (more specific), then part_id
            template_fn = _find_template_fn(part_type) or _find_template_fn(part_id)
            if not template_fn:
                return False

            # Generate code using the template with agent-extracted params
            code = template_fn(state.spec)
            if not code or len(code) < 50:
                return False

            print(f"  [{self.name}] Using template for '{part_type or part_id}' with agent params")

            state.code = code
            state.generation_error = ""
            self._execute_cad(state, code)

            # Check if execution succeeded
            if state.generation_error:
                print(f"  [{self.name}] Template execution failed: {state.generation_error}")
                state.generation_error = ""  # clear for LLM retry
                return False

            return True

        except Exception as exc:
            print(f"  [{self.name}] Template lookup failed: {exc}")
            return False

    def _execute_cad(self, state: DesignState, code: str) -> None:
        """Execute CadQuery code and capture output files + bbox."""
        from ..exporter import get_output_paths

        paths = get_output_paths(state.part_id or state.goal, self.repo_root)
        step_path = paths["step_path"]
        stl_path = paths["stl_path"]

        # Add export footer to code
        export_code = code + f"""

# === AUTO-GENERATED EXPORT ===
import os as _os
from cadquery import exporters as _exp
_step = r"{step_path}"
_stl  = r"{stl_path}"
try:
    _os.makedirs(_os.path.dirname(_step), exist_ok=True)
except OSError:
    pass
try:
    _os.makedirs(_os.path.dirname(_stl), exist_ok=True)
except OSError:
    pass
_exp.export(result, _step, _exp.ExportTypes.STEP)
_exp.export(result, _stl,  _exp.ExportTypes.STL)
"""

        # Execute in sandbox (permissive — code needs import, os, Path)
        import cadquery as cq
        import math
        import os as _os_mod
        ns: dict[str, Any] = {
            "cq": cq,
            "math": math,
            "os": _os_mod,
            "Path": Path,
            "__builtins__": __builtins__,
        }

        try:
            exec(compile(export_code, f"<{state.part_id}_agent>", "exec"), ns)

            # Capture bbox from the result object
            result_obj = ns.get("result")
            if result_obj is not None:
                bb = result_obj.val().BoundingBox()
                state.bbox = {"x": round(bb.xlen, 3), "y": round(bb.ylen, 3),
                              "z": round(bb.zlen, 3)}

            state.output_path = step_path
            state.artifacts = {"step_path": step_path, "stl_path": stl_path}
            print(f"  [{self.name}] Generated STEP ({Path(step_path).stat().st_size // 1024}KB) "
                  f"bbox: {state.bbox}")

        except Exception as exc:
            state.generation_error = str(exc)[:500]
            print(f"  [{self.name}] Execution failed: {state.generation_error}")


def _extract_code(response: str) -> str:
    """
    Extract Python code from LLM response.

    Tries in order (AutoBE-style structured output first for highest reliability):
    1. JSON with "code" key (structured output from JSON mode)
    2. JSON embedded in text
    3. Markdown code fences
    4. Raw code (starts with import/from/#)
    """
    # 1. Try JSON structured output first (highest reliability — AutoBE pattern)
    try:
        parsed = json.loads(response.strip())
        if isinstance(parsed, dict) and "code" in parsed:
            code = parsed["code"].strip()
            if code:
                return code
    except (ValueError, json.JSONDecodeError):
        pass

    # 2. Try extracting JSON object from within the response text
    json_match = re.search(r'\{[^{}]*"code"\s*:\s*"((?:[^"\\]|\\.)*)"\s*[^{}]*\}', response, re.DOTALL)
    if json_match:
        code = json_match.group(1)
        # Unescape JSON string
        code = code.replace("\\n", "\n").replace("\\\\", "\\").replace('\\"', '"').replace("\\t", "\t")
        if "import" in code or "cq." in code:
            return code.strip()

    # 3. Try markdown code fence
    match = re.search(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 4. If response starts with import or comment, treat whole thing as code
    stripped = response.strip()
    if stripped.startswith(("import ", "from ", "#", "import\n")):
        return stripped

    # 5. Look for first line that starts with import
    lines = stripped.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith(("import ", "from ")):
            return "\n".join(lines[i:])

    return ""
