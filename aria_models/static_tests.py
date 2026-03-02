# aria_models/static_tests.py
#
# WHAT THIS IS:
#   Virtual static load test engine for ARIA Setup 1 tests.
#   Computes safety factors for every load step using the actual
#   geometry and material from your Fusion scripts and project record.
#   No hardware needed — pure math.
#
# WHEN TO RUN:
#   Called by aria_dashboard.py when you select Setup 1 and click
#   "Run Simulation". Do NOT run this file directly.
#
# WHAT THE OUTPUT MEANS:
#   safety_factor >= 2.0  → geometry/material adequate for that load step.
#   safety_factor < 2.0   → you need thicker walls, better material,
#                           or a lower design load. Fix before physical test.
#   passed = True/False   → whether ANSI 2× SF requirement is met.
#
# KEY GEOMETRY (from your Fusion scripts and project record):
#   Pawl:         A2 tool steel, 58 HRC, yield ~1800 MPa
#                 Body 55mm long, 22mm tall, 9mm thick
#                 Tip contact width ~6mm, engagement depth ~3mm
#   Ratchet ring: 4140 QT 40-45 HRC, yield ~1300 MPa
#                 Pitch radius 100mm, 24 teeth, face width 20mm
#   Housing:      6061-T6, yield 276 MPa
#                 700×680×344mm box, 10mm wall thickness
#   Main shaft:   4140 HT, yield ~1000 MPa
#                 20mm diameter, supported at two bearing bores

import math
import pandas as pd

# ── Material yield strengths (MPa) ──────────────────────────────────────
YIELD_PAWL_MPA       = 1800.0   # A2 tool steel 58 HRC
YIELD_RATCHET_MPA    = 1300.0   # 4140 QT 40-45 HRC
YIELD_HOUSING_MPA    = 276.0    # 6061-T6
YIELD_SHAFT_MPA      = 1000.0   # 4140 HT

# ── Pawl geometry (mm) ──────────────────────────────────────────────────
PAWL_TIP_WIDTH_MM    = 6.0      # contact width at tooth tip
PAWL_THICKNESS_MM    = 9.0      # out-of-plane thickness
PAWL_ARM_MM          = 45.0     # moment arm pivot to tip
PAWL_BODY_H_MM       = 22.0     # cross-section height at root
PAWL_ENGAGEMENT_MM   = 3.0      # depth of tooth engagement

# ── Ratchet ring geometry (mm) ──────────────────────────────────────────
RATCHET_PITCH_R_MM   = 100.0    # pitch radius
RATCHET_FACE_W_MM    = 20.0     # tooth face width (axial)
N_TEETH              = 24       # number of teeth
N_PAWLS              = 2        # two pawls share load

# ── Housing geometry (mm) ───────────────────────────────────────────────
HOUSING_WALL_MM      = 10.0     # wall thickness after shell
HOUSING_W_MM         = 700.0
HOUSING_H_MM         = 680.0
HOUSING_D_MM         = 344.0

# ── Shaft geometry (mm) ─────────────────────────────────────────────────
SHAFT_D_MM           = 20.0     # shaft diameter
SHAFT_SPAN_MM        = 344.0    # bearing span ≈ housing depth


def _pawl_contact_stress_mpa(
    force_n: float,
    tip_width_mm: float = PAWL_TIP_WIDTH_MM,
    engagement_mm: float = PAWL_ENGAGEMENT_MM,
) -> float:
    """
    Hertzian-style contact stress at pawl tip.
    Simplified: treat as flat-on-flat contact.
    """
    area_mm2 = tip_width_mm * engagement_mm
    area_m2  = area_mm2 * 1e-6
    stress_pa = (force_n / N_PAWLS) / area_m2
    return stress_pa / 1e6   # MPa


def _pawl_bending_stress_mpa(
    force_n: float,
    thickness_mm: float = PAWL_THICKNESS_MM,
    body_h_mm: float = PAWL_BODY_H_MM,
    arm_mm: float = PAWL_ARM_MM,
) -> float:
    """
    Bending stress at pawl root cross-section.
    Cantilever: M = F × arm, I = b*h³/12, c = h/2
    σ = M*c / I
    """
    f_per_pawl = force_n / N_PAWLS
    M = f_per_pawl * (arm_mm * 1e-3)           # N·m
    b = thickness_mm * 1e-3                     # m
    h = body_h_mm * 1e-3                        # m
    I = (b * h**3) / 12.0                             # m⁴
    c = h / 2.0
    sigma_pa = M * c / I
    return sigma_pa / 1e6   # MPa


def _housing_wall_stress_mpa(
    force_n: float,
    wall_mm: float = HOUSING_WALL_MM,
    boss_d_mm: float = 20.0,
) -> float:
    """
    Bearing stress on housing wall at pawl pivot boss.
    """
    area_mm2  = wall_mm * boss_d_mm
    area_m2   = area_mm2 * 1e-6
    stress_pa = force_n / area_m2
    return stress_pa / 1e6   # MPa


