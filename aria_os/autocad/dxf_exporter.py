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
    """Generate a sample road plan layout based on standards."""
    from aria_os.autocad.civil_elements import (
        add_road_centerline, add_road_lanes, add_row,
        add_station_label, add_pavement_marking,
        add_intersection, add_north_arrow, add_title_block
    )
    # std is already the flat discipline dict from get_standard(state, "transportation")
    lane_w = std.get("lane_width_ft", 12.0)
    n_lanes = std.get("lanes_min", 2)
    row_w = std.get("row_width_ft", 60.0)
    shldr_w = std.get("shoulder_width_ft", 8.0)

    # Primary road: 1000 ft run
    cl_start = (0, 0)
    cl_end = (1000, 0)

    add_road_centerline(msp, cl_start, cl_end)
    add_road_lanes(msp, cl_start, cl_end,
                   lane_width_ft=lane_w, n_lanes=n_lanes,
                   shoulder_width_ft=shldr_w)
    add_row(msp, cl_start, cl_end, row_width_ft=row_w)

    # Station labels every 100 ft
    for sta in range(0, 1100, 100):
        add_station_label(msp, (sta, -(row_w / 2 + 3)), float(sta))

    # Pavement markings
    add_pavement_marking(msp, cl_start, cl_end, "centerline")

    # Cross-street at sta 500
    cross_start = (500, -(row_w / 2 + 200))
    cross_end = (500, row_w / 2 + 200)
    add_road_centerline(msp, cross_start, cross_end)
    add_road_lanes(msp, cross_start, cross_end,
                   lane_width_ft=lane_w, n_lanes=2,
                   shoulder_width_ft=shldr_w)
    add_intersection(msp, (500, 0), radius_ft=40)

    add_north_arrow(msp, (1050, 50), size=20)
    add_title_block(msp, origin=(-20, -row_w / 2 - 60),
                    title="ROAD PLAN", scale="1\"=50'")


def _generate_drainage_plan(msp: Any, std: dict, description: str) -> None:
    """Generate a sample storm drainage layout."""
    from aria_os.autocad.civil_elements import (
        add_storm_pipe, add_inlet, add_manhole, add_detention_pond,
        add_swale, add_north_arrow, add_title_block
    )
    pipe_size = std.get("min_culvert_dia_in", std.get("min_pipe_dia_storm_in", 18.0))
    # Main trunk
    add_storm_pipe(msp, (0, 0), (400, 0), diameter_in=pipe_size)
    add_storm_pipe(msp, (400, 0), (400, -200), diameter_in=pipe_size)
    # Laterals
    for x in range(50, 400, 100):
        add_storm_pipe(msp, (x, 60), (x, 0), diameter_in=12.0)
        add_inlet(msp, (x, 65), label=f"CI-{x // 100 + 1}")
    # Manholes at junctions
    add_manhole(msp, (0, 0), label="MH-1")
    add_manhole(msp, (400, 0), label="MH-2")
    add_manhole(msp, (400, -200), label="OUTFALL")
    # Detention pond at outfall
    add_detention_pond(msp, (400, -350), width_ft=150, depth_ft=100)
    # Swale
    add_swale(msp, [(100, 80), (200, 75), (300, 78), (400, 70)])
    add_north_arrow(msp, (450, 50), size=15)
    add_title_block(msp, origin=(-20, -500),
                    title="DRAINAGE PLAN", scale="1\"=40'")


def _generate_grading_plan(msp: Any, std: dict, description: str) -> None:
    """Generate a sample grading plan with contours."""
    from aria_os.autocad.civil_elements import (
        add_contour, add_slope_arrow, add_retaining_wall,
        add_spot_elevation, add_north_arrow, add_title_block
    )
    # Existing contours
    for elev in range(100, 120, 2):
        offset = (elev - 100) * 15
        pts = [(0, offset), (100, offset + 5), (200, offset + 3),
               (300, offset + 7), (400, offset)]
        add_contour(msp, pts, elevation=float(elev),
                    is_index=(elev % 10 == 0), is_proposed=False)

    # Proposed contours (graded building pad)
    for elev in range(110, 116, 2):
        offset = (elev - 110) * 20 + 100
        pts = [(50, offset), (150, offset + 2), (250, offset - 2), (350, offset)]
        add_contour(msp, pts, elevation=float(elev),
                    is_index=False, is_proposed=True)

    # Slope arrows
    add_slope_arrow(msp, (200, 150), (200, 50), slope_pct=5.0)
    add_slope_arrow(msp, (200, 200), (350, 200), slope_pct=2.0)

    # Retaining wall
    add_retaining_wall(msp, [(50, 120), (150, 120), (200, 110)])

    # Spot elevations
    for x, y, elev in [(100, 100, 107.3), (200, 150, 112.6), (300, 100, 104.8)]:
        add_spot_elevation(msp, (x, y), elev)

    add_north_arrow(msp, (430, 250), size=20)
    add_title_block(msp, origin=(-20, -50),
                    title="GRADING PLAN", scale="1\"=20'")


def _generate_utilities_plan(msp: Any, std: dict, description: str) -> None:
    """Generate a sample utilities plan."""
    from aria_os.autocad.civil_elements import (
        add_utility_line, add_utility_crossing, add_manhole,
        add_north_arrow, add_title_block
    )
    # Water main
    add_utility_line(msp, (0, 10), (500, 10), "water", 12.0)
    # Sewer
    add_utility_line(msp, (0, 0), (500, 0), "sewer", 8.0)
    # Gas
    add_utility_line(msp, (0, -10), (500, -10), "gas", 4.0)
    # Electric ductbank
    add_utility_line(msp, (0, -20), (500, -20), "electric", 4.0)
    # Fiber
    add_utility_line(msp, (0, -30), (500, -30), "fiber", 1.25)
    # Storm crossing marker at 250ft
    add_utility_crossing(msp, (250, 0))
    # Manholes
    for x in range(0, 600, 100):
        add_manhole(msp, (x, 0), label=f"SMH-{x // 100 + 1}")

    add_north_arrow(msp, (530, 30), size=15)
    add_title_block(msp, origin=(-20, -80),
                    title="UTILITY PLAN", scale="1\"=50'")


def _generate_site_plan(msp: Any, std: dict, description: str) -> None:
    """Generate a sample site plan."""
    from aria_os.autocad.civil_elements import (
        add_building_footprint, add_parking_stalls, add_ada_ramp,
        add_property_boundary, add_row, add_north_arrow, add_title_block
    )
    # Property
    add_property_boundary(msp, [(0, 0), (300, 0), (300, 200), (0, 200)])
    # Building
    add_building_footprint(msp, (50, 60), width_ft=150, depth_ft=100)
    # Parking
    add_parking_stalls(msp, (50, 10), stall_width_ft=9, stall_depth_ft=18,
                       n_stalls=12, angle_deg=90)
    # ADA ramps
    add_ada_ramp(msp, (50, 60))
    add_ada_ramp(msp, (200, 60))

    add_north_arrow(msp, (320, 160), size=20)
    add_title_block(msp, origin=(-20, -60),
                    title="SITE PLAN", scale="1\"=30'")


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
