# aria_dashboard.py
# ARIA virtual test dashboard — runs Setup 1/2/3 using aria_models where available.

import streamlit as st
import numpy as np
import pandas as pd

from aria_models import simulate_static_pawl as static_pawl_from_models
from aria_models import simulate_drop_test as drop_test_from_models
from aria_models import simulate_false_trip_check as false_trip_from_models
from aria_models import AriaStateMachine, Inputs
from aria_models.design_suggestions import (
    get_static_suggestions,
    get_drop_suggestions,
    get_false_trip_suggestions,
    get_state_machine_suggestions,
)

# -------------------------------------------------------
# High-level config
# -------------------------------------------------------
st.set_page_config(
    page_title="ARIA Test Dashboard",
    layout="wide",
)

st.title("ARIA Virtual Test Dashboard")
st.caption("Real physics (aria_models). Run each setup and use **Design suggestions** to iterate toward a working design that passes all tests.")

with st.expander("**Accuracy & using this for real design**", expanded=False):
    st.markdown("""
    **Will the graphs and results match real testing?** They can be made to — if you keep the models in sync with your hardware.

    - **Setup 1 (Static):** Stress formulas are simplified (no stress concentrations, ideal geometry). Use the **geometry sliders** (when available) or edit `aria_models/static_tests.py` so dimensions match your Fusion parts. Results are good for **relative comparison** and **ballpark safety factor**; run a physical proof test before relying on absolute numbers.

    - **Setup 2 (Dynamic):** The model is 1D mass–spring–damper. Real rigs have friction, rope hysteresis, and 3D effects. **To make it accurate for design changes:** (1) Run **one physical drop test** and note measured peak force (N) and arrest distance (mm). (2) In this dashboard, adjust **absorber stiffness k** and **damping c** until the simulated peak and distance match that test. (3) Then use the dashboard to explore “what if I change mass or drop height?” — those predictions will be meaningful.

    - **Setup 3 (State machine):** Logic matches the firmware; timing is ideal (no sensor delay). Good for “will TAKE confirm?” and transition order; not for exact latency.

    **Bottom line:** Use the dashboard to **iterate toward a passing design**, then **calibrate** static geometry and dynamic k/c to one real test. After that, the tool is useful for real design changes.
    """)

# -------------------------------------------------------
# Sidebar: select setup + test
# -------------------------------------------------------
SETUPS = {
    "Setup 1 – Static Load Frame": [
        "1A – Trip Lever & Pawl Visual",
        "1B – Pawl Progressive Load",
        "1C – One-Way Bearing Isolation",
        "1D – Cam Collar Reset Under Load",
        "1E – Housing Static Strength",
    ],
    "Setup 2 – Dynamic Drop Rig": [
        "2A – False Trip Check (Slow Movement)",
        "2B – Drop Test (Trigger & Arrest)",
        "2C – Energy Absorber Verification",
        "2D – Rope Spool Dynamics",
    ],
    "Setup 3 – Functional Bench": [
        "3A – State Machine Walkthrough",
        "3B – TAKE Two-Factor Confirmation",
        "3C – CV Clip Detection",
        "3D – Cam Collar Reset & Lowering",
        "3E – 50-Cycle Reliability",
    ],
    "Voice & audio": [
        "Voice commands reference",
        "Confidence threshold",
        "Record audio (Edge Impulse)",
    ],
    "Visual (CV)": [
        "Clip detection",
        "Climber detection",
        "CV thresholds",
    ],
    "ARIA tools": [
        "Live monitor & test harness",
        "PID tuner & simulator",
        "Calibration & wiring",
    ],
}

with st.sidebar:
    st.header("Test Selection")
    setup = st.selectbox("Setup", list(SETUPS.keys()))
    test = st.selectbox("Test", SETUPS[setup])

