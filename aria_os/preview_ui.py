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
import re
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Literal

ExportChoice = Literal["step", "stl", "both", "fusion", "skip"]

# ---------------------------------------------------------------------------
# DXF preview HTML  (SVG embedded inline, pan/zoom + layer toggles)
# ---------------------------------------------------------------------------
_DXF_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ARIA DXF Preview \u2014 {title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0d1117; color:#e6edf3;
         font-family:'Segoe UI',system-ui,sans-serif;
         height:100vh; display:flex; flex-direction:column; overflow:hidden; }}
  #toolbar {{ background:#161b22; border-bottom:1px solid #30363d;
              padding:8px 16px; display:flex; align-items:center;
              gap:12px; flex-shrink:0; flex-wrap:wrap; }}
  #title   {{ font-size:14px; font-weight:600; color:#58a6ff; white-space:nowrap; }}
  #meta    {{ font-size:11px; color:#8b949e; white-space:nowrap; }}
  .badge   {{ background:#21262d; border:1px solid #30363d; border-radius:6px;
              padding:3px 10px; font-size:11px; color:#c9d1d9; cursor:pointer;
              user-select:none; white-space:nowrap; }}
  .badge:hover {{ border-color:#58a6ff; color:#58a6ff; }}
  #main    {{ flex:1; display:flex; overflow:hidden; }}
  #canvas  {{ flex:1; overflow:hidden; position:relative; cursor:grab; background:#0d1117; }}
  #canvas.grabbing {{ cursor:grabbing; }}
  #svg-wrap {{ position:absolute; top:0; left:0; transform-origin:0 0; }}
  #svg-wrap svg {{ display:block; }}
  #sidebar {{ width:220px; background:#161b22; border-left:1px solid #30363d;
              overflow-y:auto; flex-shrink:0; }}
  #sidebar h3 {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em;
                 color:#8b949e; padding:10px 12px 6px; border-bottom:1px solid #21262d; }}
  .layer-row {{ display:flex; align-items:center; gap:8px; padding:5px 12px;
                cursor:pointer; font-size:11px; border-radius:4px; margin:1px 4px; }}
  .layer-row:hover {{ background:#21262d; }}
  .layer-row.hidden {{ opacity:0.35; }}
  .dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
  .layer-name {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .layer-count {{ color:#8b949e; font-size:10px; flex-shrink:0; }}
  #footer {{ background:#161b22; border-top:1px solid #30363d;
             padding:6px 16px; font-size:11px; color:#8b949e;
             display:flex; gap:20px; flex-shrink:0; }}
</style>
</head>
<body>
<div id="toolbar">
  <span id="title">DXF Plan Viewer \u2014 {title}</span>
  <span id="meta">{discipline} &nbsp;&middot;&nbsp; {state} &nbsp;&middot;&nbsp; {entity_count} entities</span>
  <span style="flex:1"></span>
  <span class="badge" onclick="fitView()">&#8982; Fit</span>
  <span class="badge" onclick="zoomIn()">+</span>
  <span class="badge" onclick="zoomOut()">&#8722;</span>
  <span class="badge" id="all-toggle" onclick="toggleAll()">Hide All</span>
</div>
<div id="main">
  <div id="canvas">
    <div id="svg-wrap">{svg_content}</div>
  </div>
  <div id="sidebar">
    <h3>Layers ({layer_count})</h3>
    <div id="layer-list">{layer_rows}</div>
  </div>
</div>
<div id="footer">
  <span>Pan: drag &nbsp;&middot;&nbsp; Zoom: scroll &nbsp;&middot;&nbsp; Reset: double-click</span>
  <span id="coord-display">x: — &nbsp; y: —</span>
</div>
<script>
const wrap = document.getElementById('svg-wrap');
const canvas = document.getElementById('canvas');
let tx = 40, ty = 40, scale = 1.0;

function applyTransform() {{
  wrap.style.transform = `translate(${{tx}}px,${{ty}}px) scale(${{scale}})`;
}}

function fitView() {{
  const svg = wrap.querySelector('svg');
  if (!svg) return;
  const vb = svg.getAttribute('viewBox');
  if (!vb) return;
  const [, , vw, vh] = vb.split(' ').map(Number);
  const cw = canvas.clientWidth - 40;
  const ch = canvas.clientHeight - 40;
  scale = Math.min(cw / vw, ch / vh) * 0.92;
  tx = (canvas.clientWidth  - vw * scale) / 2;
  ty = (canvas.clientHeight - vh * scale) / 2;
  applyTransform();
}}
function zoomIn()  {{ scale = Math.min(scale * 1.25, 200); applyTransform(); }}
function zoomOut() {{ scale = Math.max(scale / 1.25, 0.02); applyTransform(); }}

// Pan
let drag = false, lastX = 0, lastY = 0;
canvas.addEventListener('mousedown', e => {{
  if (e.button !== 0) return;
  drag = true; lastX = e.clientX; lastY = e.clientY;
  canvas.classList.add('grabbing');
}});
window.addEventListener('mousemove', e => {{
  if (!drag) return;
  tx += e.clientX - lastX; ty += e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  applyTransform();
  // coordinate display
  const svg = wrap.querySelector('svg');
  const vb  = svg && svg.getAttribute('viewBox');
  if (vb) {{
    const [vx, vy, vw, vh] = vb.split(' ').map(Number);
    const svgX = (e.clientX - canvas.getBoundingClientRect().left - tx) / scale + vx;
    const svgY = (e.clientY - canvas.getBoundingClientRect().top  - ty) / scale + vy;
    document.getElementById('coord-display').textContent =
      `x: ${{svgX.toFixed(1)}} &nbsp; y: ${{(-svgY).toFixed(1)}}`;
  }}
}});
window.addEventListener('mouseup', () => {{ drag = false; canvas.classList.remove('grabbing'); }});
canvas.addEventListener('dblclick', fitView);

// Scroll zoom
canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  const rect   = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const factor = e.deltaY < 0 ? 1.12 : 1/1.12;
  tx = mouseX - (mouseX - tx) * factor;
  ty = mouseY - (mouseY - ty) * factor;
  scale = Math.max(0.02, Math.min(200, scale * factor));
  applyTransform();
}}, {{ passive: false }});

