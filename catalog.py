"""
catalog.py — Generates a self-contained HTML catalog of all parts in outputs/cad/.

Usage:
    python catalog.py
    python catalog.py --output outputs/catalog.html
    python catalog.py --dir outputs/cad/step/

- Scans outputs/cad/step/ for .step files, outputs/cad/stl/ for .stl files
- For each part: reads file size, modification time
- If a corresponding meta JSON exists in outputs/cad/meta/, reads bbox from it
- Generates a single-file HTML with:
    - Table/grid: part name, file sizes (STEP/STL), bbox (XxYxZ mm), date generated
    - Simple CSS, no external dependencies
    - "Copy path" button per row (copies STEP path to clipboard via JS)
    - Summary stats at top: total parts, total file size
- Opens the HTML in the default browser after generating
- Prints the output path
"""
import sys
import json
import webbrowser
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFAULT_STEP_DIR = ROOT / "outputs" / "cad" / "step"
DEFAULT_STL_DIR  = ROOT / "outputs" / "cad" / "stl"
DEFAULT_META_DIR = ROOT / "outputs" / "cad" / "meta"
DEFAULT_OUTPUT   = ROOT / "outputs" / "catalog.html"


def _fmt_size(n: int | None) -> str:
    if n is None:
        return "—"
    if n >= 1_048_576:
        return f"{n/1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n/1024:.1f} KB"
    return f"{n} B"


def _fmt_date(ts: float | None) -> str:
    if ts is None:
        return "—"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _read_bbox_from_meta(meta_dir: Path, part_id: str) -> str:
    """Try to read bbox from outputs/cad/meta/{part_id}.json."""
    meta_path = meta_dir / f"{part_id}.json"
    if not meta_path.exists():
        return "—"
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Support both {"bbox": {"x":..,"y":..,"z":..}} and {"x":..,"y":..,"z":..}
        bbox = data.get("bbox", data)
        if isinstance(bbox, dict) and all(k in bbox for k in ("x", "y", "z")):
            return f"{bbox['x']}&times;{bbox['y']}&times;{bbox['z']}"
    except Exception:
        pass
    return "—"


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def collect_parts(step_dir: Path, stl_dir: Path, meta_dir: Path) -> list[dict]:
    """Collect part info from the STEP directory."""
    parts = []
    for step_file in sorted(step_dir.glob("*.step"), key=lambda f: f.stem.lower()):
        part_id = step_file.stem
        step_size = step_file.stat().st_size
        step_mtime = step_file.stat().st_mtime

        stl_file = stl_dir / f"{part_id}.stl"
        stl_size  = stl_file.stat().st_size  if stl_file.exists() else None
        stl_mtime = stl_file.stat().st_mtime if stl_file.exists() else None

        # Use the more recent mtime as the "generated" time
        gen_time = max(filter(None, [step_mtime, stl_mtime]), default=step_mtime)

        bbox = _read_bbox_from_meta(meta_dir, part_id)

        parts.append({
            "part_id":   part_id,
            "step_path": str(step_file),
            "step_size": step_size,
            "stl_size":  stl_size,
            "bbox":      bbox,
            "gen_time":  gen_time,
        })
    return parts


def _total_size(parts: list[dict]) -> int:
    total = 0
    for p in parts:
        if p["step_size"]:
            total += p["step_size"]
        if p["stl_size"]:
            total += p["stl_size"]
    return total


