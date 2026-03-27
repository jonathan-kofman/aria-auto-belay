"""
preview.py — generate any ARIA part and open it in Cursor's Simple Browser.

Usage:
    python preview.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
    python preview.py "brake drum 200mm OD, 6061 aluminum"
    python preview.py "spool 600mm diameter, 47mm bore"
    python preview.py "cam collar 55mm OD"
    python preview.py "rope guide 80x50x15mm, 12mm bore"
    python preview.py "catch pawl 60mm length"
    python preview.py "housing 700x680x344mm"
    python preview.py "LRE nozzle 500N thrust"
    python preview.py "bracket 100x50x10mm, 4xM6 bolts"
    python preview.py          # re-opens last generated part
"""
import sys, webbrowser, threading, http.server, os, functools
from pathlib import Path

# ── suppress external browser ────────────────────────────────────────────────
webbrowser.open = lambda u, **k: None

# ── serve %TEMP% so Simple Browser can load the HTML ─────────────────────────
handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                            directory=os.environ["TEMP"])
server  = http.server.HTTPServer(("", 8765), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()

# ── resolve root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent

# ── generate part if a description was given ─────────────────────────────────
desc = " ".join(sys.argv[1:]).strip()

if desc:
    from aria_os.spec_extractor      import extract_spec, merge_spec_into_plan
    from aria_os.multi_cad_router    import CADRouter
    from aria_os.cadquery_generator  import write_cadquery_artifacts

    from aria_os.cadquery_generator import _CQ_TEMPLATE_MAP
    route   = CADRouter.route(desc)
    part_id = route.get("spec", {}).get("part_type") or "custom_part"
    spec    = route.get("spec", {})

    # Resolve to the correct template map key:
    # try bare name first (e.g. "lre_nozzle"), then aria-prefixed (e.g. "aria_ratchet_ring")
    if part_id in _CQ_TEMPLATE_MAP:
        resolved_id = part_id
    elif f"aria_{part_id}" in _CQ_TEMPLATE_MAP:
        resolved_id = f"aria_{part_id}"
    else:
        resolved_id = f"aria_{part_id}"   # unknown — LLM fallback in write_cadquery_artifacts

    plan = {"part_id": resolved_id, "params": spec}

    step_path = ROOT / "outputs" / "cad" / "step" / f"{plan['part_id']}_preview.step"
    stl_path  = ROOT / "outputs" / "cad" / "stl"  / f"{plan['part_id']}_preview.stl"
    step_path.parent.mkdir(parents=True, exist_ok=True)
    stl_path.parent.mkdir(parents=True, exist_ok=True)

    # Always use CadQuery for preview — grasshopper needs Rhino to execute
    print(f"Generating: {plan['part_id']}  (cadquery backend)")
    result = write_cadquery_artifacts(plan, desc, str(step_path), str(stl_path), ROOT)
    if result.get("error"):
        print(f"[ERROR] {result['error']}")
        sys.exit(1)
    stl_file = Path(result["stl_path"])
    html_name = f"aria_preview_{plan['part_id']}.html"
else:
    # re-open last generated file
    stl_files = sorted((ROOT / "outputs" / "cad" / "stl").glob("*_preview.stl"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
    if not stl_files:
        print("No preview STL found. Pass a description, e.g.:")
        print('  python preview.py "ARIA ratchet ring, 213mm OD"')
        sys.exit(1)
    stl_file  = stl_files[0]
    part_id   = stl_file.stem.replace("_preview", "")
    html_name = f"aria_preview_{part_id}.html"
    print(f"Re-opening last part: {part_id}")

# ── show preview ──────────────────────────────────────────────────────────────
show_preview = __import__("aria_os.preview_ui", fromlist=["show_preview"]).show_preview
print(f"\nSimple Browser URL: http://localhost:8765/{html_name}")
choice = show_preview(str(stl_file), part_id=stl_file.stem.replace("_preview", ""))

# ── act on export choice ──────────────────────────────────────────────────────
import shutil
base_name = stl_file.stem.replace("_preview", "")
out_step  = ROOT / "outputs" / "cad" / "step" / f"{base_name}.step"
out_stl   = ROOT / "outputs" / "cad" / "stl"  / f"{base_name}.stl"
src_step  = stl_file.with_suffix(".step").parent.parent / "step" / f"{base_name}_preview.step"

if choice in ("step", "both"):
    if src_step.exists():
        shutil.copy2(src_step, out_step)
        print(f"  STEP → {out_step}")
    else:
        print(f"  [WARN] No STEP source found at {src_step}")

if choice in ("stl", "both"):
    shutil.copy2(stl_file, out_stl)
    print(f"  STL  → {out_stl}")

if choice == "skip":
    print("  Skipped — files not exported.")