// Layer toggles
const layerStates = {{}};
function toggleLayer(name) {{
  layerStates[name] = !layerStates[name];
  const svg = wrap.querySelector('svg');
  if (svg) {{
    // ezdxf groups layers as <g class="dxf-layer" data-layer="NAME">
    svg.querySelectorAll('[data-layer]').forEach(g => {{
      if (g.dataset.layer === name) g.style.display = layerStates[name] ? 'none' : '';
    }});
    // fallback: id-based grouping
    const gById = svg.getElementById('layer-' + name.replace(/[^a-zA-Z0-9_-]/g,'_'));
    if (gById) gById.style.display = layerStates[name] ? 'none' : '';
  }}
  const row = document.querySelector(`.layer-row[data-layer="${{name}}"]`);
  if (row) row.classList.toggle('hidden', layerStates[name]);
}}
document.querySelectorAll('.layer-row').forEach(row => {{
  row.addEventListener('click', () => toggleLayer(row.dataset.layer));
}});

let allHidden = false;
function toggleAll() {{
  allHidden = !allHidden;
  document.querySelectorAll('.layer-row').forEach(row => {{
    if (allHidden !== !!layerStates[row.dataset.layer]) toggleLayer(row.dataset.layer);
  }});
  document.getElementById('all-toggle').textContent = allHidden ? 'Show All' : 'Hide All';
}}