def simulate_state_machine_cycles(n_cycles=10, dt_s=0.2):
    """
    Run aria_models.AriaStateMachine for n_cycles; each cycle is
    IDLE -> CLIMBING -> TAKE -> LOWER -> IDLE. Returns timeline DataFrame.
    """
    sm = AriaStateMachine()
    t_now = 0.0
    rows = []

    for _ in range(n_cycles):
        # IDLE: no tension
        for _ in range(3):
            inp = Inputs(tension_N=0.0, time_s=t_now, dt=dt_s)
            out = sm.step(inp)
            rows.append({"time_s": round(t_now, 2), "state": out.state.name})
            t_now += dt_s

        # CLIMBING: tension > 15 N
        for _ in range(15):
            inp = Inputs(tension_N=45.0, time_s=t_now, dt=dt_s)
            out = sm.step(inp)
            rows.append({"time_s": round(t_now, 2), "state": out.state.name})
            t_now += dt_s

        # Voice "take" then load > 200 N within 0.5 s -> TAKE
        inp = Inputs(voice="take", tension_N=45.0, time_s=t_now, dt=dt_s)
        sm.step(inp)
        t_now += dt_s
        inp = Inputs(tension_N=250.0, time_s=t_now, dt=dt_s)
        out = sm.step(inp)
        rows.append({"time_s": round(t_now, 2), "state": out.state.name})
        t_now += dt_s

        # Hold TAKE
        for _ in range(5):
            inp = Inputs(tension_N=300.0, time_s=t_now, dt=dt_s)
            out = sm.step(inp)
            rows.append({"time_s": round(t_now, 2), "state": out.state.name})
            t_now += dt_s

        # LOWER until tension < 15 -> IDLE
        inp = Inputs(voice="lower", tension_N=300.0, time_s=t_now, dt=dt_s)
        out = sm.step(inp)
        rows.append({"time_s": round(t_now, 2), "state": out.state.name})
        t_now += dt_s
        for tension in [200.0, 100.0, 50.0, 20.0, 10.0, 5.0]:
            inp = Inputs(tension_N=tension, time_s=t_now, dt=dt_s)
            out = sm.step(inp)
            rows.append({"time_s": round(t_now, 2), "state": out.state.name})
            t_now += dt_s

    return pd.DataFrame(rows)


# -------------------------------------------------------
# Main panel: per-setup UI + plots
# -------------------------------------------------------

st.subheader(f"{setup} – {test}")

col_left, col_right = st.columns([2, 1])

