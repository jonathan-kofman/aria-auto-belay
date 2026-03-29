"""
dxf_exporter.py — headless DXF generation for civil engineering plans.

Entry point: generate_civil_dxf(description, state, discipline, output_path)

Uses ezdxf (already installed).  No GUI, no AutoCAD needed.
State standards are loaded from standards_library and applied automatically.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import ezdxf
    from ezdxf import units
    _EZDXF_AVAILABLE = True
except ImportError:
    _EZDXF_AVAILABLE = False

from aria_os.autocad.layer_manager import LAYER_DEFS, get_layer
from aria_os.autocad.standards_library import get_standard, get_pipe_design

# ── Output directory ───────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).parent.parent.parent
_OUT_DIR = _REPO_ROOT / "outputs" / "cad" / "dxf"


# ── DXF document setup ─────────────────────────────────────────────────────────

def _create_doc(units_type: str = "imperial") -> "ezdxf.document.Drawing":
    """Create a new DXF R2018 document with all civil layers pre-loaded."""
    # setup=["linetypes"] loads all standard AutoCAD linetypes (CENTER, DASHED, HIDDEN, etc.)
    doc = ezdxf.new("R2018", setup=["linetypes"])
    doc.header["$INSUNITS"] = 2 if units_type == "imperial" else 4  # feet or mm
    doc.header["$LUNITS"] = 2  # decimal
    doc.header["$ANGBASE"] = 0
    doc.header["$ANGDIR"] = 0  # CCW
    doc.header["$LTSCALE"] = 1.0

    # Create all civil engineering layers
    for name, props in LAYER_DEFS.items():
        if name not in doc.layers:
            layer = doc.layers.add(name)
            layer.color = props["color"]
            layer.linetype = props["linetype"]
            lw_val = _lineweight_to_dxf(props["lineweight"])
            layer.lineweight = lw_val
            layer.description = props.get("description", "")

    return doc



def _lineweight_to_dxf(lw_mm: float) -> int:
    """Map mm lineweight to DXF lineweight enum value."""
    table = {
        0.00: 0,   0.05: 5,   0.09: 9,   0.13: 13,
        0.15: 15,  0.18: 18,  0.20: 20,  0.25: 25,
        0.30: 30,  0.35: 35,  0.40: 40,  0.50: 50,
        0.53: 53,  0.60: 60,  0.70: 70,  0.80: 80,
        0.90: 90,  1.00: 100, 1.06: 106, 1.20: 120,
        1.40: 140, 1.58: 158, 2.00: 200, 2.11: 211,
    }
    closest = min(table.keys(), key=lambda k: abs(k - lw_mm))
    return table[closest]


# ── Discipline plan generators ─────────────────────────────────────────────────

def _generate_road_plan(msp: Any, std: dict, description: str) -> None:
    """
    Subdivision arterial street improvement plan.
    1,200 ft centerline STA 0+00 to STA 12+00, two 12' travel lanes,
    6' bike lane, 5' sidewalk each side, mountable curb & gutter.
    T-intersection at STA 6+00 with 30' curb return radii and turn-lane taper.
    """
    lane_w  = std.get("lane_width_ft", 12.0)
    n_lanes = std.get("lanes_min", 2)
    shldr_w = std.get("shoulder_width_ft", 8.0)
    row_w   = std.get("row_width_ft", 66.0)
    dspd    = std.get("design_speed_mph", 35)

    road_len  = 1200.0
    bike_w    = 6.0
    swalk_w   = 5.0
    half_pvmt = (lane_w * n_lanes) / 2.0   # half-width of travel lanes
    eop_y     = half_pvmt                  # edge of pavement offset from CL
    bike_y    = eop_y + bike_w
    sw_inner  = bike_y
    sw_outer  = sw_inner + swalk_w
    row_half  = row_w / 2.0

    # ── Centerline STA 0+00 to 12+00 ─────────────────────────────────────────
    msp.add_line((0, 0), (road_len, 0),
                 dxfattribs={"layer": "ROAD-CENTERLINE", "linetype": "CENTER"})

    # Station tick marks and labels every 100 ft
    for sta in range(0, 1300, 100):
        tick_h = 2.0
        msp.add_line((sta, -tick_h), (sta, tick_h),
                     dxfattribs={"layer": "ANNO-DIM"})
        sta_label = f"{sta // 100}+{sta % 100:02d}"
        msp.add_text(sta_label, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.15,
            "insert": (sta - 1.5, -(row_half + 3)),
        })

    # ── ROW lines ─────────────────────────────────────────────────────────────
    for sign in (+1, -1):
        msp.add_line((0, sign * row_half), (road_len, sign * row_half),
                     dxfattribs={"layer": "ROAD-ROW", "linetype": "DASHED"})

    # ── Edge of pavement lines ────────────────────────────────────────────────
    for sign in (+1, -1):
        msp.add_line((0, sign * eop_y), (road_len, sign * eop_y),
                     dxfattribs={"layer": "ROAD-EDGE"})

    # ── Bike lane stripe (6' from EOP) ────────────────────────────────────────
    for sign in (+1, -1):
        msp.add_line((0, sign * bike_y), (road_len, sign * bike_y),
                     dxfattribs={"layer": "ROAD-MARKING", "linetype": "DASHED"})
        msp.add_text("BIKE LANE", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.15,
            "insert": (50, sign * (eop_y + bike_w / 2) - 0.3),
        })

    # ── Sidewalk lines ────────────────────────────────────────────────────────
    for sign in (+1, -1):
        for y_off in (sw_inner, sw_outer):
            msp.add_line((0, sign * y_off), (road_len, sign * y_off),
                         dxfattribs={"layer": "ROAD-EDGE"})
        msp.add_text("5' SIDEWALK (TYP.)", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (20, sign * (sw_inner + swalk_w / 2) - 0.2),
        })

    # ── Centerline pavement marking ───────────────────────────────────────────
    dash_len, gap_len = 10.0, 30.0
    x = 0.0
    seg = 0
    while x < road_len:
        x_end = min(x + dash_len, road_len)
        msp.add_line((x, 0), (x_end, 0),
                     dxfattribs={"layer": "ROAD-MARKING"})
        x += dash_len + gap_len
        seg += 1

    # ── T-intersection at STA 6+00 ────────────────────────────────────────────
    int_x    = 600.0
    cross_len = 200.0
    taper_len = 100.0

    # Cross-street centerline (south leg only — T-intersection)
    msp.add_line((int_x, 0), (int_x, -(cross_len + row_half)),
                 dxfattribs={"layer": "ROAD-CENTERLINE", "linetype": "CENTER"})

    # Cross-street edge of pavement
    for sign in (+1, -1):
        msp.add_line(
            (int_x + sign * eop_y, -(row_half)),
            (int_x + sign * eop_y, -(cross_len + row_half)),
            dxfattribs={"layer": "ROAD-EDGE"},
        )

    # 30' curb return radii (arc approximated as polyline quadrant)
    r = 30.0
    for corner_cx, corner_cy, a_start, a_end in [
        (int_x - eop_y - r, -eop_y,  0,   90),
        (int_x + eop_y + r, -eop_y, 90,  180),
    ]:
        pts = []
        for deg in range(int(a_start), int(a_end) + 1, 5):
            rad = math.radians(deg)
            pts.append((corner_cx + r * math.cos(rad),
                        corner_cy + r * math.sin(rad)))
        if len(pts) >= 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer": "ROAD-EDGE"})

    msp.add_text("R=30' (TYP.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (int_x - eop_y - r - 8, -eop_y - 5),
    })

    # Turn-lane taper 100 LF west of intersection
    taper_start_x = int_x - taper_len
    msp.add_line((taper_start_x, eop_y),
                 (int_x - eop_y, eop_y + lane_w),
                 dxfattribs={"layer": "ROAD-MARKING", "linetype": "DASHED"})
    msp.add_text("TURN LANE TAPER (100 LF)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (taper_start_x, eop_y + lane_w + 1),
    })

    # Stop bar (cross-street approach)
    msp.add_line(
        (int_x - eop_y, -row_half),
        (int_x + eop_y, -row_half),
        dxfattribs={"layer": "ROAD-MARKING"},
    )
    msp.add_text("STOP BAR", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (int_x + eop_y + 2, -row_half),
    })

    # ── Design callout box ────────────────────────────────────────────────────
    bx, by = 900.0, row_half + 10
    msp.add_lwpolyline(
        [(bx, by), (bx + 110, by), (bx + 110, by + 18), (bx, by + 18), (bx, by)],
        dxfattribs={"layer": "ANNO-DIM"},
    )
    msp.add_text(f"DESIGN SPEED: {dspd} MPH", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15, "insert": (bx + 3, by + 12),
    })
    msp.add_text(f"LANE WIDTH: {lane_w:.0f}' (TYP.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15, "insert": (bx + 3, by + 7),
    })
    msp.add_text(f"ROW WIDTH: {row_w:.0f}'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15, "insert": (bx + 3, by + 2),
    })

    # ── General notes block ───────────────────────────────────────────────────
    notes_x, notes_y = 0.0, -(row_half + 20)
    msp.add_text("GENERAL NOTES:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (notes_x, notes_y),
    })
    notes = [
        "1. ALL PAVEMENT MARKINGS PER MUTCD.",
        "2. CURB RETURN RADIUS = 30'.",
        "3. ADA RAMPS AT ALL CORNERS (TYP.).",
        f"4. MOUNTABLE CURB & GUTTER EACH SIDE OF ROADWAY.",
        f"5. SEE TYPICAL SECTION FOR ADDITIONAL PAVEMENT DETAILS.",
    ]
    for i, note in enumerate(notes):
        msp.add_text(note, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": (notes_x, notes_y - 2.5 - i * 2.0),
        })

    # ── Title and north arrow ─────────────────────────────────────────────────
    msp.add_text("ROAD IMPROVEMENT PLAN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.30,
        "insert": (400, -(row_half + 50)),
    })
    msp.add_text("SCALE: 1\"=50'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (400, -(row_half + 55)),
    })
    # North arrow (simple)
    na_x, na_y = road_len + 20, 30
    msp.add_line((na_x, na_y - 10), (na_x, na_y + 10),
                 dxfattribs={"layer": "ANNO-TEXT"})
    msp.add_text("N", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (na_x - 1, na_y + 11),
    })


def _generate_drainage_plan(msp: Any, std: dict, description: str) -> None:
    """
    Site storm drainage plan with CEM-derived pipe sizing.
    500 LF trunk, 4 curb inlets CI-1..CI-4, MH-1..MH-4 with rim/invert,
    detention pond, outfall protection note.
    """
    from aria_os.autocad.civil_elements import (
        add_storm_pipe, add_inlet, add_manhole, add_detention_pond,
        add_north_arrow, add_title_block
    )

    design_storm = std.get("design_storm_minor_year", std.get("design_storm_yr", 10))
    min_cover    = std.get("min_pipe_cover_ft", 2.0)
    pipe_size    = std.get("min_culvert_dia_in", std.get("min_pipe_dia_storm_in", 18.0))

    # Trunk: MH-1 (0,0) → MH-2 (150,0) → MH-3 (300,0) → MH-4 (500,0)
    mh_coords = [(0, 0), (150, 0), (300, 0), (500, 0)]
    # Rim and invert elevations (representative, decreasing)
    mh_data = [
        {"label": "MH-1", "rim": 104.25, "inv": 99.50},
        {"label": "MH-2", "rim": 104.10, "inv": 99.20},
        {"label": "MH-3", "rim": 103.90, "inv": 98.87},
        {"label": "MH-4", "rim": 103.65, "inv": 98.50},
    ]

    # Draw trunk pipe runs
    pipe_labels = [
        f"{int(pipe_size)}\" RCP @ 0.20%",
        f"{int(pipe_size)}\" RCP @ 0.22%",
        f"{int(pipe_size)}\" RCP @ 0.25%",
    ]
    for idx in range(len(mh_coords) - 1):
        x0, y0 = mh_coords[idx]
        x1, y1 = mh_coords[idx + 1]
        msp.add_line((x0, y0), (x1, y1),
                     dxfattribs={"layer": "UTIL-STORM"})
        mid_x = (x0 + x1) / 2
        msp.add_text(pipe_labels[idx], dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (mid_x - 15, 2.5),
        })

    # Draw manholes with rim/invert callouts
    for mh, (mx, my) in zip(mh_data, mh_coords):
        # Manhole circle
        msp.add_circle((mx, my), 3.0,
                        dxfattribs={"layer": "UTIL-STORM"})
        msp.add_text(mh["label"], dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": (mx - 4, my + 4),
        })
        msp.add_text(f"RIM={mh['rim']:.2f} / INV={mh['inv']:.2f}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (mx - 12, my - 6),
        })

    # 4 curb inlets CI-1..CI-4, spaced ~100-120 LF apart along north side
    ci_x_positions = [50, 150, 300, 420]
    ci_elevs       = [104.18, 104.10, 103.92, 103.75]
    for ci_idx, (ci_x, ci_rim) in enumerate(zip(ci_x_positions, ci_elevs), start=1):
        # Lateral from inlet down to trunk
        msp.add_line((ci_x, 30), (ci_x, 0),
                     dxfattribs={"layer": "UTIL-STORM"})
        # Inlet box
        msp.add_lwpolyline(
            [(ci_x - 3, 30), (ci_x + 3, 30),
             (ci_x + 3, 36), (ci_x - 3, 36), (ci_x - 3, 30)],
            dxfattribs={"layer": "UTIL-STORM"},
        )
        msp.add_text(f"CI-{ci_idx}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": (ci_x - 2, 37),
        })
        msp.add_text(f"RIM={ci_rim:.2f}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (ci_x - 8, 28),
        })

    # Outfall at MH-4 — pipe runs south
    msp.add_line((500, 0), (500, -100),
                 dxfattribs={"layer": "UTIL-STORM"})
    msp.add_text("OUTFALL", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (503, -50),
    })
    msp.add_text("RIPRAP APRON PER DETAIL 3/C-5, CLASS B, 8' WIDE x 12' LONG", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (510, -110),
    })

    # Detention pond
    pond_cx, pond_cy = 500, -230
    msp.add_ellipse((pond_cx, pond_cy), major_axis=(80, 0), ratio=0.5,
                    dxfattribs={"layer": "UTIL-STORM"})
    msp.add_text("DETENTION POND", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (pond_cx - 30, pond_cy + 5),
    })
    msp.add_text("WSE = 101.50", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (pond_cx - 20, pond_cy - 8),
    })
    msp.add_text("EMERG. SPILLWAY ELEV = 102.00", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (pond_cx - 35, pond_cy - 15),
    })

    # ── General notes ─────────────────────────────────────────────────────────
    notes_x, notes_y = -100.0, -20.0
    msp.add_text("DRAINAGE NOTES:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (notes_x, notes_y),
    })
    notes = [
        f"1. DESIGN STORM: {design_storm}-YR / 100-YR SHOWN FOR REFERENCE.",
        f"2. MIN PIPE COVER: {min_cover:.1f}' PER STATE DOT.",
        "3. ALL STORM PIPE: HDPE ASTM F2306 OR RCP ASTM C76 CLASS III.",
        "4. PIPE SLOPES AND SIZES ARE MINIMUM; CONTRACTOR TO VERIFY.",
    ]
    for i, note in enumerate(notes):
        msp.add_text(note, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (notes_x, notes_y - 3 - i * 2.2),
        })

    # ── Title ─────────────────────────────────────────────────────────────────
    msp.add_text("STORM DRAINAGE PLAN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.30,
        "insert": (150, -50),
    })
    msp.add_text("SCALE: 1\"=40'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (150, -56),
    })
    # North arrow
    na_x, na_y = 580, 60
    msp.add_line((na_x, na_y - 10), (na_x, na_y + 10),
                 dxfattribs={"layer": "ANNO-TEXT"})
    msp.add_text("N", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (na_x - 1, na_y + 11),
    })


def _generate_grading_plan(msp: Any, std: dict, description: str) -> None:
    """
    Commercial pad grading plan, 300' x 200' site.
    Existing 2' contours (index every 10'), proposed graded pad at FFE=112.50,
    slope arrows, retaining wall, spot elevations, benchmark, general notes.
    """
    site_w, site_h = 300.0, 200.0
    ffe = 112.50

    # ── Site boundary ─────────────────────────────────────────────────────────
    msp.add_lwpolyline(
        [(0, 0), (site_w, 0), (site_w, site_h), (0, site_h), (0, 0)],
        dxfattribs={"layer": "PROP-BOUNDARY"},
    )
    msp.add_text("SITE BOUNDARY", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (site_w / 2 - 15, -5),
    })

    # ── Existing contours (2' interval, index every 10', elev 100–120) ────────
    for elev in range(100, 122, 2):
        is_index = (elev % 10 == 0)
        # Undulating polyline across site
        t = (elev - 100) / 20.0  # 0..1
        base_y = t * site_h
        # Add some undulation
        pts = []
        n_seg = 8
        for seg in range(n_seg + 1):
            x = seg * site_w / n_seg
            wave = 8.0 * math.sin(math.pi * seg / n_seg * 2.5 + t * math.pi)
            y = base_y + wave
            y = max(0.0, min(site_h, y))
            pts.append((x, y))
        layer = "GRAD-EXIST-INDEX" if is_index else "GRAD-EXIST"
        # Use dashed for existing; index contours get normal existing layer
        lt = "Continuous" if is_index else "DASHED"
        try:
            msp.add_lwpolyline(pts, dxfattribs={"layer": layer, "linetype": lt})
        except Exception:
            msp.add_lwpolyline(pts, dxfattribs={"layer": layer})
        # Label index contours
        if is_index and len(pts) > 2:
            lx, ly = pts[len(pts) // 2]
            msp.add_text(f"{elev:.0f}", dxfattribs={
                "layer": "ANNO-TEXT", "height": 0.10,
                "insert": (lx + 1, ly + 0.5),
            })

    # ── Building pad boundary (80' x 100' centered, approx) ──────────────────
    pad_x0, pad_y0 = 100.0, 60.0
    pad_w, pad_d   = 100.0, 80.0
    msp.add_lwpolyline(
        [(pad_x0, pad_y0), (pad_x0 + pad_w, pad_y0),
         (pad_x0 + pad_w, pad_y0 + pad_d), (pad_x0, pad_y0 + pad_d),
         (pad_x0, pad_y0)],
        dxfattribs={"layer": "GRAD-LIMIT"},
    )
    msp.add_text(f"BUILDING PAD", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (pad_x0 + 20, pad_y0 + pad_d / 2),
    })
    msp.add_text(f"FFE = {ffe:.2f}", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (pad_x0 + 25, pad_y0 + pad_d / 2 - 3),
    })

    # ── Proposed contours (dashed) around graded pad ──────────────────────────
    for elev_off, dist in [(0.5, 10), (1.0, 20), (1.5, 30), (2.0, 45)]:
        prop_elev = ffe - elev_off
        expand = dist
        px0 = max(0, pad_x0 - expand)
        py0 = max(0, pad_y0 - expand)
        px1 = min(site_w, pad_x0 + pad_w + expand)
        py1 = min(site_h, pad_y0 + pad_d + expand)
        pts_prop = [
            (px0, py0), (px1, py0), (px1, py1), (px0, py1), (px0, py0)
        ]
        try:
            msp.add_lwpolyline(pts_prop, dxfattribs={"layer": "GRAD-PROP", "linetype": "DASHED"})
        except Exception:
            msp.add_lwpolyline(pts_prop, dxfattribs={"layer": "GRAD-PROP"})
        msp.add_text(f"{prop_elev:.1f}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.08,
            "insert": (px1 + 1, (py0 + py1) / 2),
        })

    # ── Slope arrows (2% away from building in all four directions) ───────────
    arrow_data = [
        (pad_x0 + pad_w / 2, pad_y0 + pad_d, pad_x0 + pad_w / 2, pad_y0 + pad_d + 25, "2.0%"),
        (pad_x0 + pad_w / 2, pad_y0, pad_x0 + pad_w / 2, pad_y0 - 25, "2.0%"),
        (pad_x0, pad_y0 + pad_d / 2, pad_x0 - 25, pad_y0 + pad_d / 2, "2.0%"),
        (pad_x0 + pad_w, pad_y0 + pad_d / 2, pad_x0 + pad_w + 25, pad_y0 + pad_d / 2, "2.0%"),
    ]
    for ax0, ay0, ax1, ay1, pct in arrow_data:
        msp.add_line((ax0, ay0), (ax1, ay1),
                     dxfattribs={"layer": "GRAD-SLOPE-ARROW"})
        # Arrowhead approximation
        angle = math.atan2(ay1 - ay0, ax1 - ax0)
        ah_len = 3.0
        for side in (+0.4, -0.4):
            msp.add_line(
                (ax1, ay1),
                (ax1 - ah_len * math.cos(angle + side),
                 ay1 - ah_len * math.sin(angle + side)),
                dxfattribs={"layer": "GRAD-SLOPE-ARROW"},
            )
        msp.add_text(pct, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": ((ax0 + ax1) / 2 + 1, (ay0 + ay1) / 2 + 1),
        })

    # ── Retaining wall (north property line, where cut > 4') ─────────────────
    msp.add_line((0, site_h - 5), (site_w, site_h - 5),
                 dxfattribs={"layer": "GRAD-RETAIN-WALL"})
    msp.add_text("RETAINING WALL (CUT > 4')", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (site_w / 2 - 30, site_h - 3),
    })

    # ── Limits of disturbance (heavy dashed) ─────────────────────────────────
    lod_margin = 20.0
    lod_pts = [
        (-lod_margin, -lod_margin), (site_w + lod_margin, -lod_margin),
        (site_w + lod_margin, site_h + lod_margin), (-lod_margin, site_h + lod_margin),
        (-lod_margin, -lod_margin),
    ]
    try:
        msp.add_lwpolyline(lod_pts, dxfattribs={"layer": "GRAD-LIMIT", "linetype": "DASHED"})
    except Exception:
        msp.add_lwpolyline(lod_pts, dxfattribs={"layer": "GRAD-LIMIT"})
    msp.add_text("LIMITS OF DISTURBANCE (TYP.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (site_w + lod_margin + 2, site_h / 2),
    })

    # ── Spot elevations ───────────────────────────────────────────────────────
    spots = [
        (pad_x0, pad_y0, ffe),
        (pad_x0 + pad_w, pad_y0, ffe),
        (pad_x0, pad_y0 + pad_d, ffe),
        (pad_x0 + pad_w, pad_y0 + pad_d, ffe),
        (10, 10, 100.5),
        (site_w - 10, 10, 101.2),
        (10, site_h - 10, 118.8),
        (site_w - 10, site_h - 10, 119.4),
        (pad_x0 - 30, pad_y0 - 15, ffe - 2.5),   # parking low point
    ]
    for sx, sy, se in spots:
        msp.add_circle((sx, sy), 1.0,
                        dxfattribs={"layer": "ANNO-DIM"})
        msp.add_text(f"{se:.2f}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (sx + 1.5, sy - 0.5),
        })

    # ── Benchmark callout ─────────────────────────────────────────────────────
    bm_x, bm_y = site_w + 30, site_h - 20
    msp.add_text("BENCHMARK:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15, "insert": (bm_x, bm_y),
    })
    msp.add_text("N: 1,234,567.89  E: 456,789.01", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10, "insert": (bm_x, bm_y - 3),
    })
    msp.add_text("ELEV: 105.000 (NAVD 88)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10, "insert": (bm_x, bm_y - 6),
    })

    # ── General notes ─────────────────────────────────────────────────────────
    notes_x, notes_y = 0.0, -30.0
    msp.add_text("GRADING NOTES:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (notes_x, notes_y),
    })
    notes = [
        "1. FINISH FLOOR ELEVATION = 112.50 NAVD88.",
        "2. ALL SLOPES TO DRAIN AWAY FROM BUILDING.",
        "3. MAX SLOPE IN PAVED AREAS: 5% (MIN 1%).",
        "4. CONTRACTOR TO VERIFY EXISTING GRADES PRIOR TO CONSTRUCTION.",
    ]
    for i, note in enumerate(notes):
        msp.add_text(note, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (notes_x, notes_y - 3 - i * 2.2),
        })

    # ── Title ─────────────────────────────────────────────────────────────────
    msp.add_text("GRADING PLAN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.30,
        "insert": (site_w / 2 - 25, -55),
    })
    msp.add_text("SCALE: 1\"=20'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (site_w / 2 - 15, -61),
    })
    # North arrow
    na_x, na_y = site_w + 30, 20
    msp.add_line((na_x, na_y - 10), (na_x, na_y + 10),
                 dxfattribs={"layer": "ANNO-TEXT"})
    msp.add_text("N", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (na_x - 1, na_y + 11),
    })


def _generate_utilities_plan(msp: Any, std: dict, description: str) -> None:
    """
    New development utility extension, 500 LF corridor.
    8\" water main, 8\" gravity sewer, 4\" gas, 2\" electric conduit,
    crossing conflict at STA 2+50, hydrant, meter vault, service laterals.
    """
    run_len = 500.0
    # Y-offsets for each utility (all running east-west)
    water_y   =  15.0
    sewer_y   =   0.0
    gas_y     = -10.0
    elec_y    = -15.0

    # ── Water main (8") ───────────────────────────────────────────────────────
    msp.add_line((0, water_y), (run_len, water_y),
                 dxfattribs={"layer": "UTIL-WATER"})
    msp.add_text("8\" DIP CL350 WATER MAIN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5, water_y + 2),
    })

    # Gate valves every 500 LF (one at sta 0 and one at 500)
    for gv_x in (0, run_len):
        msp.add_circle((gv_x, water_y), 2.5,
                        dxfattribs={"layer": "UTIL-WATER"})
        msp.add_text("GV", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (gv_x - 2, water_y + 3),
        })

    # Fire hydrant at STA 2+50
    fh_x = 250.0
    msp.add_circle((fh_x, water_y + 5), 3.0,
                    dxfattribs={"layer": "UTIL-WATER"})
    msp.add_line((fh_x, water_y), (fh_x, water_y + 5),
                 dxfattribs={"layer": "UTIL-WATER"})
    msp.add_text("FH-1", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (fh_x + 3, water_y + 6),
    })
    msp.add_text("FH ASSEMBLY W/ 6\" GATE VALVE, BREAK-AWAY FLANGE", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.08,
        "insert": (fh_x + 5, water_y + 3),
    })

    # Hydrants every 250 LF
    msp.add_circle((0, water_y + 5), 3.0, dxfattribs={"layer": "UTIL-WATER"})
    msp.add_text("FH-2", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (3, water_y + 6),
    })

    # ── Sewer (8" gravity, 4% max slope) ─────────────────────────────────────
    msp.add_line((0, sewer_y), (run_len, sewer_y),
                 dxfattribs={"layer": "UTIL-SEWER"})
    msp.add_text("8\" SDR-35 PVC GRAVITY SEWER @ 0.40% MIN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5, sewer_y + 2),
    })

    # Sewer manholes at 0, 300 LF
    smh_data = [
        (0,   "SMH-1", 103.50, 99.00),
        (300, "SMH-2", 103.20, 97.80),
        (run_len, "SMH-3", 103.00, 97.20),
    ]
    for smh_x, smh_lbl, smh_rim, smh_inv in smh_data:
        msp.add_circle((smh_x, sewer_y), 3.0,
                        dxfattribs={"layer": "UTIL-SEWER"})
        msp.add_text(smh_lbl, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": (smh_x - 4, sewer_y - 6),
        })
        msp.add_text(f"RIM={smh_rim:.2f} / INV={smh_inv:.2f}", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (smh_x - 12, sewer_y - 9),
        })

    # Service lateral stubs every 50 LF (dashed, 4" dia)
    for lat_x in range(50, int(run_len), 50):
        try:
            msp.add_line((lat_x, sewer_y), (lat_x, sewer_y - 12),
                         dxfattribs={"layer": "UTIL-SEWER", "linetype": "DASHED"})
        except Exception:
            msp.add_line((lat_x, sewer_y), (lat_x, sewer_y - 12),
                         dxfattribs={"layer": "UTIL-SEWER"})
        msp.add_text("4\"", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.08,
            "insert": (lat_x + 0.5, sewer_y - 6),
        })

    # ── Gas main (4") — 10' min horizontal separation ────────────────────────
    msp.add_line((0, gas_y), (run_len, gas_y),
                 dxfattribs={"layer": "UTIL-GAS"})
    msp.add_text("4\" STEEL GAS MAIN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5, gas_y - 2),
    })
    msp.add_text(f"HORIZ. SEP.: {abs(sewer_y - gas_y):.0f}' MIN (GAS TO SEWER)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.08,
        "insert": (200, gas_y - 3),
    })

    # ── Electric conduit (2") — 5' min from gas ──────────────────────────────
    msp.add_line((0, elec_y), (run_len, elec_y),
                 dxfattribs={"layer": "UTIL-ELECTRIC"})
    msp.add_text("2\" ELEC. CONDUIT", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5, elec_y - 2),
    })
    msp.add_text(f"HORIZ. SEP.: {abs(gas_y - elec_y):.0f}' MIN (ELEC. TO GAS)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.08,
        "insert": (200, elec_y - 3),
    })

    # ── Crossing conflict STA 2+50: sewer over water ──────────────────────────
    cross_x = 250.0
    # Crossing marker (X symbol)
    d = 4.0
    msp.add_line((cross_x - d, sewer_y - d), (cross_x + d, water_y + d),
                 dxfattribs={"layer": "UTIL-CROSSING"})
    msp.add_line((cross_x - d, water_y + d), (cross_x + d, sewer_y - d),
                 dxfattribs={"layer": "UTIL-CROSSING"})
    msp.add_text("CROSSING", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (cross_x + 5, (sewer_y + water_y) / 2 + 2),
    })
    msp.add_text("WATER MAIN DEFLECTS DOWN 18\" MIN VERTICAL CLEARANCE AT CROSSING", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.08,
        "insert": (cross_x + 5, (sewer_y + water_y) / 2 - 2),
    })

    # ── Meter vault MV-1 near end ─────────────────────────────────────────────
    mv_x = 460.0
    msp.add_lwpolyline(
        [(mv_x - 4, water_y - 4), (mv_x + 4, water_y - 4),
         (mv_x + 4, water_y + 4), (mv_x - 4, water_y + 4),
         (mv_x - 4, water_y - 4)],
        dxfattribs={"layer": "UTIL-WATER"},
    )
    msp.add_text("MV-1", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (mv_x - 2, water_y + 5),
    })

    # ── General notes ─────────────────────────────────────────────────────────
    notes_x, notes_y = 0.0, elec_y - 20.0
    msp.add_text("UTILITY NOTES:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (notes_x, notes_y),
    })
    notes = [
        "1. MIN HORIZONTAL SEPARATION WATER/SEWER: 10'-0\" (AWWA C600).",
        "2. 18\" MIN VERTICAL CLEARANCE AT CROSSINGS.",
        "3. ALL WATER MAIN: DIP CLASS 350 OR PVC C-900 DR-18.",
        "4. ALL SEWER: SDR-35 PVC ASTM D3034.",
    ]
    for i, note in enumerate(notes):
        msp.add_text(note, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (notes_x, notes_y - 3 - i * 2.2),
        })

    # ── Title ─────────────────────────────────────────────────────────────────
    msp.add_text("UTILITY PLAN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.30,
        "insert": (200, elec_y - 60),
    })
    msp.add_text("SCALE: 1\"=50'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (200, elec_y - 66),
    })
    # North arrow
    na_x, na_y = run_len + 20, 30
    msp.add_line((na_x, na_y - 10), (na_x, na_y + 10),
                 dxfattribs={"layer": "ANNO-TEXT"})
    msp.add_text("N", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (na_x - 1, na_y + 11),
    })


def _generate_site_plan(msp: Any, std: dict, description: str) -> None:
    """
    Commercial site plan for a 1-acre lot (200' x 218').
    Property boundary with bearings, setbacks, 80'x120' building, parking field
    (32 standard + 2 ADA), ADA route, loading zone, dumpster enclosure,
    bike parking, site lighting, storm inlet, zoning compliance notes.
    """
    lot_w, lot_d = 200.0, 218.0   # feet

    # ── Property boundary with bearings ───────────────────────────────────────
    corners = [(0, 0), (lot_w, 0), (lot_w, lot_d), (0, lot_d), (0, 0)]
    msp.add_lwpolyline(corners, dxfattribs={"layer": "PROP-BOUNDARY"})
    bearings = [
        (lot_w / 2, -4, "N 89°14'32\" E  200.00'"),
        (lot_w + 2, lot_d / 2, "N 00°45'28\" W  218.00'"),
        (lot_w / 2, lot_d + 2, "S 89°14'32\" W  200.00'"),
        (-45, lot_d / 2, "S 00°45'28\" E  218.00'"),
    ]
    for bx, by, bearing in bearings:
        msp.add_text(bearing, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.12,
            "insert": (bx, by),
        })

    # ── Setback lines ─────────────────────────────────────────────────────────
    setback_data = [
        (25, "FRONT SETBACK (25')"),   # south (front) — y offset from bottom
        (10, "REAR SETBACK (10')"),    # north — y from top, but draw as from top
    ]
    # Front setback
    try:
        msp.add_line((0, 25), (lot_w, 25),
                     dxfattribs={"layer": "PROP-SETBACK", "linetype": "DASHED"})
    except Exception:
        msp.add_line((0, 25), (lot_w, 25),
                     dxfattribs={"layer": "PROP-SETBACK"})
    msp.add_text("25' FRONT SETBACK", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12, "insert": (2, 27),
    })
    # Rear setback
    try:
        msp.add_line((0, lot_d - 10), (lot_w, lot_d - 10),
                     dxfattribs={"layer": "PROP-SETBACK", "linetype": "DASHED"})
    except Exception:
        msp.add_line((0, lot_d - 10), (lot_w, lot_d - 10),
                     dxfattribs={"layer": "PROP-SETBACK"})
    msp.add_text("10' REAR SETBACK", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12, "insert": (2, lot_d - 8),
    })
    # Side setbacks (5' each side)
    for sx, label in [(5, "5' SIDE SETBACK"), (lot_w - 5, "5' SIDE SETBACK")]:
        try:
            msp.add_line((sx, 0), (sx, lot_d),
                         dxfattribs={"layer": "PROP-SETBACK", "linetype": "DASHED"})
        except Exception:
            msp.add_line((sx, 0), (sx, lot_d),
                         dxfattribs={"layer": "PROP-SETBACK"})
    msp.add_text("5' SIDE SETBACK (TYP.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10, "insert": (6, lot_d / 2),
    })

    # ── Building footprint (80' x 120' centered on pad) ───────────────────────
    bldg_w, bldg_d = 80.0, 120.0
    bldg_x0 = (lot_w - bldg_w) / 2
    bldg_y0 = (lot_d - bldg_d) / 2 + 15   # slightly south of center
    msp.add_lwpolyline(
        [(bldg_x0, bldg_y0), (bldg_x0 + bldg_w, bldg_y0),
         (bldg_x0 + bldg_w, bldg_y0 + bldg_d), (bldg_x0, bldg_y0 + bldg_d),
         (bldg_x0, bldg_y0)],
        dxfattribs={"layer": "BLDG-FOOTPRINT"},
    )
    msp.add_text("PROPOSED BUILDING", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (bldg_x0 + 10, bldg_y0 + bldg_d / 2 + 3),
    })
    msp.add_text(u"\u00b19,600 SF", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (bldg_x0 + 18, bldg_y0 + bldg_d / 2 - 3),
    })

    # ── Parking field ─────────────────────────────────────────────────────────
    # 32 standard stalls (9'x18') in two rows along south portion
    stall_w, stall_d = 9.0, 18.0
    row1_y = 30.0   # first row, face of stall at y=30, backs at y=48
    row2_y = 30.0 + stall_d + 24.0   # drive aisle 24', then second row
    for row_y in (row1_y, row2_y):
        for col in range(16):
            sx = 5.0 + col * stall_w
            if sx + stall_w > lot_w - 5:
                break
            msp.add_lwpolyline(
                [(sx, row_y), (sx + stall_w, row_y),
                 (sx + stall_w, row_y + stall_d), (sx, row_y + stall_d),
                 (sx, row_y)],
                dxfattribs={"layer": "SITE-PARKING"},
            )

    msp.add_text("32 STANDARD + 2 ADA = 34 PROVIDED (32 REQUIRED)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5, row2_y + stall_d + 2),
    })

    # ADA stalls (2 van-accessible, 8'+5' access aisle) at west end
    ada_x = 5.0
    ada_y = row1_y
    for i in range(2):
        msp.add_lwpolyline(
            [(ada_x, ada_y), (ada_x + 8, ada_y),
             (ada_x + 8, ada_y + stall_d), (ada_x, ada_y + stall_d),
             (ada_x, ada_y)],
            dxfattribs={"layer": "SITE-ADA"},
        )
        # 5' access aisle
        msp.add_lwpolyline(
            [(ada_x + 8, ada_y), (ada_x + 13, ada_y),
             (ada_x + 13, ada_y + stall_d), (ada_x + 8, ada_y + stall_d),
             (ada_x + 8, ada_y)],
            dxfattribs={"layer": "SITE-ADA"},
        )
        msp.add_text("ADA VAN", dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (ada_x + 0.5, ada_y + stall_d / 2),
        })
        ada_x += 13 + 9   # shift for next ADA stall

    # ── ADA accessible route ──────────────────────────────────────────────────
    # From ADA stalls to building entrance
    ada_route = [
        (5 + 6, row1_y + stall_d),
        (5 + 6, bldg_y0),
        (bldg_x0 + bldg_w / 2, bldg_y0),
    ]
    msp.add_lwpolyline(ada_route, dxfattribs={"layer": "SITE-ADA"})
    msp.add_text("ACCESSIBLE ROUTE", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (5 + 8, row1_y + stall_d + 10),
    })

    # ── Loading zone (12'x35' at rear) ───────────────────────────────────────
    lz_x0 = lot_w - 40.0
    lz_y0 = lot_d - 10 - 35
    msp.add_lwpolyline(
        [(lz_x0, lz_y0), (lz_x0 + 35, lz_y0),
         (lz_x0 + 35, lz_y0 + 12), (lz_x0, lz_y0 + 12),
         (lz_x0, lz_y0)],
        dxfattribs={"layer": "SITE-LOADING"},
    )
    msp.add_text("LOADING ZONE", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.12,
        "insert": (lz_x0 + 3, lz_y0 + 7),
    })
    msp.add_text("NO PARKING", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (lz_x0 + 5, lz_y0 + 3),
    })

    # ── Dumpster enclosure (12'x20') ─────────────────────────────────────────
    de_x0, de_y0 = lot_w - 30.0, lot_d - 40.0
    msp.add_lwpolyline(
        [(de_x0, de_y0), (de_x0 + 20, de_y0),
         (de_x0 + 20, de_y0 + 12), (de_x0, de_y0 + 12),
         (de_x0, de_y0)],
        dxfattribs={"layer": "SITE-MISC"},
    )
    msp.add_text("DUMPSTER\nENCL.", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (de_x0 + 2, de_y0 + 5),
    })

    # ── Bicycle parking (6-space rack near entrance) ─────────────────────────
    bp_x, bp_y = bldg_x0 + bldg_w + 5, bldg_y0 + 5
    msp.add_lwpolyline(
        [(bp_x, bp_y), (bp_x + 10, bp_y),
         (bp_x + 10, bp_y + 5), (bp_x, bp_y + 5), (bp_x, bp_y)],
        dxfattribs={"layer": "SITE-MISC"},
    )
    msp.add_text("BIKE PARKING\n(6 SPACES)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (bp_x + 1, bp_y + 6),
    })

    # ── Site lighting (4 pole lights in parking lot) ──────────────────────────
    light_positions = [
        (lot_w / 4, row1_y + stall_d + 12),
        (3 * lot_w / 4, row1_y + stall_d + 12),
        (lot_w / 4, row2_y + stall_d + 5),
        (3 * lot_w / 4, row2_y + stall_d + 5),
    ]
    for lx, ly in light_positions:
        msp.add_circle((lx, ly), 2.0, dxfattribs={"layer": "SITE-LIGHT"})
        msp.add_line((lx, ly - 2), (lx, ly + 2),
                     dxfattribs={"layer": "SITE-LIGHT"})
        msp.add_line((lx - 2, ly), (lx + 2, ly),
                     dxfattribs={"layer": "SITE-LIGHT"})

    msp.add_text("25' LIGHT POLE W/ 400W LED (TYP.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (light_positions[0][0] + 3, light_positions[0][1] + 3),
    })

    # ── Storm inlet in parking lot low point ─────────────────────────────────
    si_x, si_y = lot_w / 2, row1_y + stall_d + 5
    msp.add_lwpolyline(
        [(si_x - 2, si_y - 2), (si_x + 2, si_y - 2),
         (si_x + 2, si_y + 2), (si_x - 2, si_y + 2),
         (si_x - 2, si_y - 2)],
        dxfattribs={"layer": "UTIL-STORM"},
    )
    msp.add_text("STORM INLET\n(LOW PT.)", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.10,
        "insert": (si_x + 3, si_y),
    })

    # ── General notes ─────────────────────────────────────────────────────────
    notes_x, notes_y = 0.0, -20.0
    msp.add_text("SITE NOTES:", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (notes_x, notes_y),
    })
    notes = [
        "1. ZONING: C-2 COMMERCIAL.",
        "2. LOT AREA: 43,560 SF (1.00 AC).",
        "3. IMPERVIOUS COVER: 28,400 SF (65.2% — MAX ALLOWED 75%).",
        "4. REQUIRED PARKING: 1 SPACE PER 300 SF GFA = 32 SPACES.",
    ]
    for i, note in enumerate(notes):
        msp.add_text(note, dxfattribs={
            "layer": "ANNO-TEXT", "height": 0.10,
            "insert": (notes_x, notes_y - 3 - i * 2.2),
        })

    # ── Title ─────────────────────────────────────────────────────────────────
    msp.add_text("SITE PLAN", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.30,
        "insert": (lot_w / 2 - 15, -50),
    })
    msp.add_text("SCALE: 1\"=30'", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.15,
        "insert": (lot_w / 2 - 12, -56),
    })
    # North arrow
    na_x, na_y = lot_w + 15, lot_d - 20
    msp.add_line((na_x, na_y - 10), (na_x, na_y + 10),
                 dxfattribs={"layer": "ANNO-TEXT"})
    msp.add_text("N", dxfattribs={
        "layer": "ANNO-TEXT", "height": 0.20, "insert": (na_x - 1, na_y + 11),
    })


def _generate_grading_and_drainage(msp: Any, std: dict, description: str) -> None:
    """Combined grading + drainage plan."""
    _generate_grading_plan(msp, std, description)
    _generate_drainage_plan(msp, std, description)


_DISCIPLINE_GENERATORS = {
    "transportation": _generate_road_plan,
    "road":           _generate_road_plan,
    "drainage":       _generate_drainage_plan,
    "grading":        _generate_grading_plan,
    "utilities":      _generate_utilities_plan,
    "utility":        _generate_utilities_plan,
    "site":           _generate_site_plan,
    "grading_drainage": _generate_grading_and_drainage,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_civil_dxf(
    description: str,
    state: str = "national",
    discipline: str | None = None,
    output_path: str | Path | None = None,
    units_type: str = "imperial",
    drawn_by: str = "",
    project: str = "",
    date: str | None = None,
    view_after: bool = False,
) -> Path:
    """
    Generate a headless civil engineering DXF file.

    Parameters
    ----------
    description : str
        Natural-language description of the plan content.
    state : str
        2-letter US state code (e.g. "TX") or "national" for AASHTO defaults.
    discipline : str | None
        Civil discipline: "transportation", "drainage", "grading", "utilities",
        "site", or None to auto-detect from description.
    output_path : str | Path | None
        Where to write the .dxf file.  Auto-generated if None.
    units_type : str
        "imperial" (default) or "metric".
    drawn_by : str
        Designer initials / name for title block.
    project : str
        Project name / number for title block.
    date : str | None
        Date string; defaults to today.
    view_after : bool
        When True, launch the ezdxf viewer after saving the DXF.

    Returns
    -------
    Path
        Absolute path to the written DXF file.
    """
    if not _EZDXF_AVAILABLE:
        raise ImportError(
            "ezdxf is required for DXF generation. "
            "Install it with: pip install ezdxf"
        )

    # Resolve discipline
    if discipline is None:
        discipline = _detect_discipline(description)

    # Load applicable standards
    std = get_standard(state.upper(), discipline)

    # Build output path
    if output_path is None:
        slug = re.sub(r"[^a-z0-9_]+", "_",
                      f"{state}_{discipline}".lower()).strip("_")
        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _OUT_DIR / f"{slug}.dxf"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create DXF document
    doc = _create_doc(units_type)
    msp = doc.modelspace()

    # Add custom properties / metadata
    doc.set_modelspace_vport(height=500, center=(200, 100))

    # Run discipline generator
    gen_fn = _DISCIPLINE_GENERATORS.get(discipline.lower().replace(" ", "_"))
    if gen_fn is None:
        gen_fn = _generate_site_plan  # safe default

    date_str = date or datetime.now().strftime("%Y-%m-%d")
    gen_fn(msp, std, description)

    # Inject standards note as text
    _add_standards_note(msp, std, state)

    # Save
    doc.saveas(str(output_path))

    # Write sidecar JSON (standards applied + metadata)
    meta_path = output_path.with_suffix(".json")
    meta = {
        "schema_version": "1.0",
        "description": description,
        "state": state.upper(),
        "discipline": discipline,
        "standards_applied": _summarise_standards(std),
        "units": units_type,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "output_dxf": str(output_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    # Launch viewer if requested
    if view_after:
        import subprocess
        import sys as _sys
        subprocess.Popen([_sys.executable, "-m", "ezdxf", "view", str(output_path)])

    return output_path


def _detect_discipline(description: str) -> str:
    """Infer civil discipline from description keywords."""
    desc = description.lower()
    keywords = {
        "transportation": ["road", "highway", "street", "intersection",
                           "pavement", "lane", "traffic", "asphalt"],
        "drainage":       ["storm", "sewer", "culvert", "inlet", "drainage",
                           "runoff", "detention", "retention", "swale"],
        "grading":        ["grade", "grading", "contour", "elevation",
                           "earthwork", "cut", "fill", "retaining"],
        "utilities":      ["water", "gas", "electric", "fiber", "utility",
                           "main", "service", "ductbank"],
        "site":           ["site", "parking", "building", "landscape",
                           "ada", "ramp", "sidewalk"],
    }
    scores = {disc: sum(kw in desc for kw in kws)
              for disc, kws in keywords.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "site"


def _add_standards_note(msp: Any, std: dict, state: str) -> None:
    """Add standards compliance note to drawing."""
    lines = [f"STANDARDS: {state.upper()} DOT / AASHTO 7th Ed."]
    # std is the flat merged discipline dict
    lane_w = std.get("lane_width_ft")
    if lane_w:
        spd = std.get("design_speed_mph", 45)
        lines.append(f"LANE WIDTH: {lane_w}' | SPEED: {spd} MPH")
    min_cover = std.get("min_pipe_cover_ft")
    if min_cover:
        storm_yr = std.get("design_storm_minor_year", std.get("design_storm_yr", 10))
        lines.append(f"STORM: {storm_yr}-yr | PIPE COVER: {min_cover}'min")
    frost = std.get("frost_depth_in")
    if frost:
        lines.append(f"FROST DEPTH: {frost}\"")

    for i, line in enumerate(lines):
        msp.add_text(
            line,
            dxfattribs={
                "layer": "ANNO-TEXT",
                "height": 0.12,
                "insert": (-20, -5 - i * 1.5),
            }
        )


def _summarise_standards(std: dict) -> dict:
    """Return a flat summary of key standards values for the JSON sidecar."""
    # std is already a flat discipline dict — return directly
    return {k: v for k, v in std.items() if not isinstance(v, dict)}


# ── Batch generation ───────────────────────────────────────────────────────────

def generate_all_disciplines(state: str = "national",
                             output_dir: str | Path | None = None) -> list[Path]:
    """Generate DXF files for all disciplines for a given state."""
    disciplines = ["transportation", "drainage", "grading", "utilities", "site"]
    out_dir = Path(output_dir) if output_dir else _OUT_DIR / state.lower()
    results = []
    for disc in disciplines:
        path = generate_civil_dxf(
            description=f"{disc} plan",
            state=state,
            discipline=disc,
            output_path=out_dir / f"{state.lower()}_{disc}.dxf",
        )
        results.append(path)
        print(f"[autocad] wrote {disc}: {path}")
    return results
