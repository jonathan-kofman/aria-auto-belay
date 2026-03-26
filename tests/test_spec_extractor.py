"""
tests/test_spec_extractor.py

40 tests for aria_os/spec_extractor.py — extract_spec() and merge_spec_into_plan().
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aria_os.spec_extractor import extract_spec, merge_spec_into_plan


# ═══════════════════════════════════════════════════════════════════════════
# OD extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestODExtraction:
    def test_mm_od_suffix(self):
        spec = extract_spec("213mm OD")
        assert spec["od_mm"] == 213.0

    def test_od_prefix_space(self):
        spec = extract_spec("OD 50mm")
        assert spec["od_mm"] == 50.0

    def test_od_colon(self):
        spec = extract_spec("OD: 75mm")
        assert spec["od_mm"] == 75.0

    def test_od_equals(self):
        spec = extract_spec("OD=120mm")
        assert spec["od_mm"] == 120.0

    def test_mm_outer_diameter(self):
        spec = extract_spec("50mm outer diameter")
        assert spec["od_mm"] == 50.0

    def test_mm_outer_shorthand(self):
        spec = extract_spec("50mm outer")
        assert spec["od_mm"] == 50.0

    def test_outer_dia_mm(self):
        spec = extract_spec("outer dia 50mm")
        assert spec["od_mm"] == 50.0

    def test_diameter_of_mm(self):
        spec = extract_spec("diameter of 50mm")
        assert spec["od_mm"] == 50.0

    def test_od_float(self):
        spec = extract_spec("213.5mm OD")
        assert spec["od_mm"] == 213.5

    def test_mm_diameter_as_od(self):
        spec = extract_spec("ring 100mm diameter")
        assert spec["od_mm"] == 100.0


# ═══════════════════════════════════════════════════════════════════════════
# Bore / inner diameter
# ═══════════════════════════════════════════════════════════════════════════

class TestBoreExtraction:
    def test_mm_bore_suffix(self):
        spec = extract_spec("25mm bore")
        assert spec["bore_mm"] == 25.0
        assert spec["id_mm"] == 25.0

    def test_bore_prefix_space(self):
        spec = extract_spec("bore 50mm")
        assert spec["bore_mm"] == 50.0

    def test_bore_colon(self):
        spec = extract_spec("bore: 30mm")
        assert spec["bore_mm"] == 30.0

    def test_mm_id(self):
        spec = extract_spec("50mm ID")
        assert spec["bore_mm"] == 50.0

    def test_inner_diameter(self):
        spec = extract_spec("inner diameter 50mm")
        assert spec["bore_mm"] == 50.0

    def test_id_mm_alias(self):
        """bore_mm and id_mm should always be the same value."""
        spec = extract_spec("25mm bore")
        assert spec["bore_mm"] == spec["id_mm"]


# ═══════════════════════════════════════════════════════════════════════════
# Thickness / height / width / depth / length
# ═══════════════════════════════════════════════════════════════════════════

class TestLinearDimensions:
    def test_thickness_mm_thick(self):
        spec = extract_spec("21mm thick")
        assert spec["thickness_mm"] == 21.0
        assert spec["height_mm"] == 21.0

    def test_thickness_colon(self):
        spec = extract_spec("thickness: 15mm")
        assert spec["thickness_mm"] == 15.0

    def test_width_mm_wide(self):
        spec = extract_spec("60mm wide")
        assert spec["width_mm"] == 60.0

    def test_width_colon(self):
        spec = extract_spec("width: 80mm")
        assert spec["width_mm"] == 80.0

    def test_depth_mm_deep(self):
        spec = extract_spec("30mm deep")
        assert spec["depth_mm"] == 30.0

    def test_depth_colon(self):
        spec = extract_spec("depth: 45mm")
        assert spec["depth_mm"] == 45.0

    def test_length_mm_long(self):
        spec = extract_spec("200mm long")
        assert spec["length_mm"] == 200.0

    def test_length_colon(self):
        spec = extract_spec("length: 150mm")
        assert spec["length_mm"] == 150.0

    def test_mm_tall(self):
        spec = extract_spec("40mm tall")
        assert spec["thickness_mm"] == 40.0


# ═══════════════════════════════════════════════════════════════════════════
# Box notation WxHxD
# ═══════════════════════════════════════════════════════════════════════════

class TestBoxNotation:
    def test_simple_box(self):
        spec = extract_spec("bracket 50x100x200mm")
        assert spec["width_mm"] == 50.0
        assert spec["height_mm"] == 100.0
        assert spec["depth_mm"] == 200.0

    def test_box_with_spaces(self):
        spec = extract_spec("plate 50 x 100 x 200 mm")
        assert spec["width_mm"] == 50.0
        assert spec["height_mm"] == 100.0

    def test_box_does_not_overwrite_explicit(self):
        """Explicit width should not be overwritten by box notation."""
        spec = extract_spec("60mm wide bracket 50x100x200mm")
        assert spec["width_mm"] == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# Teeth
# ═══════════════════════════════════════════════════════════════════════════

class TestTeeth:
    def test_n_teeth(self):
        spec = extract_spec("24 teeth")
        assert spec["n_teeth"] == 24

    def test_n_tooth_hyphen(self):
        spec = extract_spec("24-tooth ratchet ring")
        assert spec["n_teeth"] == 24


# ═══════════════════════════════════════════════════════════════════════════
# Bolts
# ═══════════════════════════════════════════════════════════════════════════

class TestBolts:
    def test_combined_bolt_shorthand(self):
        spec = extract_spec("4xM8 bolts")
        assert spec["n_bolts"] == 4
        assert spec["bolt_dia_mm"] == 8.0

    def test_bolt_circle_mm(self):
        spec = extract_spec("90mm bolt circle")
        assert spec["bolt_circle_r_mm"] == 45.0

    def test_n_holes(self):
        spec = extract_spec("flange with 4 holes")
        assert spec["n_bolts"] == 4

    def test_pcd(self):
        spec = extract_spec("PCD: 120mm")
        assert spec["bolt_circle_r_mm"] == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# Material detection
# ═══════════════════════════════════════════════════════════════════════════

class TestMaterial:
    def test_6061(self):
        spec = extract_spec("6061 aluminium bracket")
        assert spec["material"] == "aluminium_6061"

    def test_7075(self):
        spec = extract_spec("7075 flange")
        assert spec["material"] == "aluminium_7075"

    def test_stainless(self):
        spec = extract_spec("stainless steel shaft")
        assert spec["material"] == "stainless_steel"

    def test_titanium(self):
        spec = extract_spec("titanium bracket")
        assert spec["material"] == "titanium"

    def test_generic_aluminium(self):
        spec = extract_spec("aluminium housing")
        assert spec["material"] == "aluminium"

    def test_aluminum_american_spelling(self):
        spec = extract_spec("aluminum plate")
        assert spec["material"] == "aluminium"


# ═══════════════════════════════════════════════════════════════════════════
# Part type
# ═══════════════════════════════════════════════════════════════════════════

class TestPartType:
    def test_ratchet_ring(self):
        spec = extract_spec("ARIA ratchet ring")
        assert spec["part_type"] == "ratchet_ring"

    def test_brake_drum(self):
        spec = extract_spec("brake drum 200mm OD")
        assert spec["part_type"] == "brake_drum"

    def test_cam_collar(self):
        spec = extract_spec("cam collar 50mm bore")
        assert spec["part_type"] == "cam_collar"

    def test_nozzle_routes_lre(self):
        spec = extract_spec("rocket nozzle 60mm throat")
        assert spec["part_type"] == "lre_nozzle"

    def test_housing(self):
        spec = extract_spec("housing 500mm wide")
        assert spec["part_type"] == "housing"

    def test_longest_match_wins(self):
        """'ratchet ring' (2 words) must win over 'ring' (1 word)."""
        spec = extract_spec("ratchet ring")
        assert spec["part_type"] == "ratchet_ring"


# ═══════════════════════════════════════════════════════════════════════════
# merge_spec_into_plan
# ═══════════════════════════════════════════════════════════════════════════

class TestMergeSpec:
    def test_merge_populates_empty_params(self):
        spec = {"od_mm": 213.0, "n_teeth": 24}
        plan = {"params": {}}
        merge_spec_into_plan(spec, plan)
        assert plan["params"]["od_mm"] == 213.0
        assert plan["params"]["n_teeth"] == 24

    def test_merge_does_not_overwrite_existing(self):
        spec = {"od_mm": 100.0}
        plan = {"params": {"od_mm": 213.0}}
        merge_spec_into_plan(spec, plan)
        assert plan["params"]["od_mm"] == 213.0

    def test_merge_overwrites_none(self):
        spec = {"od_mm": 100.0}
        plan = {"params": {"od_mm": None}}
        merge_spec_into_plan(spec, plan)
        assert plan["params"]["od_mm"] == 100.0

    def test_merge_creates_params_key(self):
        spec = {"od_mm": 50.0}
        plan = {}
        merge_spec_into_plan(spec, plan)
        assert plan["params"]["od_mm"] == 50.0

    def test_merge_returns_plan(self):
        plan = {"params": {}}
        result = merge_spec_into_plan({"od_mm": 1.0}, plan)
        assert result is plan


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self):
        spec = extract_spec("")
        assert isinstance(spec, dict)
        # Should have no dimensional keys
        assert "od_mm" not in spec
        assert "bore_mm" not in spec

    def test_no_dimensions(self):
        spec = extract_spec("a bracket for mounting")
        assert "od_mm" not in spec
        assert spec.get("part_type") == "bracket"

    def test_wall_thickness(self):
        spec = extract_spec("housing with 5mm wall")
        assert spec["wall_mm"] == 5.0

    def test_radius_to_diameter(self):
        spec = extract_spec("disc radius 25mm")
        assert spec["diameter_mm"] == 50.0

    def test_full_ratchet_ring_spec(self):
        """Integration: full natural-language description extracts all fields."""
        spec = extract_spec(
            "ARIA ratchet ring, 213mm OD, 185mm bore, 21mm thick, 24 teeth, 6061 aluminium"
        )
        assert spec["od_mm"] == 213.0
        assert spec["bore_mm"] == 185.0
        assert spec["thickness_mm"] == 21.0
        assert spec["n_teeth"] == 24
        assert spec["material"] == "aluminium_6061"
        assert spec["part_type"] == "ratchet_ring"