with col_right:
    st.markdown("### Inputs for this test")

    if setup.startswith("Setup 1"):
        if "1B" in test:
            load_steps = st.multiselect(
                "Static load steps (N)",
                [500, 1000, 2000, 4000, 6000, 8000, 16000],
                default=[],
                help="Select one or more; no default — you choose.",
            )
        else:
            load_steps = [st.number_input("Load (N)", min_value=100, max_value=20000, value=100, step=100, help="Single load for this test.")]
        st.caption("Match geometry to your Fusion design:")
        pawl_thickness_mm = st.slider("Pawl thickness (mm)", 6.0, 14.0, 6.0, step=0.5)
        housing_wall_mm = st.slider("Housing wall at boss (mm)", 6.0, 16.0, 6.0, step=0.5)
        shaft_d_mm = st.slider("Shaft diameter (mm)", 16.0, 28.0, 16.0, step=1.0)

    elif setup.startswith("Setup 2"):
        m_climber = st.slider("Test mass (kg)", 60, 160, 60, step=5, help="Drop test mass; used in 2A and 2B/2C/2D.")
        rope_length_m = st.slider("Effective rope length (m)", 5, 40, 5, step=1, help="Reference for real rig; shown in results.")
        drop_height_mm = st.slider("Drop height (mm)", 20, 200, 20, step=10)
        drop_height_m = drop_height_mm / 1000
        trigger_g = st.slider("Trigger threshold (g)", 0.3, 1.5, 0.3, step=0.1)
        absorber_k = st.slider("Absorber stiffness k (N/m)", 10000, 80000, 10000, step=5000)
        absorber_c = st.slider("Absorber damping c (N·s/m)", 500, 5000, 500, step=100)
        rope_k = st.slider("Rope stiffness (N/m)", 40000, 120000, 40000, step=5000)
        st.caption("**Calibrate:** After your first real drop test, tune k and c until simulated peak and arrest distance match measured values.")

    elif setup.startswith("Setup 3"):
        n_cycles = st.slider("Simulated cycles", 5, 100, 5, step=5)

    elif setup.startswith("Voice"):
        voice_cmd = st.selectbox(
            "Simulate voice command",
            ["(none)", "take", "lower", "rest", "watch me", "up", "climbing", "slack"],
            index=0,
            help="Command the ESP32 sends to STM32 over UART.",
        )
        # Confidence is determined by the Edge Impulse model, not set by user
        voice_model_outcome = st.selectbox(
            "Voice model outcome (confidence determined by model)",
            [
                "High confidence — 0.92",
                "Above threshold — 0.88",
                "Borderline — 0.85",
                "Below threshold — 0.78",
                "Low — 0.60",
            ],
            index=0,
            help="In real system the voice model outputs this; STM32 acts only if ≥ 0.85.",
        )
        voice_conf = float(voice_model_outcome.split("—")[1].strip())

    elif setup.startswith("Visual"):
        # Clip confidence is determined by the CV model, not set by user
        cv_model_outcome = st.selectbox(
            "CV model outcome (clip confidence determined by model)",
            [
                "Clip detected — 0.88",
                "Borderline — 0.75",
                "Not detected — 0.55",
                "No clip — 0.30",
            ],
            index=0,
            help="In real system the camera/CV model outputs this; CLIPPING if ≥ 0.75.",
        )
        cv_clip_conf = float(cv_model_outcome.split("—")[1].strip())
        cv_climber = st.checkbox("Climber on wall", help="Climber detected by camera (model output).")

    elif setup.startswith("ARIA tools"):
        pass  # no inputs

    if setup.startswith("Setup 1") or setup.startswith("Setup 2") or setup.startswith("Setup 3"):
        st.caption("Results update automatically when you change inputs above.")

