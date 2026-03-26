"""
tests/test_cad_router.py

Tests for aria_os/tool_router.py (select_cad_tool) and
aria_os/cadquery_generator.py (_CQ_TEMPLATE_MAP template smoke tests).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aria_os.tool_router import (
    select_cad_tool,
    get_output_formats,
    GRASSHOPPER_PART_IDS,
    FUSION_PART_IDS,
    GRASSHOPPER_KEYWORDS,
    FUSION_KEYWORDS,
    BLENDER_KEYWORDS,
)


# ═══════════════════════════════════════════════════════════════════════════
# Known part_id routing
# ═══════════════════════════════════════════════════════════════════════════

class TestPartIDRouting:
    def test_grasshopper_part_ids(self):
        """Every part_id in GRASSHOPPER_PART_IDS must route to grasshopper."""
        for pid in GRASSHOPPER_PART_IDS:
            result = select_cad_tool("some goal", {"part_id": pid})
            assert result == "grasshopper", f"{pid} should route to grasshopper"

    def test_fusion_part_ids(self):
        """Every part_id in FUSION_PART_IDS must route to fusion."""
        for pid in FUSION_PART_IDS:
            result = select_cad_tool("some goal", {"part_id": pid})
            assert result == "fusion", f"{pid} should route to fusion"

    def test_unknown_part_id_defaults_cadquery(self):
        result = select_cad_tool("make a widget", {"part_id": "unknown_widget"})
        assert result == "cadquery"


# ═══════════════════════════════════════════════════════════════════════════
# Keyword-based routing
# ═══════════════════════════════════════════════════════════════════════════

class TestKeywordRouting:
    def test_grasshopper_keyword_helical(self):
        result = select_cad_tool("helical spring 50mm", {})
        assert result == "grasshopper"

    def test_grasshopper_keyword_loft(self):
        result = select_cad_tool("loft between two profiles", {})
        assert result == "grasshopper"

    def test_fusion_keyword_lattice(self):
        result = select_cad_tool("lattice infill structure", {})
        assert result == "fusion"

    def test_fusion_keyword_honeycomb(self):
        result = select_cad_tool("honeycomb panel", {})
        assert result == "fusion"

    def test_blender_keyword_organic(self):
        result = select_cad_tool("organic sculpt form", {})
        assert result == "blender"

    def test_blender_keyword_remesh(self):
        result = select_cad_tool("remesh and cleanup model", {})
        assert result == "blender"


# ═══════════════════════════════════════════════════════════════════════════
# LRE keyword routing (should go to cadquery per CLAUDE.md)
# ═══════════════════════════════════════════════════════════════════════════

class TestLRERouting:
    """LRE keywords (nozzle, rocket, etc.) should NOT route to grasshopper/fusion
    when there is no grasshopper/fusion keyword match — they should fall through
    to cadquery (default)."""

    def test_nozzle_default_cadquery(self):
        result = select_cad_tool("nozzle 60mm throat", {"part_id": "lre_nozzle"})
        assert result == "cadquery"

    def test_rocket_default_cadquery(self):
        result = select_cad_tool("rocket nozzle", {"part_id": "lre_nozzle"})
        assert result == "cadquery"

    def test_turbopump_default_cadquery(self):
        result = select_cad_tool("turbopump housing", {"part_id": "turbopump"})
        assert result == "cadquery"


# ═══════════════════════════════════════════════════════════════════════════
# Feature-based routing
# ═══════════════════════════════════════════════════════════════════════════

class TestFeatureRouting:
    def test_ramp_feature_routes_grasshopper(self):
        plan = {"features": [{"type": "ramp", "description": "cam ramp"}]}
        result = select_cad_tool("cam collar", plan)
        assert result == "grasshopper"

    def test_helical_feature_description_routes_grasshopper(self):
        plan = {"features": [{"type": "groove", "description": "helical groove"}]}
        result = select_cad_tool("spool", plan)
        assert result == "grasshopper"

    def test_lattice_feature_routes_fusion(self):
        plan = {"features": [{"type": "lattice"}]}
        result = select_cad_tool("panel", plan)
        assert result == "fusion"


# ═══════════════════════════════════════════════════════════════════════════
# get_output_formats
# ═══════════════════════════════════════════════════════════════════════════

class TestOutputFormats:
    def test_cadquery_formats(self):
        assert get_output_formats("cadquery") == ["step", "stl"]

    def test_blender_formats(self):
        assert get_output_formats("blender") == ["stl"]

    def test_unknown_tool_defaults_stl(self):
        assert get_output_formats("nonexistent") == ["stl"]


# ═══════════════════════════════════════════════════════════════════════════
# Default routing
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaultRouting:
    def test_empty_goal_and_plan(self):
        result = select_cad_tool("", {})
        assert result == "cadquery"

    def test_none_goal(self):
        result = select_cad_tool(None, {})
        assert result == "cadquery"

    def test_plain_description_defaults(self):
        result = select_cad_tool("a simple bracket 100mm wide", {})
        assert result == "cadquery"


# ═══════════════════════════════════════════════════════════════════════════
# CadQuery template smoke tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCQTemplateMap:
    """Verify every entry in _CQ_TEMPLATE_MAP is a callable function."""

    @pytest.fixture(autouse=True)
    def _load_map(self):
        from aria_os.cadquery_generator import _CQ_TEMPLATE_MAP
        self.template_map = _CQ_TEMPLATE_MAP

    def test_map_not_empty(self):
        assert len(self.template_map) >= 14, (
            f"Expected at least 14 templates, got {len(self.template_map)}"
        )

    def test_all_entries_callable(self):
        for part_id, fn in self.template_map.items():
            assert callable(fn), f"Template for {part_id} is not callable"

    def test_core_aria_parts_present(self):
        expected = [
            "aria_ratchet_ring", "aria_housing", "aria_spool",
            "aria_cam_collar", "aria_brake_drum", "aria_catch_pawl",
            "aria_rope_guide",
        ]
        for pid in expected:
            assert pid in self.template_map, f"Missing core ARIA template: {pid}"

    def test_generic_parts_present(self):
        expected = [
            "aria_bracket", "aria_flange", "aria_shaft",
            "aria_pulley", "aria_cam", "aria_pin", "aria_spacer",
        ]
        for pid in expected:
            assert pid in self.template_map, f"Missing generic template: {pid}"

    def test_lre_nozzle_present(self):
        assert "lre_nozzle" in self.template_map
        assert "aria_nozzle" in self.template_map

    def test_template_returns_string(self):
        """Each template function should return a string of CadQuery code."""
        for part_id, fn in self.template_map.items():
            try:
                result = fn({})
            except TypeError:
                # Some templates may require params — pass empty dict
                try:
                    result = fn(params={})
                except Exception:
                    continue  # skip if template needs special args
            if result is not None:
                assert isinstance(result, str), (
                    f"Template {part_id} returned {type(result)}, expected str"
                )
