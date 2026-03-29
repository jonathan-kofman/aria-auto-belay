"""
fetch_component.py — Resolve a standard component to a STEP file.

Looks up a component key in components/registry.json, generates the STEP via
the matching CadQuery template, and caches it to components/cache/.

Usage:
    python fetch_component.py nema17
    python fetch_component.py mgn12_400
    python fetch_component.py bearing_6200
    python fetch_component.py --list              (show all registered components)
    python fetch_component.py --list motors       (filter by keyword)
    python fetch_component.py nema17 --params '{"length_mm": 60}'   (param override)
    python fetch_component.py nema17 --force      (regenerate even if cached)

Outputs:
    STEP: components/cache/<key>.step
    STL:  components/cache/<key>.stl

The returned STEP path can be used directly in assembly JSON configs:
    {"id": "j1_motor", "step": "component:nema17", "pos": [0, 0, 0], "rot": [0, 0, 0]}
"""
import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "cad-pipeline" / "components" / "registry.json"
CACHE_DIR     = ROOT / "cad-pipeline" / "components" / "cache"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        print(f"[fetch] Error: registry not found at {REGISTRY_PATH}")
        sys.exit(1)
    with open(REGISTRY_PATH, "r", encoding="utf-8") as fh:
        reg = json.load(fh)
    # Strip meta keys
    return {k: v for k, v in reg.items() if not k.startswith("_")}


def fetch(
    key: str,
    param_overrides: dict | None = None,
    force: bool = False,
) -> Path:
    """
    Resolve component key → STEP path.
    Generates if not cached or force=True.
    Returns the STEP path.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    registry = load_registry()

    if key not in registry:
        # Fuzzy match suggestion
        matches = [k for k in registry if key.lower() in k.lower()]
        msg = f"[fetch] Unknown component key: '{key}'"
        if matches:
            msg += f"\n        Did you mean: {', '.join(matches[:5])}"
        print(msg)
        sys.exit(1)

    entry = registry[key]
    template = entry["template"]
    params   = dict(entry.get("params", {}))
    if param_overrides:
        params.update(param_overrides)

    step_path = CACHE_DIR / f"{key}.step"
    stl_path  = CACHE_DIR / f"{key}.stl"

    if step_path.exists() and not force:
        sz = step_path.stat().st_size
        print(f"[fetch] Cached: {step_path}  ({sz // 1024} KB)")
        return step_path

    print(f"[fetch] Generating '{key}': {entry.get('description', template)}")

    try:
        from aria_os.cadquery_generator import write_cadquery_artifacts
    except ImportError as e:
        print(f"[fetch] Error importing cadquery_generator: {e}")
        sys.exit(1)

    plan = {"part_id": template, "params": params}
    result = write_cadquery_artifacts(
        plan,
        goal=entry.get("description", key),
        step_path=str(step_path),
        stl_path=str(stl_path),
        repo_root=ROOT,
    )

    if result.get("error"):
        print(f"[fetch] FAILED: {result['error']}")
        sys.exit(1)

    bbox = result.get("bbox", {})
    print(f"[fetch] OK  {step_path.name}  "
          f"bbox={bbox.get('x','?')}×{bbox.get('y','?')}×{bbox.get('z','?')} mm")
    return step_path


def cmd_list(filter_kw: str | None = None) -> None:
    registry = load_registry()
    rows = list(registry.items())
    if filter_kw:
        filt = filter_kw.lower()
        rows = [(k, v) for k, v in rows if filt in k.lower() or filt in v.get("description","").lower()]

    if not rows:
        print(f"[fetch] No components matching '{filter_kw}'")
        return

    col_k = max(len(k) for k, _ in rows) + 2
    col_t = 24
    print(f"\n{'Key':{col_k}}  {'Template':{col_t}}  Description")
    print("-" * (col_k + col_t + 50))
    for key, entry in rows:
        cached = " [cached]" if (CACHE_DIR / f"{key}.step").exists() else ""
        print(f"{key:{col_k}}  {entry['template']:{col_t}}  "
              f"{entry.get('description','')}{cached}")
    print(f"\n{len(rows)} component(s) registered.  "
          f"Cache: {CACHE_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch/generate a standard mechanical component as STEP+STL."
    )
    parser.add_argument(
        "key",
        nargs="?",
        default=None,
        help="Component registry key (e.g. nema17, mgn12_400, bearing_6200)",
    )
    parser.add_argument(
        "--list",
        nargs="?",
        const="",
        metavar="FILTER",
        help="List registered components (optionally filter by keyword)",
    )
    parser.add_argument(
        "--params",
        default=None,
        metavar="JSON",
        help='JSON string of param overrides, e.g. \'{"length_mm": 60}\'',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if STEP is already cached",
    )
    args = parser.parse_args()

    if args.list is not None:
        cmd_list(args.list or None)
        return

    if not args.key:
        parser.print_help()
        sys.exit(0)

    overrides = None
    if args.params:
        try:
            overrides = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"[fetch] Bad --params JSON: {e}")
            sys.exit(1)

    step = fetch(args.key, param_overrides=overrides, force=args.force)
    print(f"\nSTEP: {step}")
    stl = step.with_suffix(".stl")
    if stl.exists():
        print(f"STL:  {stl}")


if __name__ == "__main__":
    main()