with col_left:
    # Run simulation with current parameters — results update when you change inputs
    # ---------- SETUP 1 ----------
    if setup.startswith("Setup 1"):
        if "1B" in test and not load_steps:
            st.warning("Select at least one static load step (N) to run the test.")
        else:
            df = static_pawl_from_models(
                load_steps,
                pawl_thickness_mm=pawl_thickness_mm,
                housing_wall_mm=housing_wall_mm,
                shaft_d_mm=shaft_d_mm,
            )
            st.markdown("#### Static pawl / housing response (real physics — aria_models)")

            passed_all = df["passed"].all()
            st.metric("Result", "PASS" if passed_all else "FAIL", "min SF ≥ 2.0 at all loads")
            st.dataframe(df, hide_index=True)

            st.bar_chart(
                df.set_index("load_N")["min_sf"],
                use_container_width=True,
            )

            min_sf = df["min_sf"].min()
            st.caption(f"Minimum safety factor: {min_sf:.2f} (ANSI target ≥ 2.0).")

            suggestions = get_static_suggestions(df)
            if suggestions:
                st.markdown("#### Design suggestions to pass")
                for s in suggestions:
                    st.markdown(f"- {s}")
            elif not passed_all:
                st.markdown("#### Design suggestions to pass")
                st.markdown("- Increase section sizes or use higher yield materials so min SF ≥ 2.0 at every load step.")

    # ---------- SETUP 2 ----------
    elif setup.startswith("Setup 2"):
        if "2A" in test:
            # False trip check (real physics): must NOT fire at 0.3g
            result = false_trip_from_models(
                mass_kg=m_climber,
                accel_g=0.3,
                rope_k=rope_k,
                trigger_g=trigger_g,
            )
            st.markdown("#### False trip check (real physics — must NOT fire at 0.3g)")
            passed = result["passed"]
            st.metric("Result", "PASS" if passed else "FAIL", result["message"])
            st.caption(f"Applied acceleration: {result['accel_g_applied']}g · Trigger threshold: {result['trigger_g_threshold']}g")
            suggestions = get_false_trip_suggestions(result)
            if suggestions:
                st.markdown("#### Design suggestions to pass")
                for s in suggestions:
                    st.markdown(f"- {s}")
        else:
            # 2B / 2C / 2D: drop test (real physics)
            df, summary = drop_test_from_models(
                mass_kg=m_climber,
                drop_height_m=drop_height_m,
                trigger_g=trigger_g,
                absorber_k=absorber_k,
                absorber_c=absorber_c,
                rope_k=rope_k,
            )

            st.markdown("#### Rope / mass dynamic response (real physics — aria_models)")

            tab1, tab2, tab3, tab4 = st.tabs(
                ["Tension vs time", "Acceleration vs time", "Position vs time", "Velocity vs time"]
            )

            with tab1:
                st.line_chart(
                    df.set_index("time_s")["tension_N"],
                    use_container_width=True,
                )
            with tab2:
                st.line_chart(
                    df.set_index("time_s")["accel_ms2"],
                    use_container_width=True,
                )
            with tab3:
                st.line_chart(
                    df.set_index("time_s")["pos_m"],
                    use_container_width=True,
                )
            with tab4:
                st.line_chart(
                    df.set_index("time_s")["vel_ms"],
                    use_container_width=True,
                )

            passed = summary.get("passed", False)
            st.metric("Result", "PASS" if passed else "FAIL", "ANSI: distance < 813 mm, peak < 8000 N, avg < 6000 N, trigger fires")
            st.markdown("#### Summary vs ANSI limits")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Arrest distance (mm)", f"{summary['arrest_distance_mm']:.2f}", "limit 813")
            col_b.metric("Peak force (N)", f"{summary['peak_force_N']:.2f}", "limit 8000")
            col_c.metric("Avg force (N)", f"{summary['avg_force_N']:.2f}", "limit 6000")
            st.caption(f"Trigger fired: **{summary.get('trigger_fired', False)}** — Absorber activated: **{summary.get('absorber_activated', False)}** — Rope length (reference): **{rope_length_m} m**")

            suggestions = get_drop_suggestions(summary)
            if suggestions:
                st.markdown("#### Design suggestions to pass")
                for s in suggestions:
                    st.markdown(f"- {s}")

    # ---------- SETUP 3 ----------
    elif setup.startswith("Setup 3"):
        df = simulate_state_machine_cycles(n_cycles)
        st.markdown("#### State machine timeline (real logic — aria_models)")

        states_seen = df["state"].unique().tolist()
        has_cycle = all(s in states_seen for s in ["IDLE", "CLIMBING", "TAKE", "LOWER"])
        passed_sm = has_cycle and len(df) > 10
        st.metric("Result", "PASS" if passed_sm else "CHECK", "IDLE → CLIMBING → TAKE → LOWER → IDLE cycles")

        state_map = {s: i for i, s in enumerate(sorted(df["state"].unique()))}
        df_plot = df.copy()
        df_plot["state_id"] = df_plot["state"].map(state_map)

        st.line_chart(
            df_plot.set_index("time_s")["state_id"],
            use_container_width=True,
        )

        st.caption("State encoding: " + ", ".join(f"{k}={v}" for k, v in state_map.items()))
        st.caption(f"Simulated {n_cycles} cycles using **aria_models** state machine (same logic as firmware).")

        suggestions = get_state_machine_suggestions(df, n_cycles)
        if suggestions:
            st.markdown("#### Design suggestions")
            for s in suggestions:
                st.markdown(f"- {s}")

    # ---------- VOICE & AUDIO ----------
    elif setup.startswith("Voice"):
        st.markdown("#### Voice commands (ESP32 → STM32)")
        st.markdown("""
        The ESP32 **Edge Impulse** wake-word model determines confidence for each detected command; you don't set it. STM32 acts only if confidence ≥ 0.85. Keep **VOICE_CONFIDENCE_MIN = 0.85** in sync with `aria_simulator.py` and firmware.
        """)
        if voice_cmd and voice_cmd != "(none)":
            would_act = "✓ Would act" if voice_conf >= 0.85 else "✗ Below threshold (no action)"
            st.info(f"**{voice_cmd}** — voice model confidence **{voice_conf:.2f}** → {would_act}")
        st.markdown("""
        | Command   | Effect |
        |-----------|--------|
        | take      | TAKE (with load > 200 N within 500 ms) |
        | lower     | LOWER |
        | rest      | REST |
        | watch me  | WATCH_ME |
        | up        | UP |
        | climbing  | Exit REST/TAKE → CLIMBING |
        | slack     | Slack payout |
        """)
        st.markdown("---")
        st.markdown("#### Record audio for Edge Impulse")
        st.markdown("""
        - Run **`python tools/aria_collect_audio.py`** to record labeled `.wav` samples.
        - Upload to [Edge Impulse](https://studio.edgeimpulse.com), train the model, export `.zip`, reflash ESP32.
        - See **`docs/edge_impulse_setup.md`** for full steps.
        """)

    # ---------- VISUAL (CV) ----------
    elif setup.startswith("Visual"):
        st.markdown("#### Clip detection (camera → CLIPPING)")
        st.markdown("""
        The ESP32 **CV model** (camera) determines clip confidence; you don't set it. When confidence ≥ 0.75, STM32 enters **CLIPPING** and pays out slack. Keep **CLIP_DETECT_CONFIDENCE = 0.75** in sync with firmware and simulator.
        """)
        st.metric("Clip confidence (from CV model)", f"{cv_clip_conf:.2f}", "≥ 0.75 → CLIPPING state")
        st.metric("Climber on wall", "Yes" if cv_climber else "No", "Used for IDLE → CLIMBING")
        st.markdown("---")
        st.markdown("#### CV in the state machine")
        st.markdown("- **IDLE → CLIMBING:** needs `cv_climber_detected` + tension > 15 N.")
        st.markdown("- **CLIMBING → CLIPPING:** when clip gesture confidence ≥ threshold; motor pays out 0.65 m slack.")
        st.markdown("- Retrain or tune thresholds in ESP32 firmware and match in `aria_simulator.py`.")

    # ---------- ARIA TOOLS ----------
    elif setup.startswith("ARIA tools"):
        st.markdown("#### Live monitor & test harness")
        st.markdown("""
        - **`python tools/aria_monitor.py`** — Real-time dashboard when STM32 is connected (state, tension, motor %). Use **`--inject`** to send fake voice commands without ESP32.
        - **`python tools/aria_test_harness.py --run all`** — Automated STM32 scenarios (climb, fall, watch_me, rest, up). Run before a test day.
        """)
        st.markdown("#### PID tuner & simulator")
        st.markdown("""
        - **`python tools/aria_pid_tuner.py`** — Tune Kp, Ki, Kd for climbing tension. Copy values to `aria_simulator.py` and `firmware/stm32/aria_main.cpp`.
        - **`python tools/aria_simulator.py`** — CLI state-machine replica; use `voice take`, `sensor load_cell_n=680`, `scenario climb`, etc. Constants must match STM32 (see CURSOR_GUIDE Golden Rule).
        """)
        st.markdown("#### Calibration & wiring")
        st.markdown("""
        - **Load cell:** After first STM32 flash, type `cal` in serial within 3 s; copy HX711_OFFSET and HX711_SCALE into `firmware/stm32/calibration.cpp`, reflash.
        - **Wiring check:** Flash `firmware/stm32/wiring_verify.cpp` to confirm load cell, encoder, UART, GPIO before running main firmware.
        - **Docs:** `docs/ARIA_SETUP.md` (flash order, wiring), `docs/REAL_TESTING_CHECKLIST.md` (test day checklist).
        """)
