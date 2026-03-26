"""
cem_aria.py — ARIA CEM shim

Thin re-export layer so the CEM registry can import "cem_aria" without
shadowing the aria_cem/ package that may exist in the repo root.

All public names from aria_cem.py are re-exported here.
"""
from aria_cem import (  # noqa: F401  (re-export everything)
    ARIAInputs,
    ARIAGeom,
    BrakeDrumGeom,
    RatchetGeom,
    CentrifugalClutchGeom,
    RopeSpoolGeom,
    MotorSpec,
    HousingGeom,
    ANSI_Z359_14,
    MATERIAL_6061_T6,
    MATERIAL_4140_STEEL,
    compute_brake_drum,
    compute_ratchet,
    compute_centrifugal_clutch,
    compute_rope_spool,
    compute_motor,
    compute_housing,
    compute_aria,
)

# Alias so callers can use either name
compute_aria_geometry = compute_aria


def compute_for_goal(goal: str, params: dict | None = None) -> dict:
    """
    Entry point used by the CEM pipeline orchestrator.

    Accepts an optional params dict that can override ARIAInputs defaults.
    Returns a flat dict of geometry scalars suitable for plan["params"] injection.
    """
    inp_kwargs: dict = {}
    if params:
        for field_name in ARIAInputs.__dataclass_fields__:
            if field_name in params and params[field_name] is not None:
                try:
                    inp_kwargs[field_name] = float(params[field_name])
                except (TypeError, ValueError):
                    pass

    inp = ARIAInputs(**inp_kwargs)
    geom = compute_aria(inp)

    return {
        "part_family": "aria",
        # Brake drum
        "brake_drum_od_mm":        geom.brake_drum.diameter_mm,
        "brake_drum_width_mm":     geom.brake_drum.width_mm,
        "brake_drum_wall_mm":      geom.brake_drum.wall_thickness_mm,
        "brake_drum_sf":           geom.brake_drum.safety_factor,
        # Ratchet
        "ratchet_n_teeth":         geom.ratchet.n_teeth,
        "ratchet_pitch_mm":        geom.ratchet.pitch_mm,
        "ratchet_face_width_mm":   geom.ratchet.face_width_mm,
        "ratchet_tooth_height_mm": geom.ratchet.tooth_height_mm,
        "ratchet_sf":              geom.ratchet.safety_factor,
        # Spool
        "spool_hub_od_mm":         geom.spool.hub_diameter_mm,
        "spool_flange_od_mm":      geom.spool.flange_diameter_mm,
        "spool_width_mm":          geom.spool.width_mm,
        "spool_capacity_m":        geom.spool.capacity_m,
        # Housing
        "housing_od_mm":           geom.housing.od_mm,
        "housing_wall_mm":         geom.housing.wall_thickness_mm,
        "housing_length_mm":       geom.housing.length_mm,
        # Motor
        "motor_torque_Nm":         geom.motor.required_torque_Nm,
        "gearbox_ratio":           geom.motor.gearbox_ratio,
        # System
        "predicted_arrest_dist_m": geom.predicted_arrest_distance_m,
        "predicted_peak_force_kN": geom.predicted_peak_force_kN,
        "total_mass_kg":           geom.total_mass_kg,
    }