def _shaft_bending_stress_mpa(
    force_n: float,
    shaft_d_mm: float = SHAFT_D_MM,
    span_mm: float = SHAFT_SPAN_MM,
) -> float:
    """
    Shaft bending: simply supported beam, center load.
    """
    F = force_n
    L = span_mm * 1e-3
    d = shaft_d_mm * 1e-3
    M = F * L / 4.0
    I = math.pi * d**4 / 64.0
    c = d / 2.0
    sigma_pa = M * c / I
    return sigma_pa / 1e6   # MPa


def simulate_static_pawl(
    load_steps: list[float],
    ansi_static_n: float = 16000.0,
    *,
    pawl_tip_width_mm: float | None = None,
    pawl_engagement_mm: float | None = None,
    pawl_thickness_mm: float | None = None,
    pawl_body_h_mm: float | None = None,
    pawl_arm_mm: float | None = None,
    housing_wall_mm: float | None = None,
    shaft_d_mm: float | None = None,
    shaft_span_mm: float | None = None,
) -> pd.DataFrame:
    """
    Run virtual Setup 1 static tests for each load step.

    Args:
        load_steps:     List of loads in Newtons to test (e.g. [500,1000,...,8000])
        ansi_static_n:  ANSI proof load for Test 1E (default 16,000 N)

    Returns:
        DataFrame with columns:
            load_N              applied load
            contact_stress_MPa  pawl tip contact stress
            bending_stress_MPa  pawl root bending stress
            housing_stress_MPa  housing wall bearing stress
            shaft_stress_MPa    shaft bending stress
            sf_contact          safety factor vs pawl yield (contact)
            sf_bending          safety factor vs pawl yield (bending)
            sf_housing          safety factor vs housing yield
            sf_shaft            safety factor vs shaft yield
            min_sf              minimum safety factor across all checks
            passed              True if min_sf >= 2.0
    """
    tip_w = pawl_tip_width_mm if pawl_tip_width_mm is not None else PAWL_TIP_WIDTH_MM
    eng = pawl_engagement_mm if pawl_engagement_mm is not None else PAWL_ENGAGEMENT_MM
    thick = pawl_thickness_mm if pawl_thickness_mm is not None else PAWL_THICKNESS_MM
    body_h = pawl_body_h_mm if pawl_body_h_mm is not None else PAWL_BODY_H_MM
    arm = pawl_arm_mm if pawl_arm_mm is not None else PAWL_ARM_MM
    wall = housing_wall_mm if housing_wall_mm is not None else HOUSING_WALL_MM
    sd = shaft_d_mm if shaft_d_mm is not None else SHAFT_D_MM
    span = shaft_span_mm if shaft_span_mm is not None else SHAFT_SPAN_MM

    rows = []
    for F in load_steps:
        sc  = _pawl_contact_stress_mpa(F, tip_width_mm=tip_w, engagement_mm=eng)
        sb  = _pawl_bending_stress_mpa(F, thickness_mm=thick, body_h_mm=body_h, arm_mm=arm)
        sh  = _housing_wall_stress_mpa(F, wall_mm=wall)
        ss  = _shaft_bending_stress_mpa(F, shaft_d_mm=sd, span_mm=span)

        sf_c = YIELD_PAWL_MPA    / sc  if sc  > 0 else 999
        sf_b = YIELD_PAWL_MPA    / sb  if sb  > 0 else 999
        sf_h = YIELD_HOUSING_MPA / sh  if sh  > 0 else 999
        sf_s = YIELD_SHAFT_MPA   / ss  if ss  > 0 else 999

        min_sf = min(sf_c, sf_b, sf_h, sf_s)

        rows.append(dict(
            load_N              = F,
            contact_stress_MPa  = round(sc,  1),
            bending_stress_MPa  = round(sb,  1),
            housing_stress_MPa  = round(sh,  1),
            shaft_stress_MPa    = round(ss,  1),
            sf_contact          = round(sf_c, 2),
            sf_bending          = round(sf_b, 2),
            sf_housing          = round(sf_h, 2),
            sf_shaft            = round(sf_s, 2),
            min_sf              = round(min_sf, 2),
            passed              = min_sf >= 2.0,
        ))

    return pd.DataFrame(rows)


def ansi_proof_load_check(
    housing_wall_mm: float = HOUSING_WALL_MM,
    yield_mpa: float = YIELD_HOUSING_MPA,
    ansi_load_n: float = 16000.0,
) -> dict:
    """
    Test 1E: ANSI 16,000 N proof load check on housing wall.
    Returns a summary dict with stress, SF, and pass/fail.
    """
    sh = _housing_wall_stress_mpa(ansi_load_n)
    sf = yield_mpa / sh if sh > 0 else 999
    return dict(
        test         = "1E — Housing Proof Load",
        load_N       = ansi_load_n,
        stress_MPa   = round(sh, 1),
        yield_MPa    = yield_mpa,
        safety_factor= round(sf, 2),
        passed       = sf >= 2.0,
    )