def _generate_html(parts: list[dict], title: str = "ARIA CAD Parts Catalog") -> str:
    total_size_str = _fmt_size(_total_size(parts))
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    rows_html = ""
    for i, p in enumerate(parts, 1):
        step_path_escaped  = _escape_html(p["step_path"])
        part_id_escaped    = _escape_html(p["part_id"])
        step_size_str      = _fmt_size(p["step_size"])
        stl_size_str       = _fmt_size(p["stl_size"])
        bbox_str           = p["bbox"]
        date_str           = _fmt_date(p["gen_time"])

        rows_html += f"""
        <tr>
          <td class="idx">{i}</td>
          <td class="name" title="{step_path_escaped}">{part_id_escaped}</td>
          <td class="size">{step_size_str}</td>
          <td class="size">{stl_size_str}</td>
          <td class="bbox">{bbox_str}</td>
          <td class="date">{date_str}</td>
          <td class="action">
            <button class="copy-btn" onclick="copyPath(this)" data-path="{step_path_escaped}" title="Copy STEP path">&#128203;</button>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(title)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    background: #f0f2f5;
    color: #1a1a2e;
  }}
  header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: #e0e0e0;
    padding: 24px 32px 20px;
    border-bottom: 3px solid #e94560;
  }}
  header h1 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.03em;
    color: #fff;
    margin-bottom: 4px;
  }}
  header p {{
    font-size: 12px;
    color: #9ab;
  }}
  .stats {{
    display: flex;
    gap: 24px;
    padding: 16px 32px;
    background: #fff;
    border-bottom: 1px solid #dde;
    flex-wrap: wrap;
  }}
  .stat-chip {{
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    color: #3730a3;
    font-weight: 500;
  }}
  .stat-chip span {{
    font-weight: 700;
  }}
  .container {{
    padding: 24px 32px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
  }}
  thead {{
    background: #1a1a2e;
    color: #c8d0e0;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  thead th {{
    padding: 12px 14px;
    text-align: left;
    font-weight: 600;
  }}
  tbody tr {{
    border-bottom: 1px solid #eef0f5;
    transition: background 0.12s;
  }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #f5f7ff; }}
  td {{
    padding: 10px 14px;
    vertical-align: middle;
  }}
  td.idx {{
    width: 42px;
    color: #999;
    font-size: 12px;
    text-align: right;
  }}
  td.name {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 13px;
    font-weight: 500;
    color: #0f3460;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  td.size {{
    width: 90px;
    text-align: right;
    color: #555;
    font-size: 12px;
  }}
  td.bbox {{
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 12px;
    color: #333;
    white-space: nowrap;
  }}
  td.date {{
    font-size: 12px;
    color: #666;
    white-space: nowrap;
  }}
  td.action {{
    width: 44px;
    text-align: center;
  }}
  .copy-btn {{
    background: none;
    border: 1px solid #dde;
    border-radius: 5px;
    cursor: pointer;
    padding: 4px 7px;
    font-size: 14px;
    transition: background 0.1s, border-color 0.1s;
    color: #444;
  }}
  .copy-btn:hover {{
    background: #e8eaff;
    border-color: #7c83e5;
  }}
  .copy-btn.copied {{
    background: #d1fae5;
    border-color: #34d399;
    color: #065f46;
  }}
  #toast {{
    position: fixed;
    bottom: 28px;
    right: 28px;
    background: #1a1a2e;
    color: #e0ffe8;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    opacity: 0;
    transition: opacity 0.25s;
    pointer-events: none;
    border-left: 4px solid #34d399;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  }}
  footer {{
    text-align: center;
    padding: 20px;
    color: #aaa;
    font-size: 11px;
  }}
</style>
</head>
<body>

<header>
  <h1>{_escape_html(title)}</h1>
  <p>Generated {now_str} &nbsp;&bull;&nbsp; ARIA Auto-Belay CAD Pipeline</p>
</header>

<div class="stats">
  <div class="stat-chip">Total parts: <span>{len(parts)}</span></div>
  <div class="stat-chip">Total size: <span>{total_size_str}</span></div>
  <div class="stat-chip">Generated: <span>{now_str}</span></div>
</div>

<div class="container">
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Part ID</th>
        <th style="text-align:right">STEP</th>
        <th style="text-align:right">STL</th>
        <th>BBox (X&times;Y&times;Z mm)</th>
        <th>Generated</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>

<footer>ARIA CAD Pipeline &bull; {len(parts)} parts</footer>

<div id="toast">Path copied!</div>

<script>
function copyPath(btn) {{
  var path = btn.getAttribute('data-path');
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(path).then(function() {{
      flashCopied(btn);
    }}).catch(function() {{
      fallbackCopy(path, btn);
    }});
  }} else {{
    fallbackCopy(path, btn);
  }}
}}

function fallbackCopy(text, btn) {{
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {{ document.execCommand('copy'); }} catch(e) {{}}
  document.body.removeChild(ta);
  flashCopied(btn);
}}

function flashCopied(btn) {{
  btn.classList.add('copied');
  btn.textContent = '✓';
  var toast = document.getElementById('toast');
  toast.style.opacity = '1';
  setTimeout(function() {{
    toast.style.opacity = '0';
    btn.classList.remove('copied');
    btn.innerHTML = '&#128203;';
  }}, 1800);
}}
</script>

</body>
</html>"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained HTML catalog of all parts in outputs/cad/."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"Output HTML path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_STEP_DIR,
        metavar="STEP_DIR",
        help=f"Directory to scan for .step files (default: {DEFAULT_STEP_DIR})",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the HTML in a browser after generating",
    )
    args = parser.parse_args()

    step_dir = args.dir
    if not step_dir.is_absolute():
        step_dir = ROOT / step_dir

    # Derive sibling stl/ and meta/ directories from the step/ dir
    stl_dir  = step_dir.parent / "stl"
    meta_dir = step_dir.parent / "meta"

    if not step_dir.exists():
        print(f"[catalog] Error: STEP directory not found: {step_dir}")
        print(f"          Run the CAD pipeline first to generate parts.")
        sys.exit(1)

    parts = collect_parts(step_dir, stl_dir, meta_dir)

    if not parts:
        print(f"[catalog] No .step files found in {step_dir}")
        print(f"          Run 'python batch.py' or 'python generate_clock.py' first.")
        sys.exit(0)

    print(f"[catalog] Found {len(parts)} part(s) in {step_dir}")

    html = _generate_html(parts)

    output_path = args.output
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    size_str = _fmt_size(output_path.stat().st_size)
    print(f"[catalog] Written: {output_path}  ({size_str})")

    if not args.no_open:
        webbrowser.open(output_path.as_uri())
        print(f"[catalog] Opened in browser.")


if __name__ == "__main__":
    main()
