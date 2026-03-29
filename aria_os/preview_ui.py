"""
ARIA CAD Preview UI

Opens a self-contained Three.js STL viewer in the default browser,
then prompts in the terminal for export format choice.

No local server is required: the STL is embedded as base64 inside the HTML.

Usage
-----
    from aria_os.preview_ui import show_preview
    choice = show_preview(stl_path, part_id="aria_housing")
    # choice -> "step" | "stl" | "both" | "skip"
"""
from __future__ import annotations

import base64
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Literal

ExportChoice = Literal["step", "stl", "both", "fusion", "skip"]

# ---------------------------------------------------------------------------
# HTML template  (Three.js r163 from CDN, STL embedded as base64)
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ARIA Preview \u2014 {part_id}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0d1117; color:#e6edf3;
         font-family:'Segoe UI',system-ui,sans-serif;
         height:100vh; display:flex; flex-direction:column; overflow:hidden; }}
  #toolbar {{ background:#161b22; border-bottom:1px solid #30363d;
              padding:10px 20px; display:flex; align-items:center;
              gap:14px; flex-shrink:0; }}
  #title   {{ font-size:15px; font-weight:600; color:#58a6ff; }}
  #meta    {{ font-size:12px; color:#8b949e; }}
  #viewer  {{ flex:1; display:block; }}
  #footer  {{ background:#161b22; border-top:1px solid #30363d;
              padding:10px 20px; font-size:12px; color:#8b949e; text-align:center; }}
  .badge   {{ background:#21262d; border:1px solid #30363d; border-radius:6px;
              padding:3px 10px; font-size:11px; color:#c9d1d9; }}
</style>
</head>
<body>
<div id="toolbar">
  <span id="title">ARIA CAD Preview</span>
  <span id="meta">{part_id}&nbsp;&middot;&nbsp;{stl_kb:.1f}&nbsp;KB</span>
  <span style="flex:1"></span>
  <span class="badge" id="dims">loading&hellip;</span>
  <span class="badge" style="color:#58a6ff">select format in your terminal</span>
</div>
<canvas id="viewer"></canvas>
<div id="footer">
  Orbit: left-drag &nbsp;&middot;&nbsp; Zoom: scroll &nbsp;&middot;&nbsp;
  Pan: right-drag &nbsp;&middot;&nbsp;
  <strong>Type your export choice in the terminal window</strong>
</div>

<script type="importmap">
{{"imports":{{
  "three":"https://cdn.jsdelivr.net/npm/three@0.163.0/build/three.module.js",
  "three/addons/":"https://cdn.jsdelivr.net/npm/three@0.163.0/examples/jsm/"
}}}}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }}  from 'three/addons/controls/OrbitControls.js';
import {{ STLLoader }}      from 'three/addons/loaders/STLLoader.js';

const canvas = document.getElementById('viewer');

const renderer = new THREE.WebGLRenderer({{ canvas, antialias:true }});
renderer.setPixelRatio(devicePixelRatio);
renderer.shadowMap.enabled = true;

const scene  = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);

// Lighting
const ambient = new THREE.AmbientLight(0xffffff, 0.55);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xffffff, 1.1);
sun.position.set(2, 4, 3);
sun.castShadow = true;
scene.add(sun);
const fill = new THREE.DirectionalLight(0x4488ff, 0.25);
fill.position.set(-3, -2, -1);
scene.add(fill);

const camera   = new THREE.PerspectiveCamera(45, 1, 0.01, 1e6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping  = true;
controls.dampingFactor  = 0.08;

// Decode STL
const b64 = "{stl_b64}";
const raw = atob(b64);
const buf = new Uint8Array(raw.length);
for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);

const geo = new STLLoader().parse(buf.buffer);
geo.computeBoundingBox();
const bbox   = geo.boundingBox;
const center = new THREE.Vector3();
bbox.getCenter(center);
geo.translate(-center.x, -center.y, -center.z);
geo.computeVertexNormals();

const size   = new THREE.Vector3();
bbox.getSize(size);
const maxDim = Math.max(size.x, size.y, size.z);

const material = new THREE.MeshPhysicalMaterial({{
  color:0x4a90d9, metalness:0.55, roughness:0.35, side:THREE.DoubleSide
}});
const mesh = new THREE.Mesh(geo, material);
mesh.castShadow = true;
scene.add(mesh);

