"""GD&T engineering drawing generator for ARIA-OS.

Takes a STEP file, projects three orthographic views via CadQuery,
then composes them into a single-page A3 landscape SVG with a title
block, dimension annotations, and basic GD&T symbols.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_gdnt_drawing(
    step_path: str | Path,
    part_id: str,
    params: dict | None = None,
    repo_root: Path | None = None,
) -> Path:
    """
    Generate a GD&T engineering drawing SVG from a STEP file.
    Returns path to the output SVG file.
    Output: outputs/drawings/<part_id>.svg
    """
    step_path = Path(step_path)
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    out_dir = repo_root / "outputs" / "drawings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{part_id}.svg"

    params = params or {}

    # Try to load projections from CadQuery; fall back to None on any error.
    bb: _BBox | None = None
    svg_front: str | None = None
    svg_top:   str | None = None
    svg_right: str | None = None

    if step_path.exists():
        try:
            bb, svg_front, svg_top, svg_right = _load_projections(step_path)
        except Exception as exc:
            print(f"[GD&T] CadQuery projection failed ({exc}); generating fallback drawing.")

    # Compose final SVG
    svg_content = _compose_drawing(
        part_id=part_id,
        params=params,
        bb=bb,
        svg_front=svg_front,
        svg_top=svg_top,
        svg_right=svg_right,
    )

    out_path.write_text(svg_content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _BBox:
    """Minimal bounding-box wrapper."""
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin = xmin; self.xmax = xmax
        self.ymin = ymin; self.ymax = ymax
        self.zmin = zmin; self.zmax = zmax
        self.xlen = xmax - xmin
        self.ylen = ymax - ymin
        self.zlen = zmax - zmin


def _load_projections(step_path: Path):
    """
    Load a STEP file with CadQuery and export three orthographic SVG projections.
    Returns (BBox, svg_front_str, svg_top_str, svg_right_str).
    """
    import cadquery as cq
    from cadquery import exporters, importers  # type: ignore

    shape = importers.importStep(str(step_path))
    raw_bb = shape.val().BoundingBox()
    bb = _BBox(raw_bb.xmin, raw_bb.xmax, raw_bb.ymin, raw_bb.ymax, raw_bb.zmin, raw_bb.zmax)

    _PROJ_OPTS = {"showAxes": False, "strokeColor": (0, 0, 0), "hiddenColor": (160, 160, 160)}

    def _get_svg(direction: tuple) -> str:
        opts = {**_PROJ_OPTS, "projectionDir": direction}
        try:
            return exporters.getSVG(shape.val(), opts=opts)
        except Exception:
            # Older CadQuery versions don't accept opts dict
            try:
                return exporters.getSVG(shape.val())
            except Exception:
                return ""

    svg_front = _get_svg((0, -1, 0))
    svg_top   = _get_svg((0, 0, 1))
    svg_right = _get_svg((1, 0, 0))

    return bb, svg_front, svg_top, svg_right


# ---------------------------------------------------------------------------
# SVG composition
# ---------------------------------------------------------------------------

# A3 landscape at 96 dpi ≈ 1587 × 1123 px
_W  = 1587
_H  = 1123
_BORDER = 20
_TITLE_W = 400
_TITLE_H = 120
_FONT = "monospace"
_LABEL_FONT = "Arial, sans-serif"


def _compose_drawing(
    *,
    part_id: str,
    params: dict,
    bb: _BBox | None,
    svg_front: str | None,
    svg_top:   str | None,
    svg_right: str | None,
) -> str:
    """Build the full A3 SVG drawing and return it as a string."""

    lines: list[str] = []

    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" '
        f'font-family="{_LABEL_FONT}" font-size="12">'
    )

    # ---- Background ----
    lines.append(f'  <rect width="{_W}" height="{_H}" fill="white"/>')

    # ---- Drawing border ----
    b = _BORDER
    lines.append(
        f'  <rect x="{b}" y="{b}" width="{_W - 2*b}" height="{_H - 2*b}" '
        f'fill="none" stroke="black" stroke-width="2"/>'
    )

    # ---- Compute view areas ----
    # Drawing area minus border and title block
    # Title block: bottom-right corner
    title_x = _W - _BORDER - _TITLE_W
    title_y = _H - _BORDER - _TITLE_H

    draw_inner_w = _W - 2 * _BORDER
    draw_inner_h = _H - 2 * _BORDER - _TITLE_H - 8  # gap above title

    half_w = draw_inner_w // 2
    half_h = draw_inner_h // 2

    # View bounding rectangles (x, y, w, h) with small padding
    _pad = 8
    front_rect = (_BORDER + _pad,          _BORDER + _pad,          half_w - _pad*2, half_h - _pad*2)
    top_rect   = (_BORDER + half_w + _pad, _BORDER + _pad,          half_w - _pad*2, half_h - _pad*2)
    right_rect = (_BORDER + _pad,          _BORDER + half_h + _pad, half_w - _pad*2, half_h - _pad*2)
    # Isometric placeholder shares with right side of bottom-right quadrant (above title block)
    iso_rect   = (_BORDER + half_w + _pad, _BORDER + half_h + _pad, half_w - _pad*2 - (_TITLE_W - half_w + _pad), half_h - _pad*2)
    # Clamp iso width
    iso_rect = (iso_rect[0], iso_rect[1], max(10, iso_rect[2]), iso_rect[3])

    # ---- View box outlines ----
    for rx, ry, rw, rh in (front_rect, top_rect, right_rect, iso_rect):
        lines.append(
            f'  <rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" '
            f'fill="#fafafa" stroke="#aaa" stroke-width="0.5" stroke-dasharray="4,3"/>'
        )

    # ---- View labels ----
    label_style = 'font-size="10" fill="#555" font-family="Arial, sans-serif"'
    lines.append(f'  <text x="{front_rect[0]+4}" y="{front_rect[1]+12}" {label_style}>FRONT VIEW</text>')
    lines.append(f'  <text x="{top_rect[0]+4}"   y="{top_rect[1]+12}"   {label_style}>TOP VIEW</text>')
    lines.append(f'  <text x="{right_rect[0]+4}"  y="{right_rect[1]+12}"  {label_style}>RIGHT VIEW</text>')
    lines.append(f'  <text x="{iso_rect[0]+4}"   y="{iso_rect[1]+12}"   {label_style}>ISOMETRIC (N/A)</text>')

    # ---- Embed CadQuery SVG projections ----
    if svg_front:
        lines.append(_embed_svg(svg_front, front_rect, label="front"))
    if svg_top:
        lines.append(_embed_svg(svg_top,   top_rect,   label="top"))
    if svg_right:
        lines.append(_embed_svg(svg_right, right_rect, label="right"))

    # ---- Dimension annotations ----
    if bb is not None:
        lines.extend(_dimension_annotations(bb, front_rect, params))

    # ---- GD&T symbols ----
    if bb is not None:
        symbols = _classify_gdnt_symbols(bb, params)
        lines.extend(_render_gdnt_symbols(symbols, front_rect, right_rect))

    # ---- Title block ----
    lines.extend(_title_block(title_x, title_y, _TITLE_W, _TITLE_H, part_id, params))

    # ---- Fallback text when no projections loaded ----
    if bb is None:
        lines.append(
            f'  <text x="{_W//2}" y="{_H//2 - 40}" '
            f'text-anchor="middle" font-size="14" fill="#c00">'
            f'CadQuery projections unavailable — check STEP file</text>'
        )
        _fb_params = dict(params)
        _fb_lines = [
            f"Part ID : {part_id}",
            f"Material: {_fb_params.get('material', '—')}",
        ]
        for key in ("od_mm", "bore_mm", "height_mm", "width_mm", "depth_mm", "length_mm"):
            if key in _fb_params:
                _fb_lines.append(f"{key}: {_fb_params[key]} mm")
        for i, txt in enumerate(_fb_lines):
            lines.append(
                f'  <text x="{_W//2}" y="{_H//2 - 10 + i*18}" '
                f'text-anchor="middle" font-size="13" fill="#333">{_escape(txt)}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def _embed_svg(raw_svg: str, rect: tuple, *, label: str = "") -> str:
    """
    Parse a CadQuery SVG string, extract its viewBox, and return a <g> group
    that transforms the content to fit inside *rect* = (x, y, w, h).
    """
    rx, ry, rw, rh = rect
    # Label height reservation
    label_h = 16

    vb = _parse_viewbox(raw_svg)
    if vb is None:
        # No viewBox found — embed raw with a simple translate
        inner = _strip_svg_wrapper(raw_svg)
        return (
            f'  <g transform="translate({rx},{ry + label_h})" '
            f'clip-path="url(#clip_{label})">\n'
            f'    <clipPath id="clip_{label}"><rect width="{rw}" height="{rh - label_h}"/></clipPath>\n'
            f'    {inner}\n'
            f'  </g>'
        )

    vb_x, vb_y, vb_w, vb_h = vb
    if vb_w == 0 or vb_h == 0:
        return ""

    # Scale to fit rect while preserving aspect ratio
    scale = min(rw / vb_w, (rh - label_h) / vb_h) * 0.88  # 88% fill
    # Center within the rect
    tx = rx + (rw  - vb_w * scale) / 2 - vb_x * scale
    ty = ry + label_h + ((rh - label_h) - vb_h * scale) / 2 - vb_y * scale

    inner = _strip_svg_wrapper(raw_svg)
    clip_id = f"clip_{label}"
    return (
        f'  <clipPath id="{clip_id}"><rect x="{rx}" y="{ry}" width="{rw}" height="{rh}"/></clipPath>\n'
        f'  <g clip-path="url(#{clip_id})" transform="translate({tx:.2f},{ty:.2f}) scale({scale:.4f})">\n'
        f'    {inner}\n'
        f'  </g>'
    )


def _parse_viewbox(svg: str) -> tuple[float, float, float, float] | None:
    """Extract (x, y, w, h) from SVG viewBox attribute."""
    m = re.search(r'viewBox=["\']([^"\']+)["\']', svg, re.IGNORECASE)
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _strip_svg_wrapper(svg: str) -> str:
    """Return the inner content of an SVG string (strip outer <svg> tag)."""
    # Remove XML declaration
    svg = re.sub(r'<\?xml[^>]*\?>', '', svg).strip()
    # Remove outer <svg ...> ... </svg> wrapper
    svg = re.sub(r'^<svg[^>]*>', '', svg, count=1).strip()
    svg = re.sub(r'</svg>\s*$', '', svg).strip()
    return svg


# ---------------------------------------------------------------------------
# Dimension annotations
# ---------------------------------------------------------------------------

def _dimension_annotations(bb: _BBox, front_rect: tuple, params: dict) -> list[str]:
    """Return SVG lines for overall dimension annotations."""
    rx, ry, rw, rh = front_rect
    lines: list[str] = []

    xlen = round(bb.xlen, 2)
    ylen = round(bb.ylen, 2)
    zlen = round(bb.zlen, 2)

    # Overall width — below front view
    dim_y = ry + rh + 22
    dim_x1, dim_x2 = rx + 20, rx + rw - 20
    cx = (dim_x1 + dim_x2) / 2
    lines += _dim_line_h(dim_x1, dim_x2, dim_y, f"{xlen} mm", color="#1a1a8c")

    # Overall depth — right of front view
    dim_x = rx + rw + 22
    dim_y1, dim_y2 = ry + 20, ry + rh - 20
    cy = (dim_y1 + dim_y2) / 2
    lines += _dim_line_v(dim_x, dim_y1, dim_y2, f"{ylen} mm", color="#1a1a8c")

    # Overall height — left of front view
    dim_x_left = rx - 22
    lines += _dim_line_v(dim_x_left, ry + 20, ry + rh - 20, f"{zlen} mm", color="#1a1a8c")

    # Bore annotation
    bore = params.get("bore_mm")
    if bore:
        bx = rx + rw // 2
        by = ry + rh // 2
        lines.append(
            f'  <line x1="{bx}" y1="{by}" x2="{bx+40}" y2="{by-30}" '
            f'stroke="#c00" stroke-width="1"/>'
        )
        lines.append(
            f'  <text x="{bx+42}" y="{by-32}" fill="#c00" font-size="11">'
            f'&#x2300;{bore} mm</text>'
        )

    return lines


def _dim_line_h(x1: float, x2: float, y: float, text: str, *, color: str = "black") -> list[str]:
    """Horizontal dimension line with arrows."""
    ah = 5  # arrowhead half-height
    al = 8  # arrowhead length
    cx = (x1 + x2) / 2
    return [
        # Extension lines
        f'  <line x1="{x1}" y1="{y-ah*2}" x2="{x1}" y2="{y+ah*2}" stroke="{color}" stroke-width="0.8"/>',
        f'  <line x1="{x2}" y1="{y-ah*2}" x2="{x2}" y2="{y+ah*2}" stroke="{color}" stroke-width="0.8"/>',
        # Main dim line
        f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="0.8"/>',
        # Arrowheads
        f'  <polygon points="{x1},{y} {x1+al},{y-ah} {x1+al},{y+ah}" fill="{color}"/>',
        f'  <polygon points="{x2},{y} {x2-al},{y-ah} {x2-al},{y+ah}" fill="{color}"/>',
        # Label
        f'  <text x="{cx}" y="{y-6}" text-anchor="middle" font-size="11" fill="{color}">{_escape(text)}</text>',
    ]


def _dim_line_v(x: float, y1: float, y2: float, text: str, *, color: str = "black") -> list[str]:
    """Vertical dimension line with arrows."""
    ah = 5
    al = 8
    cy = (y1 + y2) / 2
    return [
        # Extension lines
        f'  <line x1="{x-ah*2}" y1="{y1}" x2="{x+ah*2}" y2="{y1}" stroke="{color}" stroke-width="0.8"/>',
        f'  <line x1="{x-ah*2}" y1="{y2}" x2="{x+ah*2}" y2="{y2}" stroke="{color}" stroke-width="0.8"/>',
        # Main dim line
        f'  <line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="0.8"/>',
        # Arrowheads
        f'  <polygon points="{x},{y1} {x-ah},{y1+al} {x+ah},{y1+al}" fill="{color}"/>',
        f'  <polygon points="{x},{y2} {x-ah},{y2-al} {x+ah},{y2-al}" fill="{color}"/>',
        # Rotated label
        f'  <text x="{x-14}" y="{cy}" text-anchor="middle" font-size="11" fill="{color}" '
        f'transform="rotate(-90,{x-14},{cy})">{_escape(text)}</text>',
    ]


# ---------------------------------------------------------------------------
# GD&T symbols
# ---------------------------------------------------------------------------

def _classify_gdnt_symbols(bb: _BBox, params: dict) -> list[dict]:
    """Return list of GD&T symbol dicts based on geometry analysis."""
    symbols: list[dict] = []

    # Cylindrical part → cylindricity
    if bb.zlen > bb.xlen * 2 and abs(bb.xlen - bb.ylen) < 1.0:
        symbols.append({"type": "cylindricity", "value": "0.05", "surface": "outer"})

    # Flat part → flatness
    if bb.zlen < min(bb.xlen, bb.ylen) * 0.2:
        symbols.append({"type": "flatness", "value": "0.02", "surface": "top"})

    # Has bore → position
    if params.get("bore_mm"):
        symbols.append({"type": "position", "value": "\u2300" + "0.1", "feature": "bore"})

    # Always: surface finish
    symbols.append({"type": "surface_finish", "value": "Ra 1.6"})

    return symbols


def _render_gdnt_symbols(symbols: list[dict], front_rect: tuple, right_rect: tuple) -> list[str]:
    """Render GD&T symbol boxes into SVG lines."""
    lines: list[str] = []
    rx, ry, rw, rh = front_rect

    # Stack symbols to the upper-right area of the front view
    sx = rx + rw - 160
    sy = ry + 20

    for sym in symbols:
        stype = sym["type"]
        value = sym.get("value", "")

        if stype == "cylindricity":
            icon, label = "\u25cb", f"  {value}"   # ○
        elif stype == "flatness":
            icon, label = "\u25ad", f"  {value}"   # ▭
        elif stype == "position":
            icon, label = "\u2295", f"  {value}"   # ⊕
        elif stype == "surface_finish":
            icon, label = "\u2207\u2207", f" {value}"  # ∇∇
        else:
            icon, label = "?", f"  {value}"

        # Outer frame
        lines.append(
            f'  <rect x="{sx}" y="{sy}" width="140" height="20" '
            f'fill="#fffff8" stroke="#333" stroke-width="0.8"/>'
        )
        # Divider after icon cell (30px wide)
        lines.append(
            f'  <line x1="{sx+30}" y1="{sy}" x2="{sx+30}" y2="{sy+20}" '
            f'stroke="#333" stroke-width="0.8"/>'
        )
        # Icon
        lines.append(
            f'  <text x="{sx+15}" y="{sy+14}" text-anchor="middle" '
            f'font-size="12" fill="#1a1a8c">{_escape(icon)}</text>'
        )
        # Value
        lines.append(
            f'  <text x="{sx+35}" y="{sy+14}" '
            f'font-size="11" fill="#000">{_escape(label)}</text>'
        )

        sy += 24

    return lines


# ---------------------------------------------------------------------------
# Title block
# ---------------------------------------------------------------------------

def _title_block(
    x: float, y: float, w: float, h: float,
    part_id: str, params: dict,
) -> list[str]:
    """Return SVG elements for the title block."""
    lines: list[str] = []

    # Outer border
    lines.append(
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="white" stroke="black" stroke-width="1.5"/>'
    )

    # Header bar
    lines.append(
        f'  <rect x="{x}" y="{y}" width="{w}" height="22" '
        f'fill="#1a1a8c"/>'
    )
    lines.append(
        f'  <text x="{x + w/2}" y="{y+15}" text-anchor="middle" '
        f'font-size="13" fill="white" font-weight="bold">'
        f'ARIA-OS Engineering Drawing</text>'
    )

    today = date.today().isoformat()
    material = params.get("material", "\u2014")  # —

    rows = [
        ("PART ID",   part_id),
        ("MATERIAL",  str(material)),
        ("SCALE",     "1:1"),
        ("DATE",      today),
        ("DRAWN BY",  "ARIA-OS"),
        ("UNITS",     "mm"),
        ("TOLERANCE", "\u00b10.1mm general"),
    ]

    col_w = w / 2
    row_h = (h - 22) / ((len(rows) + 1) // 2)

    for i, (key, val) in enumerate(rows):
        col = i % 2
        row = i // 2
        cx = x + col * col_w
        cy = y + 22 + row * row_h

        # Cell border
        lines.append(
            f'  <rect x="{cx}" y="{cy}" width="{col_w}" height="{row_h}" '
            f'fill="none" stroke="#bbb" stroke-width="0.5"/>'
        )
        # Key label
        lines.append(
            f'  <text x="{cx+4}" y="{cy+10}" font-size="8" fill="#666">'
            f'{_escape(key)}</text>'
        )
        # Value
        lines.append(
            f'  <text x="{cx+4}" y="{cy+22}" font-size="11" fill="#000" font-weight="bold">'
            f'{_escape(str(val))}</text>'
        )

    return lines


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    """Escape special XML characters for safe SVG text content."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
