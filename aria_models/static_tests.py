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
    yield_pawl_mpa: float = YIELD_PAWL_MPA,
    yield_housing_mpa: float = YIELD_HOUSING_MPA,
    yield_shaft_mpa: float = YIELD_SHAFT_MPA,
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

        sf_c = yield_pawl_mpa    / sc  if sc  > 0 else 999
        sf_b = yield_pawl_mpa    / sb  if sb  > 0 else 999
        sf_h = yield_housing_mpa / sh  if sh  > 0 else 999
        sf_s = yield_shaft_mpa   / ss  if ss  > 0 else 999

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


# ── ANSI Z359.14 drop test limits ─────────────────────────────────────
ANSI_MAX_ARREST_FORCE_N   = 8000.0   # peak arrest force
ANSI_MAX_AVG_ARREST_N     = 6000.0   # average arrest force
ANSI_MAX_ARREST_DIST_MM   = 813.0    # maximum arrest distance

# ── Default drop test parameters (from context/aria_test_standards.md) ─
DEFAULT_MASS_KG           = 140.0
DEFAULT_DROP_HEIGHT_M     = 0.040
DEFAULT_TRIGGER_G         = 0.7
DEFAULT_ROPE_K            = 80000.0   # N/m
DEFAULT_ABSORBER_K        = 30000.0   # N/m
DEFAULT_ABSORBER_C        = 2000.0    # Ns/m
DEFAULT_ABSORBER_FMAX     = 4000.0    # N


def simulate_drop_test(
    mass_kg: float = DEFAULT_MASS_KG,
    drop_height_m: float = DEFAULT_DROP_HEIGHT_M,
    rope_k: float = DEFAULT_ROPE_K,
    absorber_k: float = DEFAULT_ABSORBER_K,
    absorber_c: float = DEFAULT_ABSORBER_C,
    absorber_fmax: float = DEFAULT_ABSORBER_FMAX,
    dt: float = 0.0001,
    t_max: float = 2.0,
) -> dict:
    """Simulate a 1-D mass-spring-damper fall arrest per ANSI Z359.14.

    Model:
        A point mass falls from *drop_height_m* under gravity, then
        engages a series rope-spring (stiffness *rope_k*) and an energy
        absorber (spring *absorber_k* + dashpot *absorber_c*, force
        capped at *absorber_fmax*).  Integration uses classic 4th-order
        Runge-Kutta with timestep *dt*.

    Returns a dict with:
        peak_force_N        max rope tension during arrest
        avg_force_N         mean rope tension while rope is loaded
        arrest_distance_mm  max displacement below the engagement point
        peak_decel_g        peak deceleration in g
        ansi_peak_ok        peak_force_N <= 8000 N
        ansi_avg_ok         avg_force_N  <= 6000 N
        ansi_dist_ok        arrest_distance_mm <= 813 mm
        ansi_passed         all three checks pass
        time_steps          number of integration steps taken
    """
    g = 9.81

    # ── helpers ────────────────────────────────────────────────────────
    def _rope_force(x):
        """Rope tension (only in compression of spring, i.e. x > 0)."""
        if x <= 0.0:
            return 0.0
        return rope_k * x

    def _absorber_force(x, v):
        """Combined absorber spring + damper, capped at Fmax."""
        if x <= 0.0:
            return 0.0
        f_spring = absorber_k * x
        f_damp   = absorber_c * v  # v > 0 → damping opposes motion
        f_total  = f_spring + f_damp
        # Absorber saturates at Fmax (energy-absorber tear/deformation)
        if f_total > absorber_fmax:
            f_total = absorber_fmax
        if f_total < 0.0:
            f_total = 0.0
        return f_total

    def _accel(x, v):
        """Net acceleration on the mass.  Positive x = downward."""
        f_rope = _rope_force(x)
        f_abs  = _absorber_force(x, v)
        # gravity pulls down (+), rope & absorber resist (-)
        return g - (f_rope + f_abs) / mass_kg

    # ── initial conditions ────────────────────────────────────────────
    # Free-fall from drop_height_m: impact velocity via energy
    v0 = math.sqrt(2.0 * g * drop_height_m)  # m/s downward (positive)
    x  = 0.0   # displacement below engagement point
    v  = v0

    peak_force   = 0.0
    peak_decel   = 0.0
    max_x        = 0.0
    force_sum    = 0.0
    force_count  = 0
    steps        = 0

    # ── RK4 integration ──────────────────────────────────────────────
    t = 0.0
    while t < t_max:
        # Current force (for logging)
        f_now = _rope_force(x) + _absorber_force(x, v)
        if f_now > 0.0:
            force_sum   += f_now
            force_count += 1
        if f_now > peak_force:
            peak_force = f_now
        decel = f_now / mass_kg
        if decel > peak_decel:
            peak_decel = decel
        if x > max_x:
            max_x = x

        # RK4 step
        k1v = _accel(x, v)
        k1x = v

        k2v = _accel(x + 0.5 * dt * k1x, v + 0.5 * dt * k1v)
        k2x = v + 0.5 * dt * k1v

        k3v = _accel(x + 0.5 * dt * k2x, v + 0.5 * dt * k2v)
        k3x = v + 0.5 * dt * k2v

        k4v = _accel(x + dt * k3x, v + dt * k3v)
        k4x = v + dt * k3v

        x += (dt / 6.0) * (k1x + 2.0 * k2x + 2.0 * k3x + k4x)
        v += (dt / 6.0) * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)

        t += dt
        steps += 1

        # Early termination: mass has bounced back and is above
        # engagement point with upward velocity (arrest complete)
        if x < 0.0 and v < 0.0 and t > 0.01:
            break

    avg_force = force_sum / force_count if force_count > 0 else 0.0
    arrest_dist_mm = max_x * 1000.0

    ansi_peak = peak_force <= ANSI_MAX_ARREST_FORCE_N
    ansi_avg  = avg_force  <= ANSI_MAX_AVG_ARREST_N
    ansi_dist = arrest_dist_mm <= ANSI_MAX_ARREST_DIST_MM

    return dict(
        peak_force_N       = round(peak_force, 2),
        avg_force_N        = round(avg_force, 2),
        arrest_distance_mm = round(arrest_dist_mm, 2),
        peak_decel_g       = round(peak_decel / g, 2),
        ansi_peak_ok       = ansi_peak,
        ansi_avg_ok        = ansi_avg,
        ansi_dist_ok       = ansi_dist,
        ansi_passed        = ansi_peak and ansi_avg and ansi_dist,
        time_steps         = steps,
    )