// Initial fit after a short delay (SVG needs to be rendered)
setTimeout(fitView, 120);
window.addEventListener('resize', fitView);
</script>
</body>
</html>
"""

# ACI color → hex mapping (standard AutoCAD 256-color palette, common entries)
_ACI_TO_HEX = {
    0:  "#ffffff",  # ByBlock
    1:  "#ff0000",  2:  "#ffff00",  3:  "#00ff00",
    4:  "#00ffff",  5:  "#0000ff",  6:  "#ff00ff",
    7:  "#ffffff",  8:  "#808080",  9:  "#c0c0c0",
    30: "#ff7f00",  34: "#7f3f00",  92: "#80ff80",
    150: "#80c0ff", 200: "#ff80c0",
}

def _aci_to_hex(aci: int) -> str:
    return _ACI_TO_HEX.get(aci, "#aaaaaa")


def _dxf_to_svg(dxf_path: "Path") -> tuple[str, list[dict]]:
    """
    Convert a DXF file to an SVG string using ezdxf's drawing backend.
    Returns (svg_string, layer_info_list).
    layer_info = [{name, color_hex, entity_count}, ...]
    Falls back to a simple line-drawing if the drawing addon is unavailable.
    """
    import ezdxf

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    # Collect layer info for the sidebar
    from aria_os.autocad.layer_manager import LAYER_DEFS
    layer_info: list[dict] = []
    entity_layers: dict[str, int] = {}
    for entity in msp:
        lyr = getattr(entity.dxf, "layer", "0")
        entity_layers[lyr] = entity_layers.get(lyr, 0) + 1

    for lyr_name, count in sorted(entity_layers.items(), key=lambda x: -x[1]):
        aci = 7  # default white
        if lyr_name in doc.layers:
            aci = doc.layers.get(lyr_name).color
        elif lyr_name in LAYER_DEFS:
            aci = LAYER_DEFS[lyr_name]["color"]
        layer_info.append({
            "name": lyr_name,
            "color_hex": _aci_to_hex(abs(aci)),
            "count": count,
        })

    # Try ezdxf drawing backend for SVG
    try:
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.svg import SVGBackend
        from ezdxf.addons.drawing.layout import Page

        page = Page(width=600, height=500)

        context  = RenderContext(doc)
        backend  = SVGBackend()
        frontend = Frontend(context, backend)
        frontend.draw_layout(msp, finalize=True)
        svg_string = backend.get_string(page)
        # Strip XML declaration; force transparent background
        lines = [l for l in svg_string.splitlines() if not l.startswith("<?xml")]
        svg_string = "\n".join(lines)
        svg_string = re.sub(
            r'(<svg\b[^>]*?)(\s*style="[^"]*")?(\s*>)',
            lambda m: m.group(1) + ' style="background:transparent;display:block"' + m.group(3),
            svg_string, count=1
        )
        return svg_string, layer_info

    except Exception:
        pass  # fall through to manual SVG builder

    # Fallback: manual SVG from ezdxf entities
    return _manual_svg(msp, doc), layer_info


def _manual_svg(msp: Any, doc: Any) -> str:
    """
    Build a minimal SVG from LINE, LWPOLYLINE, CIRCLE, TEXT entities.
    Used when ezdxf drawing addon is unavailable or fails.
    """
    import ezdxf
    from aria_os.autocad.layer_manager import LAYER_DEFS

    lines: list[str] = []
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    def _upd(x: float, y: float) -> None:
        nonlocal min_x, min_y, max_x, max_y
        min_x = min(min_x, x); min_y = min(min_y, y)
        max_x = max(max_x, x); max_y = max(max_y, y)

    elements: list[str] = []

    for entity in msp:
        try:
            lyr = getattr(entity.dxf, "layer", "0")
            aci = 7
            if lyr in LAYER_DEFS:
                aci = LAYER_DEFS[lyr]["color"]
            elif lyr in doc.layers:
                aci = doc.layers.get(lyr).color
            color = _aci_to_hex(abs(aci))
            t = entity.dxftype()

            if t == "LINE":
                x1, y1 = entity.dxf.start.x, entity.dxf.start.y
                x2, y2 = entity.dxf.end.x,   entity.dxf.end.y
                _upd(x1, y1); _upd(x2, y2)
                elements.append(
                    f'<line x1="{x1:.3f}" y1="{-y1:.3f}" x2="{x2:.3f}" y2="{-y2:.3f}" '
                    f'stroke="{color}" stroke-width="0.3" data-layer="{lyr}"/>'
                )
            elif t == "LWPOLYLINE":
                pts = list(entity.get_points())
                if len(pts) >= 2:
                    for p in pts:
                        _upd(p[0], p[1])
                    d = "M " + " L ".join(f"{p[0]:.3f},{-p[1]:.3f}" for p in pts)
                    if entity.closed:
                        d += " Z"
                    elements.append(
                        f'<path d="{d}" fill="none" stroke="{color}" '
                        f'stroke-width="0.3" data-layer="{lyr}"/>'
                    )
            elif t == "CIRCLE":
                cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
                _upd(cx - r, cy - r); _upd(cx + r, cy + r)
                elements.append(
                    f'<circle cx="{cx:.3f}" cy="{-cy:.3f}" r="{r:.3f}" fill="none" '
                    f'stroke="{color}" stroke-width="0.3" data-layer="{lyr}"/>'
                )
            elif t in ("TEXT", "MTEXT"):
                try:
                    ins = entity.dxf.insert
                    txt = entity.plain_mtext() if t == "MTEXT" else entity.dxf.text
                    h = getattr(entity.dxf, "height", 0.12)
                    _upd(ins.x, ins.y)
                    elements.append(
                        f'<text x="{ins.x:.3f}" y="{-ins.y:.3f}" fill="{color}" '
                        f'font-size="{h:.3f}" font-family="monospace" '
                        f'data-layer="{lyr}">{txt[:80]}</text>'
                    )
                except Exception:
                    pass
        except Exception:
            continue

    if min_x == float("inf"):
        min_x = min_y = 0; max_x = max_y = 100

    pad = (max_x - min_x + max_y - min_y) * 0.05 + 5
    vx = min_x - pad; vy = -(max_y + pad)
    vw = (max_x - min_x) + 2 * pad
    vh = (max_y - min_y) + 2 * pad

    # Group by layer
    layer_groups: dict[str, list[str]] = {}
    for el in elements:
        import re as _re
        m = _re.search(r'data-layer="([^"]*)"', el)
        lyr = m.group(1) if m else "0"
        layer_groups.setdefault(lyr, []).append(el)

    body = "\n".join(
        f'<g id="layer-{lyr.replace(" ", "_")}" data-layer="{lyr}">'
        + "\n".join(elems) + "</g>"
        for lyr, elems in layer_groups.items()
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}" '
        f'style="background:#0d1117">\n{body}\n</svg>'
    )


def show_dxf_preview(
    dxf_path: "str | Path",
    title: str = "",
    discipline: str = "",
    state: str = "",
) -> None:
    """
    Open the DXF in the same browser-based viewer used for STL previews.
    Reuses the local HTTP server infrastructure from show_preview().
    Non-blocking: server runs in background daemon thread.
    """
    import http.server
    import socket
    import threading

    dxf_path = Path(dxf_path)
    if not dxf_path.exists():
        print(f"[DXF PREVIEW] File not found: {dxf_path}")
        return

    title     = title or dxf_path.stem
    discipline = discipline or ""
    state      = state or ""

    print(f"[DXF PREVIEW] Converting {dxf_path.name} to SVG ...")
    try:
        svg_content, layer_info = _dxf_to_svg(dxf_path)
    except Exception as exc:
        print(f"[DXF PREVIEW] SVG conversion failed: {exc}")
        print(f"[DXF PREVIEW] Falling back to ezdxf viewer: python -m ezdxf view {dxf_path}")
        import subprocess
        subprocess.Popen([sys.executable, "-m", "ezdxf", "view", str(dxf_path)])
        return

    entity_count = sum(l["count"] for l in layer_info)

    # Build layer sidebar rows
    layer_rows = "\n".join(
        f'<div class="layer-row" data-layer="{l["name"]}">'
        f'<span class="dot" style="background:{l["color_hex"]}"></span>'
        f'<span class="layer-name" title="{l["name"]}">{l["name"]}</span>'
        f'<span class="layer-count">{l["count"]}</span></div>'
        for l in layer_info
    )

    html = _DXF_HTML_TEMPLATE.format(
        title=title,
        discipline=discipline or "civil",
        state=state.upper() or "—",
        entity_count=entity_count,
        layer_count=len(layer_info),
        svg_content=svg_content,
        layer_rows=layer_rows,
    )

    tmp_dir   = Path(tempfile.gettempdir())
    slug      = re.sub(r"[^a-z0-9_]", "_", title.lower())[:40]
    html_path = tmp_dir / f"aria_dxf_{slug}.html"
    html_path.write_text(html, encoding="utf-8")

    # Reuse the same free-port + HTTP server pattern
    def _find_free_port() -> int:
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    port = _find_free_port()

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(tmp_dir), **kw)
        def log_message(self, *_):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://localhost:{port}/{html_path.name}"
    print(f"[DXF PREVIEW] {entity_count} entities across {len(layer_info)} layers")
    print(f"[DXF PREVIEW] URL --> {url}")
    print(f"[DXF PREVIEW] In Cursor: Ctrl+Shift+P -> 'Simple Browser: Show' -> paste URL")
    webbrowser.open(url)


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
    view_only: bool = False,
) -> ExportChoice:
    """
    Render the generated part in the browser and ask the user to choose a
    format in the terminal.

    Parameters
    ----------
    stl_path    : path to the generated STL (must exist)
    part_id     : display name shown in the viewer title bar
    script_path : path to the .py source (shown in terminal output only)
    view_only   : if True, keep server alive until Ctrl+C (no export prompt)

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

    # Serve via a local HTTP server so Simple Browser (http:// only) can load it.
    import http.server, threading, socket

    def _find_free_port() -> int:
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    port = _find_free_port()
    serve_dir = tmp_dir

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_dir), **kw)
        def log_message(self, *_):
            pass  # silence request log

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    http_url = f"http://localhost:{port}/{html_path.name}"

    print(f"\n[PREVIEW] 3D viewer ready.")
    if script_path:
        print(f"[PREVIEW] Source: {script_path}")
    print(f"[PREVIEW] STL:    {stl_path}  ({stl_kb:.1f} KB)")
    print(f"[PREVIEW]")
    print(f"[PREVIEW] URL --> http://localhost:{port}/{html_path.name}")
    print(f"[PREVIEW]")
    print(f"[PREVIEW] In Cursor: Ctrl+Shift+P -> 'Simple Browser: Show' -> paste URL above")
    print(f"[PREVIEW] Keep this terminal open while viewing.")

    if view_only:
        print(f"\n[PREVIEW] Server running — press Ctrl+C to stop.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()
            print("\n[PREVIEW] Server stopped.")
        return "skip"

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
