# Operations

## How to Maintain and Extend ARIA-OS

### Adding a New CadQuery Template

Every template follows the same pattern. Here is the process:

**1. Write the template function** in `aria_os/generators/cadquery_generator.py`:

```python
def _cq_your_part(params: dict[str, Any]) -> str:
    # Extract dimensions with defaults
    width  = float(params.get("width_mm", 100.0))
    height = float(params.get("height_mm", 50.0))
    thick  = float(params.get("thickness_mm", 8.0))

    return f"""
import cadquery as cq

result = (
    cq.Workplane("XY")
    .rect({width}, {height})
    .extrude({thick})
)

bb = result.val().BoundingBox()
print(f"BBOX:{{bb.xlen:.1f}},{{bb.ylen:.1f}},{{bb.zlen:.1f}}")
cq.exporters.export(result, str(step_path))
cq.exporters.export(result, str(stl_path), exportType="STL")
"""
```

Rules:
- Always print `BBOX:x,y,z` for validation
- Build solid first, then cut features
- No fillets on first attempt
- Select faces by direction (`faces(">Z")`), never by index
- All geometry constants from `context/aria_mechanical.md` for ARIA parts

**2. Register in `_CQ_TEMPLATE_MAP`** (around line 2637):

```python
_CQ_TEMPLATE_MAP: dict[str, Any] = {
    # ... existing entries ...
    "your_part":       _cq_your_part,
    "your_part_alias": _cq_your_part,  # add common aliases
}
```

**3. Add keyword aliases** to `_KEYWORD_TO_TEMPLATE` (around line 2857):

```python
(["your_part", "your_alias", "your keyword"], _cq_your_part),
```

**4. Add part_type detection** in `aria_os/spec_extractor.py` (`_PART_TYPE_KEYWORDS` list):

```python
("your part",   "your_part"),
("your alias",  "your_part"),
```

**5. Write tests** in `tests/test_cad_router.py` to confirm routing and in `tests/test_spec_extractor.py` to confirm spec parsing.

### Adding a New CEM Physics Domain

The CEM system maps goal keywords to physics modules. To add a new domain:

**1. Create the module** at `cem/cem_<domain>.py`:

```python
"""CEM module for <domain>."""
from cem.cem_core import Material

def compute_for_goal(goal: str, params: dict) -> dict:
    """Entry point called by the orchestrator."""
    # Run physics calculations
    # Return dict with SF values, geometry params, warnings
    return {
        "safety_factors": {"primary_check": 3.5},
        "geometry": {"od_mm": 100, "height_mm": 50},
        "warnings": [],
    }
```

**2. Register in `cem/cem_registry.py`**:

```python
_CEM_MODULES = {
    "aria":    ("cem.cem_aria", ["aria", "belay", "clutch"]),
    "lre":     ("cem.cem_lre",  ["nozzle", "rocket", "lre", "turbopump"]),
    "your_domain": ("cem.cem_your_domain", ["keyword1", "keyword2"]),
}
```

**3. Add geometry generation** (optional) in `cem/cem_to_geometry.py`:

```python
def _your_part_script(params: dict) -> str:
    """Deterministic CadQuery from CEM scalars. No LLM."""
    # Return CadQuery script string
```

Rule: `cem_to_geometry.py` must NEVER call an LLM. Deterministic only.

### Adding New Spec Extraction Patterns

`aria_os/spec_extractor.py` uses regex patterns to parse dimensions from natural language.

**Add a new dimension pattern:**

The function `extract_spec(description)` contains regex blocks for each parameter. To add a new pattern (e.g., "thread pitch"):

1. Add the key to the docstring
2. Add a regex block in the extraction section
3. Add test cases in `tests/test_spec_extractor.py`

**Add a new part_type keyword:**

In the `_PART_TYPE_KEYWORDS` list (sorted longest-first for longest-match-wins):

```python
("your long keyword", "your_part_type"),
("short keyword",     "your_part_type"),
```

**Add a new material keyword:**

In the material detection section, specific grades are checked before generic names:

```python
# Specific grades first
("4140", "steel_4140"),
("inconel", "inconel_718"),
# Generic last
("steel", "steel_generic"),
```

### Tuning the EvalAgent

The `EvalAgent` (`aria_os/agents/eval_agent.py`) runs domain-specific validators. Key thresholds:

| Check | Location | Default | Notes |
|-------|----------|---------|-------|
| Solid count | `_eval_cad` | Must be 1 | Multiple solids = disconnected geometry |
| Bbox tolerance | `geometry_validator.py` | +/- 10% of spec | Adjustable per part type |
| CEM SF minimum | `cem_checks.py` | 2.0 (general), 8.0 (ratchet tooth shear) | Safety-critical parts need higher SF |
| Watertight mesh | `post_gen_validator.py` | Required | Auto-repairs via trimesh fill_holes |
| Visual verification | `visual_verifier.py` | Feature checklist | Threshold is per-feature presence |

The refinement loop (`aria_os/agents/refinement_loop.py`) runs up to 3 iterations of: evaluate -> diagnose failures -> refine code -> re-evaluate. Failure messages from each iteration are injected into the next attempt's prompt.

### Onshape API Key Setup

1. Go to https://cad.onshape.com/appstore/dev-portal
2. Create a new API key pair
3. Add to `.env`:
   ```
   ONSHAPE_ACCESS_KEY=your_access_key
   ONSHAPE_SECRET_KEY=your_secret_key
   ```
4. Test: `python -c "from aria_os.agents.onshape_bridge import OnshapeBridge; b = OnshapeBridge(); print(b.auth.is_configured)"`

### Feature Flags

`aria_os/agents/features.py` defines build profiles that toggle capabilities:

| Flag | dev | demo | production |
|------|-----|------|------------|
| GRASSHOPPER_BACKEND | on | off | on |
| BLENDER_LATTICE | on | off | on |
| MILLFORGE_BRIDGE | off | off | on |
| ONSHAPE_INTEGRATION | on | on | on |
| WEB_SEARCH | on | on | on |
| OLLAMA_AGENTS | on | on | on |
| DEBUG_GEOMETRY | on | off | off |

Set profile via `ARIA_PROFILE=dev` environment variable, or override individual flags with `ARIA_FEATURE_<FLAG>=1`.