def test_drop_ansi_compliance():
    """Run the default-parameter drop test and assert ANSI Z359.14 compliance.

    Called by:  python -m pytest aria_models/static_tests.py
                python aria_models/static_tests.py   (via __main__ block)
    """
    result = simulate_drop_test()
    print("\n── Dynamic Drop Test (ANSI Z359.14) ──")
    for k, v in result.items():
        print(f"  {k:24s} = {v}")

    assert result["ansi_peak_ok"], (
        f"Peak arrest force {result['peak_force_N']:.0f} N exceeds "
        f"ANSI limit {ANSI_MAX_ARREST_FORCE_N:.0f} N")
    assert result["ansi_avg_ok"], (
        f"Avg arrest force {result['avg_force_N']:.0f} N exceeds "
        f"ANSI limit {ANSI_MAX_AVG_ARREST_N:.0f} N")
    assert result["ansi_dist_ok"], (
        f"Arrest distance {result['arrest_distance_mm']:.1f} mm exceeds "
        f"ANSI limit {ANSI_MAX_ARREST_DIST_MM:.0f} mm")

    print("  ANSI Z359.14 compliance:  PASSED")
    return result


def ansi_proof_load_check(
    housing_wall_mm: float = HOUSING_WALL_MM,
    yield_mpa: float = YIELD_HOUSING_MPA,
    ansi_load_n: float = 16000.0,
) -> dict:
    """
    Test 1E: ANSI 16,000 N proof load check on housing wall.
    Returns a summary dict with stress, SF, and pass/fail.
    """
    sh = _housing_wall_stress_mpa(ansi_load_n, wall_mm=housing_wall_mm)
    sf = yield_mpa / sh if sh > 0 else 999
    return dict(
        test         = "1E — Housing Proof Load",
        load_N       = ansi_load_n,
        stress_MPa   = round(sh, 1),
        yield_MPa    = yield_mpa,
        safety_factor= round(sf, 2),
        passed       = sf >= 2.0,
    )


# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Static tests
    loads = [500, 1000, 2000, 4000, 8000, 16000]
    df = simulate_static_pawl(loads)
    print("\n── Static Pawl Test ──")
    print(df.to_string(index=False))

    proof = ansi_proof_load_check()
    print(f"\n── {proof['test']} ──")
    for k, v in proof.items():
        print(f"  {k}: {v}")

    # Dynamic drop test
    test_drop_ansi_compliance()