// Grid floor
const grid = new THREE.GridHelper(maxDim * 3, 18, 0x222244, 0x191e2a);
grid.position.y = -(size.z / 2) - 0.5;
scene.add(grid);

// Fit camera — elevate more for flat parts (thickness < 20% of max planar dim)
const planarDim = Math.max(size.x, size.y);
const flatPart  = size.z < planarDim * 0.2;
const camY      = flatPart ? maxDim * 2.2 : maxDim * 1.1;
camera.position.set(maxDim * 1.4, camY, maxDim * 1.4);
controls.target.set(0, 0, 0);
controls.update();

// Dims badge
document.getElementById('dims').textContent =
  `${{size.x.toFixed(1)}} \u00d7 ${{size.y.toFixed(1)}} \u00d7 ${{size.z.toFixed(1)}} mm`;

// Resize
function onResize() {{
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight - 80; // toolbars
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}}
window.addEventListener('resize', onResize);
onResize();

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}}
animate();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_preview(
    stl_path: str | Path,
    part_id: str = "aria_part",
    script_path: str | Path | None = None,
) -> ExportChoice:
    """
    Render the generated part in the browser and ask the user to choose a
    format in the terminal.

    Parameters
    ----------
    stl_path    : path to the generated STL (must exist)
    part_id     : display name shown in the viewer title bar
    script_path : path to the .py source (shown in terminal output only)

    Returns
    -------
    "step" | "stl" | "both" | "skip"
    """
    stl_path = Path(stl_path)
    if not stl_path.exists():
        print(f"[PREVIEW] STL not found: {stl_path}  — skipping preview, defaulting to 'both'")
        return "both"

    stl_bytes = stl_path.read_bytes()
    stl_kb    = len(stl_bytes) / 1024
    stl_b64   = base64.b64encode(stl_bytes).decode("ascii")

    html = _HTML_TEMPLATE.format(
        part_id=part_id,
        stl_kb=stl_kb,
        stl_b64=stl_b64,
    )

    # Write to a temp file and open in browser
    tmp_dir  = Path(tempfile.gettempdir())
    html_path = tmp_dir / f"aria_preview_{part_id}.html"
    html_path.write_text(html, encoding="utf-8")

    url = html_path.as_uri()
    print(f"\n[PREVIEW] Opening 3D viewer in browser...")
    if script_path:
        print(f"[PREVIEW] Source: {script_path}")
    print(f"[PREVIEW] STL:    {stl_path}  ({stl_kb:.1f} KB)")
    print(f"[PREVIEW] Viewer: {html_path}")

    # Use os.startfile on Windows so the OS default browser opens the HTML,
    # not whichever app Python's webbrowser module happens to pick up
    # (e.g. Cursor's embedded browser when running inside the IDE).
    import platform, subprocess
    if platform.system() == "Windows":
        # cmd /c start uses the Windows URL handler (default browser),
        # not the .html file association (which Cursor may have claimed).
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    else:
        webbrowser.open(url)

    return _prompt_export_choice()


def _prompt_export_choice() -> ExportChoice:
    """Block on stdin until the user picks a valid export format."""
    print()
    print("=" * 64)
    print("  ARIA CAD Preview — choose export format")
    print("=" * 64)
    print("  [1] step   — export STEP only  (for CAD tools / assembly)")
    print("  [2] stl    — export STL only   (for slicers / mesh tools)")
    print("  [3] both   — export STEP + STL (default)")
    print("  [4] fusion — generate Fusion 360 script (parametric feature tree)")
    print("  [5] skip   — discard this run, do not export")
    print("=" * 64)

    _MAP: dict[str, ExportChoice] = {
        "1": "step",   "step": "step",   "s": "step",
        "2": "stl",    "stl": "stl",
        "3": "both",   "both": "both",   "b": "both",  "": "both",
        "4": "fusion", "fusion": "fusion", "f": "fusion",
        "5": "skip",   "skip": "skip",   "n": "skip",  "no": "skip",
        "discard": "skip",
    }

    # Non-interactive / piped stdin → default without blocking
    if not sys.stdin.isatty():
        print("  (non-interactive — defaulting to 'both')")
        return "both"

    while True:
        try:
            raw = input("  Your choice [1/2/3/4/5] (default: both): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  (interrupted — skipping export)")
            return "skip"
        choice = _MAP.get(raw)
        if choice is not None:
            print(f"  Selected: {choice.upper()}")
            return choice
        print(f"  Unrecognised: {raw!r} — enter 1, 2, 3, 4, or 5")
