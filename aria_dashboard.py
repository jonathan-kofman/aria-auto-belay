# aria_dashboard.py
# ARIA virtual test dashboard — runs Setup 1/2/3 using aria_models where available.

import streamlit as st
import numpy as np
import pandas as pd
import os
import json
import threading
import time
from glob import glob

try:  # optional, used for live serial connection
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception:  # pyserial not installed
    serial = None  # type: ignore
    list_ports = None  # type: ignore

try:  # optional, used for richer charts
    import plotly.graph_objs as go  # type: ignore
except Exception:
    go = None  # type: ignore

try:  # optional, used for Firebase push of sessions
    import firebase_admin  # type: ignore
    from firebase_admin import credentials, firestore as fb_firestore  # type: ignore
except Exception:
    firebase_admin = None  # type: ignore
    credentials = None  # type: ignore
    fb_firestore = None  # type: ignore

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
    "Fault injection & failsafe": [
        "Load cell failure",
        "Encoder failure",
        "Voice module offline",
        "Zone camera offline",
        "Motor driver fault",
    ],
    "Misuse & edge cases": [
        "Two climbers on one device",
        "Down-pulling on rope",
        "Dynamic clipping / jumping",
        "Heavy climber fall on short rope",
    ],
    "Clearance & fall zone": [
        "Ground strike margin",
        "Obstacle clearance along swing arc",
    ],
    "E-stop & interventions": [
        "E-stop during climb",
        "E-stop during fall",
        "Manual takeover / belayer present",
    ],
    "Standards checklist": [
        "ANSI/EN coverage summary",
    ],
    "Test Session": [
        "Live hardware session",
    ],
    "PID Tuner": [
        "Tension PID gains",
    ],
    "Hardware Bring-Up": [
        "Pre-power-on checklist",
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

def simulate_state_machine_scenario(
    duration_s: float,
    dt_s: float,
    *,
    tension_profile_fn,
    voice_profile_fn,
    cv_clip_profile_fn,
    estop_profile_fn,
):
    """
    Generic state-machine simulation harness that can inject faults.
    Each *_profile_fn takes time_s -> value.
    Returns timeline DataFrame with time_s, state, motor_mode, and inputs.
    """
    sm = AriaStateMachine()
    t_now = 0.0
    rows = []
    n_steps = int(max(1, duration_s / dt_s))
    for _ in range(n_steps):
        inp = Inputs(
            voice=str(voice_profile_fn(t_now) or ""),
            tension_N=float(tension_profile_fn(t_now) or 0.0),
            cv_clip=bool(cv_clip_profile_fn(t_now) or False),
            estop=bool(estop_profile_fn(t_now) or False),
            time_s=t_now,
            dt=dt_s,
        )
        out = sm.step(inp)
        rows.append(
            {
                "time_s": round(t_now, 3),
                "state": out.state.name,
                "motor_mode": out.motor_mode,
                "tension_N": inp.tension_N,
                "voice": inp.voice,
                "cv_clip": inp.cv_clip,
                "estop": inp.estop,
            }
        )
        t_now += dt_s
    return pd.DataFrame(rows)

def _first_time_state(df: pd.DataFrame, state_name: str) -> float | None:
    sub = df[df["state"] == state_name]
    if sub.empty:
        return None
    return float(sub.iloc[0]["time_s"])


def _get_test_session_state():
    """Helper to keep all test-session state inside st.session_state."""
    if "test_session" not in st.session_state:
        st.session_state["test_session"] = {
            "connected": False,
            "port": None,
            "baud": 115200,
            "thread": None,
            "stop_flag": False,
            "rows": [],  # live packets
            "events": [],  # voice / drop / sync
            "recording": False,
            "record_name": "",
            "record_start": None,
            "push_to_firebase": False,
            "drop_count": 0,
        }
    return st.session_state["test_session"]


def _ensure_sessions_dir():
    os.makedirs("sessions", exist_ok=True)


BRING_UP_LOG_PATH = "bring_up_log.json"


def _load_bring_up_log() -> dict:
    if os.path.exists(BRING_UP_LOG_PATH):
        try:
            with open(BRING_UP_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_bring_up_log(data: dict) -> None:
    try:
        with open(BRING_UP_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


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
            load_steps = [
                st.number_input(
                    "Load (N)",
                    min_value=100,
                    max_value=20000,
                    value=100,
                    step=100,
                    help="Single load for this test.",
                )
            ]
        st.caption("Match geometry to your Fusion design:")
        pawl_thickness_mm = st.slider("Pawl thickness (mm)", 6.0, 14.0, 6.0, step=0.5)
        housing_wall_mm = st.slider("Housing wall at boss (mm)", 6.0, 16.0, 6.0, step=0.5)
        shaft_d_mm = st.slider("Shaft diameter (mm)", 16.0, 28.0, 16.0, step=1.0)

        # Scenario library for static setup (per session)
        st.markdown("#### Scenario library")
        static_name = st.text_input("Static scenario name")
        static_scenarios = st.session_state.setdefault("static_scenarios", {})
        static_existing = sorted(static_scenarios.keys())
        static_selected = st.selectbox("Load existing static scenario", ["(none)"] + static_existing)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save static scenario", disabled=not static_name.strip()):
                static_scenarios[static_name.strip()] = {
                    "load_steps": load_steps,
                    "pawl_thickness_mm": pawl_thickness_mm,
                    "housing_wall_mm": housing_wall_mm,
                    "shaft_d_mm": shaft_d_mm,
                }
                st.session_state["static_scenarios"] = static_scenarios
                st.success(f"Saved static scenario '{static_name.strip()}' for this session.")
        with c2:
            if st.button("Load static scenario", disabled=static_selected == "(none)"):
                s = static_scenarios.get(static_selected)
                if s:
                    if "1B" in test:
                        st.session_state["Static load steps (N)"] = s["load_steps"]
                    else:
                        st.session_state["Load (N)"] = s["load_steps"][0] if s["load_steps"] else 100
                    st.session_state["Pawl thickness (mm)"] = s["pawl_thickness_mm"]
                    st.session_state["Housing wall at boss (mm)"] = s["housing_wall_mm"]
                    st.session_state["Shaft diameter (mm)"] = s["shaft_d_mm"]
                    st.experimental_rerun()

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

        # Simple in-memory scenario library (per browser session)
        st.markdown("#### Scenario library")
        scenario_name = st.text_input("Scenario name")
        scenarios = st.session_state.setdefault("drop_scenarios", {})
        existing_names = sorted(scenarios.keys())
        selected_existing = st.selectbox("Load existing scenario", ["(none)"] + existing_names)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("Save current as scenario", disabled=not scenario_name.strip()):
                scenarios[scenario_name.strip()] = {
                    "m_climber": m_climber,
                    "rope_length_m": rope_length_m,
                    "drop_height_mm": drop_height_mm,
                    "trigger_g": trigger_g,
                    "absorber_k": absorber_k,
                    "absorber_c": absorber_c,
                    "rope_k": rope_k,
                }
                st.session_state["drop_scenarios"] = scenarios
                st.success(f"Saved scenario '{scenario_name.strip()}' for this session.")
        with col_s2:
            if st.button("Load scenario", disabled=selected_existing == "(none)"):
                s = scenarios.get(selected_existing)
                if s:
                    st.session_state["Test mass (kg)"] = s["m_climber"]
                    st.session_state["Effective rope length (m)"] = s["rope_length_m"]
                    st.session_state["Drop height (mm)"] = s["drop_height_mm"]
                    st.session_state["Trigger threshold (g)"] = s["trigger_g"]
                    st.session_state["Absorber stiffness k (N/m)"] = s["absorber_k"]
                    st.session_state["Absorber damping c (N·s/m)"] = s["absorber_c"]
                    st.session_state["Rope stiffness (N/m)"] = s["rope_k"]
                    st.experimental_rerun()

    elif setup.startswith("Setup 3"):
        n_cycles = st.slider("Simulated cycles", 5, 100, 5, step=5)

        # Scenario library for functional bench
        st.markdown("#### Scenario library")
        sm_name = st.text_input("State-machine scenario name")
        sm_scenarios = st.session_state.setdefault("sm_scenarios", {})
        sm_existing = sorted(sm_scenarios.keys())
        sm_selected = st.selectbox("Load existing SM scenario", ["(none)"] + sm_existing)
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Save SM scenario", disabled=not sm_name.strip()):
                sm_scenarios[sm_name.strip()] = {"n_cycles": n_cycles}
                st.session_state["sm_scenarios"] = sm_scenarios
                st.success(f"Saved SM scenario '{sm_name.strip()}' for this session.")
        with s2:
            if st.button("Load SM scenario", disabled=sm_selected == "(none)"):
                s = sm_scenarios.get(sm_selected)
                if s:
                    st.session_state["Simulated cycles"] = s["n_cycles"]
                    st.experimental_rerun()

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

    elif setup.startswith("Fault injection"):
        st.caption("Configure rough operating envelope for fault impact estimates:")
        fault_mass_kg = st.slider("Representative climber mass (kg)", 60, 160, 80, step=5)
        fault_rope_m = st.slider("Effective rope length (m)", 5, 40, 15, step=1)
        fault_height_m = st.slider("Max fall distance to consider (m)", 0.5, 5.0, 2.0, step=0.1)

    elif setup.startswith("Misuse"):
        misuse_mass_kg = st.slider("Heaviest allowed climber (kg)", 60, 160, 120, step=5)
        misuse_two_climbers = st.checkbox("Allow two climbers clipped at once (for what-if only)")

    elif setup.startswith("Clearance"):
        wall_height_m = st.slider("Wall height (floor to anchors) (m)", 8.0, 20.0, 12.0, step=0.5)
        climber_height_m = st.slider("Climber height (m)", 1.4, 2.1, 1.75, step=0.05)
        lowest_hold_m = st.slider("Lowest usable hold height (m)", 0.3, 2.0, 0.6, step=0.1)
        worst_fall_m = st.slider("Worst-case dynamic fall distance (m)", 0.5, 6.0, 3.0, step=0.1)
        safety_buffer_m = st.slider("Required clearance buffer (m)", 0.3, 1.5, 0.6, step=0.1)

    elif setup.startswith("E-stop"):
        estop_latency_ms = st.slider("E-stop reaction latency target (ms)", 50, 500, 200, step=10)

    elif setup.startswith("Standards"):
        pass

    elif setup.startswith("Test Session"):
        ts = _get_test_session_state()
        st.markdown("### Serial connection")

        if serial is None or list_ports is None:
            st.warning("pyserial is not installed. Install `pyserial` to enable live hardware streaming.")
        else:
            ports = list(list_ports.comports())
            port_labels = [p.device for p in ports] or ["(none)"]
            default_idx = 0 if ports else 0
            selected_port = st.selectbox("Serial port", port_labels, index=default_idx)
            baud = st.selectbox("Baud rate", [9600, 19200, 57600, 115200], index=3)

            ts["baud"] = baud
            if selected_port != "(none)":
                ts["port"] = selected_port

            col_conn1, col_conn2 = st.columns([1, 1])
            with col_conn1:
                if not ts["connected"] and st.button("Connect", use_container_width=True):
                    if ts.get("port"):
                        ts["stop_flag"] = False
                        def _reader():
                            try:
                                with serial.Serial(ts["port"], ts["baud"], timeout=0.1) as ser:  # type: ignore
                                    ts["connected"] = True
                                    while not ts["stop_flag"]:
                                        try:
                                            line = ser.readline()
                                        except Exception:
                                            break
                                        if not line:
                                            continue
                                        try:
                                            text = line.decode("utf-8", errors="ignore").strip()
                                        except Exception:
                                            continue
                                        now = time.time()
                                        # Parse S:<state_int>:<tension>:<rope_pos>:<motor_mode>
                                        if text.startswith("S:"):
                                            parts = text.split(":")
                                            if len(parts) >= 5:
                                                try:
                                                    state_int = int(parts[1])
                                                    tension = float(parts[2])
                                                    rope_pos = float(parts[3])
                                                    motor_mode = parts[4]
                                                except ValueError:
                                                    continue
                                                ts["rows"].append(
                                                    {
                                                        "ts": now,
                                                        "state_int": state_int,
                                                        "tension": tension,
                                                        "rope_pos": rope_pos,
                                                        "motor_mode": motor_mode,
                                                    }
                                                )
                                                if len(ts["rows"]) > 5000:
                                                    ts["rows"] = ts["rows"][-5000:]
                                                if ts["recording"]:
                                                    # events and rows share same structure; rows persisted on stop
                                                    pass
                                        elif text.startswith("V:"):
                                            # Optional voice event line: V:<command>
                                            cmd = text[2:].strip()
                                            ts["events"].append(
                                                {
                                                    "ts": now,
                                                    "type": "voice",
                                                    "command": cmd,
                                                }
                                            )
                                            if len(ts["events"]) > 2000:
                                                ts["events"] = ts["events"][-2000:]
                            finally:
                                ts["connected"] = False
                        t = threading.Thread(target=_reader, daemon=True)
                        ts["thread"] = t
                        t.start()
            with col_conn2:
                if ts["connected"] and st.button("Disconnect", use_container_width=True):
                    ts["stop_flag"] = True

            status_color = "🟢" if ts["connected"] else "🔴"
            st.markdown(f"Connection status: {status_color} {'Connected' if ts['connected'] else 'Disconnected'}")

        st.markdown("### Recording controls")
        fall_threshold = st.slider("Fall detection threshold (N)", 50.0, 400.0, 150.0, step=10.0)
        name_input = st.text_input("Session name (optional; will default to timestamp)", value=ts.get("record_name") or "")
        ts["record_name"] = name_input
        col_rec1, col_rec2, col_rec3 = st.columns([1, 1, 1])
        with col_rec1:
            if not ts["recording"] and st.button("Start Recording", type="primary"):
                ts["recording"] = True
                ts["record_start"] = time.time()
                ts["rows"] = []
                ts["events"] = []
                ts["drop_count"] = 0
        with col_rec2:
            if ts["recording"] and st.button("Stop Recording"):
                ts["recording"] = False
                _ensure_sessions_dir()
                ts_name = ts["record_name"].strip() or time.strftime("%Y%m%d_%H%M%S")
                path = os.path.join("sessions", f"{ts_name}.json")
                session_doc = {
                    "name": ts_name,
                    "start_ts": ts.get("record_start"),
                    "end_ts": time.time(),
                    "device_id": "STM32",
                    "rows": ts["rows"],
                    "events": ts["events"],
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(session_doc, f, indent=2)
                if ts.get("push_to_firebase"):
                    if firebase_admin and credentials and fb_firestore and os.path.exists("serviceAccountKey.json"):
                        try:
                            if not firebase_admin._apps:  # type: ignore
                                cred = credentials.Certificate("serviceAccountKey.json")  # type: ignore
                                firebase_admin.initialize_app(cred)  # type: ignore
                            db = fb_firestore.client()  # type: ignore
                            gym_id = "gym_001"
                            ref = db.collection("gyms").document(gym_id).collection("sessions").document()
                            db_dict = {
                                **session_doc,
                                "sessionId": ref.id,
                            }
                            ref.set(db_dict)
                        except Exception:
                            st.info("Firebase Admin not configured correctly; session saved locally only.")
                    else:
                        st.info("To push to Firebase, add `serviceAccountKey.json` and install firebase-admin.")
        with col_rec3:
            ts["push_to_firebase"] = st.checkbox("Push session to Firebase on stop", value=bool(ts.get("push_to_firebase")))

        st.caption(f"Live packets buffered: {len(ts['rows'])}")

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

            # Simple report for static setup
            static_report = [
                "# ARIA Static Test Report",
                "",
                f"- Loads: {', '.join(str(l) for l in (load_steps if isinstance(load_steps, list) else [load_steps]))} N",
                f"- Pawl thickness: {pawl_thickness_mm} mm",
                f"- Housing wall: {housing_wall_mm} mm",
                f"- Shaft diameter: {shaft_d_mm} mm",
                "",
                f"- Minimum safety factor: {min_sf:.2f}",
                f"Overall result: {'PASS' if passed_all else 'FAIL'} (ANSI target SF ≥ 2.0).",
            ]
            st.download_button(
                "Download static test report",
                "\n".join(static_report),
                file_name="aria_static_test_report.txt",
            )

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
                uploaded = st.file_uploader(
                    "Optional: upload real drop CSV (time_s,tension_N) to compare",
                    type=["csv"],
                    key="real_drop_csv",
                )
                if uploaded is not None:
                    real_df = pd.read_csv(uploaded)
                    if {"time_s", "tension_N"}.issubset(real_df.columns):
                        st.line_chart(
                            real_df.set_index("time_s")["tension_N"],
                            use_container_width=True,
                        )
                        st.caption("Real test data (tension vs time) plotted below simulated curve.")
                    else:
                        st.warning("CSV must contain columns 'time_s' and 'tension_N'.")
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
            st.metric(
                "Result",
                "PASS" if passed else "FAIL",
                "ANSI: distance < 813 mm, peak < 8000 N, avg < 6000 N, trigger fires",
            )
            st.markdown("#### Summary vs ANSI limits")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Arrest distance (mm)", f"{summary['arrest_distance_mm']:.2f}", "limit 813")
            col_b.metric("Peak force (N)", f"{summary['peak_force_N']:.2f}", "limit 8000")
            col_c.metric("Avg force (N)", f"{summary['avg_force_N']:.2f}", "limit 6000")
            st.caption(
                f"Trigger fired: **{summary.get('trigger_fired', False)}** — Absorber activated: **{summary.get('absorber_activated', False)}** — Rope length (reference): **{rope_length_m} m**"
            )

            suggestions = get_drop_suggestions(summary)
            if suggestions:
                st.markdown("#### Design suggestions to pass")
                for s in suggestions:
                    st.markdown(f"- {s}")

            # Monte Carlo exploration around current scenario
            st.markdown("#### Monte Carlo around this scenario (optional)")
            n_mc = st.slider("Monte Carlo runs", 0, 200, 0, step=10)
            if n_mc > 0:
                runs = []
                rng = np.random.default_rng()
                for i in range(n_mc):
                    m_i = float(rng.normal(m_climber, m_climber * 0.05))
                    h_i = float(max(0.05, rng.normal(drop_height_m, max(drop_height_m * 0.15, 0.05))))
                    _, sum_i = drop_test_from_models(
                        mass_kg=m_i,
                        drop_height_m=h_i,
                        trigger_g=trigger_g,
                        absorber_k=absorber_k,
                        absorber_c=absorber_c,
                        rope_k=rope_k,
                    )
                    runs.append(
                        {
                            "run": i + 1,
                            "mass_kg": m_i,
                            "drop_height_m": h_i,
                            "peak_force_N": sum_i["peak_force_N"],
                            "arrest_distance_mm": sum_i["arrest_distance_mm"],
                            "passed": bool(sum_i.get("passed", False)),
                        }
                    )
                mc_df = pd.DataFrame(runs)
                st.dataframe(mc_df, hide_index=True)
                st.caption(
                    f"Monte Carlo summary — pass rate: {(mc_df['passed'].mean() * 100):.1f}% · "
                    f"peak force range: {mc_df['peak_force_N'].min():.0f}–{mc_df['peak_force_N'].max():.0f} N"
                )

            # Simple text report download
            report_lines = [
                "# ARIA Drop Test Report",
                "",
                f"- Test mass: {m_climber} kg",
                f"- Drop height: {drop_height_mm} mm",
                f"- Trigger threshold: {trigger_g:.2f} g",
                f"- Absorber k: {absorber_k} N/m",
                f"- Absorber c: {absorber_c} N·s/m",
                f"- Rope k: {rope_k} N/m",
                "",
                f"- Arrest distance: {summary['arrest_distance_mm']:.2f} mm",
                f"- Peak force: {summary['peak_force_N']:.2f} N",
                f"- Avg force: {summary['avg_force_N']:.2f} N",
                f"- Trigger fired: {summary.get('trigger_fired', False)}",
                f"- Absorber activated: {summary.get('absorber_activated', False)}",
                "",
                f"Overall result: {'PASS' if passed else 'FAIL'} (ANSI limits embedded in dashboard).",
            ]
            st.download_button(
                "Download text report",
                "\n".join(report_lines),
                file_name="aria_drop_test_report.txt",
            )

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

        sm_report = [
            "# ARIA State Machine Test Report",
            "",
            f"- Simulated cycles: {n_cycles}",
            f"- States visited: {', '.join(states_seen)}",
            "",
            f"Overall result: {'PASS' if passed_sm else 'CHECK'} (IDLE → CLIMBING → TAKE → LOWER → IDLE cycles).",
        ]
        st.download_button(
            "Download state machine report",
            "\n".join(sm_report),
            file_name="aria_state_machine_report.txt",
        )

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

    # ---------- FAULT INJECTION & FAILSAFE ----------
    elif setup.startswith("Fault injection"):
        st.markdown("#### Fault injection simulator (modeled with state machine + drop physics)")

        dt = 0.05
        duration = 12.0
        t_fault = 5.0

        # Base behavior: climber present, then 'take' during climb, and a clip gesture event
        def base_tension(t):
            # 0-2s idle; 2-12s climbing tension ~45N; brief high load during take confirm
            if t < 2.0:
                return 0.0
            if 6.0 <= t <= 6.2:
                return 260.0
            return 45.0

        def base_voice(t):
            if 6.0 <= t <= 6.05:
                return "take"
            return ""

        def base_cv_clip(t):
            return 3.0 <= t <= 3.2

        def no_estop(_t):
            return False

        if "Load cell failure" in test:
            st.caption("Model: tension sensor drops to 0 at fault time while climber is active.")
            def tension_fn(t):
                return 0.0 if t >= t_fault else base_tension(t)
            def voice_fn(t):
                return base_voice(t)
            def cv_fn(t):
                return base_cv_clip(t)
            def estop_fn(t):
                return False
            df = simulate_state_machine_scenario(
                duration,
                dt,
                tension_profile_fn=tension_fn,
                voice_profile_fn=voice_fn,
                cv_clip_profile_fn=cv_fn,
                estop_profile_fn=estop_fn,
            )
            # Safety criterion: should NOT continue driving "TENSION" when sensor is dead.
            after = df[df["time_s"] >= t_fault]
            unsafe = (after["motor_mode"] == "TENSION").any()
            st.metric("Virtual result", "FAIL" if unsafe else "PASS", "Should enter safe state (LOCKOUT/ESTOP) not keep TENSION")
            st.line_chart(df.set_index("time_s")["tension_N"], use_container_width=True)
            st.dataframe(df.tail(50), hide_index=True)
        elif "Encoder failure" in test:
            st.caption("Model: encoder failure triggers an ESTOP (treated as a hard fault).")
            def tension_fn(t):
                return base_tension(t)
            def voice_fn(t):
                return base_voice(t)
            def cv_fn(t):
                return base_cv_clip(t)
            def estop_fn(t):
                return t >= t_fault
            df = simulate_state_machine_scenario(
                duration,
                dt,
                tension_profile_fn=tension_fn,
                voice_profile_fn=voice_fn,
                cv_clip_profile_fn=cv_fn,
                estop_profile_fn=estop_fn,
            )
            t_estop = _first_time_state(df, "ESTOP")
            st.metric("Entered ESTOP at (s)", "—" if t_estop is None else f"{t_estop:.2f}", "Expected immediate OFF")
            st.metric("Virtual result", "PASS" if t_estop is not None and t_estop <= t_fault + dt else "FAIL", "ESTOP must engage on encoder fault")
            st.dataframe(df.tail(80), hide_index=True)
        elif "Voice module offline" in test:
            st.caption("Model: voice commands are never received; device must still climb safely (but TAKE cannot be requested).")
            def tension_fn(t):
                return base_tension(t)
            def voice_fn(_t):
                return ""
            def cv_fn(t):
                return base_cv_clip(t)
            def estop_fn(_t):
                return False
            df = simulate_state_machine_scenario(
                duration,
                dt,
                tension_profile_fn=tension_fn,
                voice_profile_fn=voice_fn,
                cv_clip_profile_fn=cv_fn,
                estop_profile_fn=estop_fn,
            )
            saw_take = (df["state"] == "TAKE").any()
            saw_climb = (df["state"] == "CLIMBING").any()
            st.metric("Reached CLIMBING", "Yes" if saw_climb else "No")
            st.metric("Entered TAKE (should be No)", "Yes" if saw_take else "No")
            st.metric("Virtual result", "PASS" if saw_climb and not saw_take else "CHECK", "System should remain safe; TAKE requires voice+load")
            st.dataframe(df.tail(80), hide_index=True)
        elif "Zone camera offline" in test:
            st.caption("Model: clip gesture never detected; should avoid CLIPPING payout.")
            def tension_fn(t):
                return base_tension(t)
            def voice_fn(t):
                return base_voice(t)
            def cv_fn(_t):
                return False
            def estop_fn(_t):
                return False
            df = simulate_state_machine_scenario(
                duration,
                dt,
                tension_profile_fn=tension_fn,
                voice_profile_fn=voice_fn,
                cv_clip_profile_fn=cv_fn,
                estop_profile_fn=estop_fn,
            )
            clipping = (df["state"] == "CLIPPING").any()
            st.metric("Entered CLIPPING (should be No)", "Yes" if clipping else "No")
            st.metric("Virtual result", "PASS" if not clipping else "FAIL", "Should not payout slack if CV is offline")
            st.dataframe(df.tail(80), hide_index=True)
        else:
            st.caption("Model: motor driver fault triggers ESTOP immediately.")
            def tension_fn(t):
                return base_tension(t)
            def voice_fn(t):
                return base_voice(t)
            def cv_fn(t):
                return base_cv_clip(t)
            def estop_fn(t):
                return t >= t_fault
            df = simulate_state_machine_scenario(
                duration,
                dt,
                tension_profile_fn=tension_fn,
                voice_profile_fn=voice_fn,
                cv_clip_profile_fn=cv_fn,
                estop_profile_fn=estop_fn,
            )
            t_estop = _first_time_state(df, "ESTOP")
            st.metric("Virtual result", "PASS" if t_estop is not None else "FAIL", "ESTOP must engage on motor driver fault")
            st.dataframe(df.tail(80), hide_index=True)

        # Physics envelope still shown for cost-saving iteration
        st.markdown("#### Mechanical envelope under this fault (drop physics)")
        df_drop, summary = drop_test_from_models(
            mass_kg=fault_mass_kg,
            drop_height_m=float(fault_height_m),
            trigger_g=trigger_g if "trigger_g" in globals() else 0.7,
            absorber_k=absorber_k if "absorber_k" in globals() else 30000,
            absorber_c=absorber_c if "absorber_c" in globals() else 2000,
            rope_k=rope_k if "rope_k" in globals() else 80000,
        )
        st.metric("Peak force (N)", f"{summary['peak_force_N']:.0f}", f"limit {summary['ansi_peak_limit_N']:.0f}")
        st.metric("Arrest distance (mm)", f"{summary['arrest_distance_mm']:.1f}", f"limit {summary['ansi_distance_limit_mm']:.0f}")
        st.metric("Mechanical PASS", "YES" if summary.get("passed") else "NO", "Drop physics vs ANSI limits")

    # ---------- MISUSE & EDGE CASES ----------
    elif setup.startswith("Misuse"):
        st.markdown("#### Misuse & edge-case simulator (drop physics + false-trip physics)")

        # Use the Setup 2 sliders if present; otherwise defaults.
        trig = trigger_g if "trigger_g" in globals() else 0.7
        k_abs = absorber_k if "absorber_k" in globals() else 30000
        c_abs = absorber_c if "absorber_c" in globals() else 2000
        k_rope = rope_k if "rope_k" in globals() else 80000

        if "Two climbers" in test:
            st.caption("Model: two climbers clipped-in approximated as combined mass. This should be blocked, but we simulate worst-case loads.")
            total_mass = misuse_mass_kg * (2 if misuse_two_climbers else 1)
            df_drop, summary = drop_test_from_models(
                mass_kg=float(total_mass),
                drop_height_m=0.04,
                trigger_g=trig,
                absorber_k=k_abs,
                absorber_c=c_abs,
                rope_k=k_rope,
            )
            st.metric("Combined mass (kg)", f"{total_mass:.0f}", "policy test")
            st.metric("Mechanical PASS", "YES" if summary.get("passed") else "NO", "ANSI limits")
            st.line_chart(df_drop.set_index("time_s")["tension_N"], use_container_width=True)
        elif "Down-pulling" in test:
            st.caption("Model: evaluate false-trip risk during strong down-pull (accel_g). Pass = trigger does not fire.")
            accel_g = st.slider("Down-pull equivalent accel (g)", 0.1, 0.8, 0.3, step=0.05)
            result = false_trip_from_models(
                mass_kg=float(misuse_mass_kg),
                accel_g=float(accel_g),
                rope_k=float(k_rope),
                trigger_g=float(trig),
            )
            st.metric("Virtual result", "PASS" if result["passed"] else "FAIL", result["message"])
            st.caption(f"Applied accel: {accel_g:.2f}g vs trigger {trig:.2f}g")
        elif "Dynamic clipping" in test:
            st.caption("Model: evaluate false-trip risk from dynamic jump/clip movement as a higher accel_g pulse.")
            accel_g = st.slider("Dynamic movement accel (g)", 0.2, 1.2, 0.5, step=0.05)
            result = false_trip_from_models(
                mass_kg=float(misuse_mass_kg),
                accel_g=float(accel_g),
                rope_k=float(k_rope),
                trigger_g=float(trig),
            )
            st.metric("Virtual result", "PASS" if result["passed"] else "FAIL", result["message"])
        else:
            st.caption("Model: heavy climber fall approximated as worst-case Setup 2 drop with larger drop height.")
            drop_h = st.slider("Worst-case slack/drop before taut (mm)", 20, 200, 80, step=10) / 1000.0
            df_drop, summary = drop_test_from_models(
                mass_kg=float(misuse_mass_kg),
                drop_height_m=float(drop_h),
                trigger_g=float(trig),
                absorber_k=float(k_abs),
                absorber_c=float(c_abs),
                rope_k=float(k_rope),
            )
            st.metric("Mechanical PASS", "YES" if summary.get("passed") else "NO", "ANSI limits")
            st.metric("Peak force (N)", f"{summary['peak_force_N']:.0f}", f"limit {summary['ansi_peak_limit_N']:.0f}")
            st.metric("Arrest distance (mm)", f"{summary['arrest_distance_mm']:.1f}", f"limit {summary['ansi_distance_limit_mm']:.0f}")
            st.line_chart(df_drop.set_index("time_s")["tension_N"], use_container_width=True)

    # ---------- CLEARANCE & FALL ZONE ----------
    elif setup.startswith("Clearance"):
        st.markdown("#### Ground strike and obstacle clearance")
        # Very simple model: assume climber's feet start at lowest_hold_m, plus worst_fall_m downwards.
        clearance_m = wall_height_m - (climber_height_m + lowest_hold_m + worst_fall_m)
        margin_m = clearance_m - safety_buffer_m
        passed = margin_m >= 0
        st.metric(
            "Ground clearance margin (m)",
            f"{margin_m:.2f}",
            f"Required buffer: {safety_buffer_m:.2f} m",
        )
        st.caption(
            f"Approximate: wall={wall_height_m:.1f} m, climber={climber_height_m:.2f} m, "
            f"lowest hold={lowest_hold_m:.2f} m, worst fall={worst_fall_m:.2f} m."
        )
        st.info(
            "Result: "
            + ("PASS — clearance ≥ buffer." if passed else "FAIL — increase clearance or reduce fall distance.")
        )

    # ---------- E-STOP & INTERVENTIONS ----------
    elif setup.startswith("E-stop"):
        st.markdown("#### E-stop modeled test (state machine)")
        st.caption("This sim checks control logic: ESTOP immediately forces motor_mode=OFF and state=ESTOP.")
        dt = 0.05
        duration = 10.0
        t_press = st.slider("When E-stop is pressed (s)", 0.5, 9.0, 4.0, step=0.5)
        estop_latency_s = float(estop_latency_ms) / 1000.0

        def tension_fn(t):
            return 0.0 if t < 1.0 else 45.0

        def voice_fn(_t):
            return ""

        def cv_fn(_t):
            return False

        def estop_fn(t):
            return t >= (t_press + estop_latency_s)

        df = simulate_state_machine_scenario(
            duration,
            dt,
            tension_profile_fn=tension_fn,
            voice_profile_fn=voice_fn,
            cv_clip_profile_fn=cv_fn,
            estop_profile_fn=estop_fn,
        )
        t_estop = _first_time_state(df, "ESTOP")
        st.metric("ESTOP entered at (s)", "—" if t_estop is None else f"{t_estop:.2f}")
        st.metric(
            "Virtual result",
            "PASS" if t_estop is not None and t_estop <= (t_press + estop_latency_s + dt) else "FAIL",
            "ESTOP must engage by latency target",
        )
        st.dataframe(df.tail(80), hide_index=True)

    # ---------- STANDARDS CHECKLIST ----------
    elif setup.startswith("Standards"):
        st.markdown("#### ANSI/EN coverage checklist (virtual → real)")
        rows = [
            {
                "Requirement",
                "Virtual test",
                "Notes",
            },
        ]
        # Build as DataFrame more explicitly
        standards_rows = [
            {
                "Requirement": "Peak arrest force limit",
                "Virtual test": "Setup 2 – Drop Test",
                "Notes": "Check peak_force_N and avg_force_N vs ANSI limits.",
            },
            {
                "Requirement": "Maximum arrest distance",
                "Virtual test": "Setup 2 – Drop Test",
                "Notes": "Check arrest_distance_mm < 813 mm.",
            },
            {
                "Requirement": "Static strength of housing / anchors",
                "Virtual test": "Setup 1 – Static Load",
                "Notes": "Min safety factor ≥ 2.0 for all critical components.",
            },
            {
                "Requirement": "Functional state transitions",
                "Virtual test": "Setup 3 – State Machine Walkthrough",
                "Notes": "Verify IDLE → CLIMBING → TAKE → LOWER → IDLE under expected inputs.",
            },
            {
                "Requirement": "Emergency stop behavior",
                "Virtual test": "E-stop & interventions",
                "Notes": "Latency and resulting states must match spec.",
            },
            {
                "Requirement": "Misuse / foreseeable misuse",
                "Virtual test": "Misuse & edge cases",
                "Notes": "Document which scenarios are blocked vs allowed.",
            },
        ]
        df_std = pd.DataFrame(standards_rows)
        st.dataframe(df_std, hide_index=True)

    # ---------- TEST SESSION (LIVE + REPLAY) ----------
    elif setup.startswith("Test Session"):
        ts = _get_test_session_state()

        st.markdown("#### Live charts")
        if not ts["rows"]:
            st.info("No live data yet. Connect to a serial port and start recording to see live charts.")
        elif go is None:
            st.warning("Install `plotly` to see rich charts. For now, data is still being recorded to JSON.")
        else:
            # Build DataFrame of recent 10 seconds
            now = time.time()
            window = 10.0
            recent = [r for r in ts["rows"] if now - r["ts"] <= window]
            if recent:
                df_live = pd.DataFrame(recent)
                df_live["t_rel"] = df_live["ts"] - df_live["ts"].min()

                # Tension chart with threshold and voice/drop markers
                fig_tension = go.Figure()
                fig_tension.add_trace(
                    go.Scatter(x=df_live["t_rel"], y=df_live["tension"], mode="lines", name="Tension (N)")
                )
                fig_tension.add_hline(
                    y=fall_threshold,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Fall threshold",
                )
                for ev in ts["events"]:
                    if ev.get("type") == "voice":
                        t_ev = ev["ts"] - df_live["ts"].min()
                        fig_tension.add_vline(
                            x=t_ev,
                            line_dash="dot",
                            line_color="blue",
                            annotation_text=ev.get("command", "voice"),
                        )
                st.plotly_chart(fig_tension, use_container_width=True)

                # Rope/motor chart
                fig_rope = go.Figure()
                fig_rope.add_trace(
                    go.Scatter(x=df_live["t_rel"], y=df_live["rope_pos"], mode="lines", name="Rope pos"),
                )
                st.plotly_chart(fig_rope, use_container_width=True)

                # State timeline
                fig_state = go.Figure()
                states = df_live["state_int"].unique().tolist()
                for s_val in states:
                    mask = df_live["state_int"] == s_val
                    fig_state.add_trace(
                        go.Scatter(
                            x=df_live.loc[mask, "t_rel"],
                            y=[s_val] * mask.sum(),
                            mode="markers",
                            marker=dict(size=6),
                            name=f"state {s_val}",
                        )
                    )
                fig_state.update_yaxes(title_text="state_int")
                st.plotly_chart(fig_state, use_container_width=True)

        st.markdown("#### Session replay")
        _ensure_sessions_dir()
        files = sorted(glob(os.path.join("sessions", "*.json")))
        labels = [os.path.basename(f) for f in files]
        selected = st.selectbox("Recorded session", ["(none)"] + labels)
        if selected != "(none)":
            path = os.path.join("sessions", selected)
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            rows = doc.get("rows", [])
            events = doc.get("events", [])
            if go is None or not rows:
                st.warning("Install `plotly` to see replay charts, and ensure session has rows.")
            else:
                df = pd.DataFrame(rows)
                df["t_rel"] = df["ts"] - df["ts"].min()
                duration = float(df["t_rel"].max()) if not df.empty else 0.0
                playhead = st.slider("Playhead (s)", 0.0, max(duration, 0.1), 0.0, step=max(duration / 100, 0.1))

                # Build charts similar to live but static for full session
                fig_t = go.Figure()
                fig_t.add_trace(go.Scatter(x=df["t_rel"], y=df["tension"], mode="lines", name="Tension (N)"))
                fig_t.add_vline(x=playhead, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_t, use_container_width=True)

                fig_r = go.Figure()
                fig_r.add_trace(go.Scatter(x=df["t_rel"], y=df["rope_pos"], mode="lines", name="Rope pos"))
                fig_r.add_vline(x=playhead, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_r, use_container_width=True)

                fig_s = go.Figure()
                if "state_int" in df.columns:
                    for s_val in df["state_int"].unique().tolist():
                        mask = df["state_int"] == s_val
                        fig_s.add_trace(
                            go.Scatter(
                                x=df.loc[mask, "t_rel"],
                                y=[s_val] * mask.sum(),
                                mode="markers",
                                marker=dict(size=4),
                                name=f"state {s_val}",
                            )
                        )
                fig_s.add_vline(x=playhead, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_s, use_container_width=True)

                # Summary stats
                st.markdown("#### Session summary")
                duration_s = duration
                falls = int((df["tension"] > fall_threshold).sum()) if "tension" in df.columns else 0
                states_visited = sorted(set(df.get("state_int", []))) if "state_int" in df.columns else []
                voice_cmds = [e for e in events if e.get("type") == "voice"]
                drops = [e for e in events if e.get("type") == "drop_test"]
                st.write(f"- Duration: {duration_s:.1f} s")
                st.write(f"- Tension spikes > threshold: {falls}")
                st.write(f"- Distinct states visited: {states_visited}")
                st.write(f"- Voice commands: {len(voice_cmds)}")
                st.write(f"- Drop markers: {len(drops)}")

    # ---------- PID TUNER ----------
    elif setup.startswith("PID Tuner"):
        st.markdown("#### Tension PID tuner (embedded)")
        st.caption(
            "Mirror of `tools/aria_pid_tuner.py`, but inline. "
            "Tune Kp/Ki/Kd, preview a simple step response model, and write gains into STM32 firmware."
        )

        # Current firmware defaults
        default_kp = 0.08
        default_ki = 1.5
        default_kd = 0.0005

        kp = st.slider("Kp", 0.0, 1.0, float(st.session_state.get("pid_kp", default_kp)), step=0.01)
        ki = st.slider("Ki", 0.0, 5.0, float(st.session_state.get("pid_ki", default_ki)), step=0.05)
        kd = st.slider("Kd", 0.0, 0.01, float(st.session_state.get("pid_kd", default_kd)), step=0.0005)

        st.session_state["pid_kp"] = kp
        st.session_state["pid_ki"] = ki
        st.session_state["pid_kd"] = kd

        st.markdown("##### Step response (simple 1D model)")
        step_size = st.slider("Tension step (N)", 10.0, 80.0, 40.0, step=5.0)
        sim_duration = 5.0
        dt = 0.01
        n_steps = int(sim_duration / dt)

        # Very simple first-order plant + PID in velocity form (illustrative only)
        plant_tau = st.slider("Approx. plant time constant τ (s)", 0.1, 1.0, 0.4, step=0.05)
        plant_gain = st.slider("Approx. plant gain K (ΔN per Δu)", 0.5, 3.0, 1.0, step=0.1)

        t_vals = []
        y_vals = []
        u_vals = []
        y = 0.0
        i_term = 0.0
        prev_e = 0.0

        for i in range(n_steps):
            t_now = i * dt
            sp = step_size if t_now >= 0.2 else 0.0
            e = sp - y
            i_term += e * dt * ki
            de = (e - prev_e) / dt if dt > 0 else 0.0
            u = kp * e + i_term + kd * de
            prev_e = e

            # First-order plant: dy/dt = (-y + K*u)/τ
            dy = (-y + plant_gain * u) / plant_tau
            y += dy * dt

            t_vals.append(t_now)
            y_vals.append(y)
            u_vals.append(u)

        df_pid = pd.DataFrame({"time_s": t_vals, "tension_N": y_vals, "control_u": u_vals})
        st.line_chart(df_pid.set_index("time_s")[["tension_N"]], use_container_width=True)

        st.caption(
            "This is an approximate model for shape intuition only. "
            "Real tuning still depends on hardware tests."
        )

        st.markdown("##### Ziegler–Nichols suggestion")
        if st.button("Suggest gains (soft Z-N)", key="zn_suggest"):
            # Rough pseudo ZN based on time constant slider and gain
            T_c = plant_tau
            T_d = max(0.05, T_c * 0.2)
            K = max(0.1, plant_gain)
            Kp_zn = (1.2 / K) * (T_c / T_d) if T_d > 0 else 1.0 / K
            Ti = 2.0 * T_d
            Td = 0.5 * T_d
            Ki_zn = Kp_zn / Ti if Ti > 0 else 0.0
            Kd_zn = Kp_zn * Td
            SAFETY = 0.6
            st.session_state["pid_kp"] = Kp_zn * SAFETY
            st.session_state["pid_ki"] = Ki_zn * SAFETY
            st.session_state["pid_kd"] = Kd_zn * SAFETY
            st.success(
                f"Suggested Kp={st.session_state['pid_kp']:.4f}, "
                f"Ki={st.session_state['pid_ki']:.4f}, "
                f"Kd={st.session_state['pid_kd']:.6f} (scaled Z-N)"
            )
            st.experimental_rerun()

        st.markdown("##### Copy to firmware")
        st.caption(
            "Writes these gains into `firmware/stm32/aria_main.cpp` inside the `PID tensionPID{...}` initializer. "
            "You must recompile/flash STM32 after updating."
        )

        if st.button("Copy gains into firmware (aria_main.cpp)"):
            try:
                cpp_path = os.path.join("firmware", "stm32", "aria_main.cpp")
                with open(cpp_path, "r", encoding="utf-8") as f:
                    cpp = f.read()

                # Replace PID tensionPID initializer line
                import re

                pattern = r"PID\s+tensionPID\{[^}]*\};"
                repl = (
                    f"PID tensionPID{{.kp={kp:.6f}f,.ki={ki:.6f}f,.kd={kd:.6f}f}};"
                )
                new_cpp, n = re.subn(pattern, repl, cpp)
                if n == 0:
                    st.error(
                        "Could not find `PID tensionPID{...};` block in aria_main.cpp. "
                        "Update the pattern or edit manually."
                    )
                else:
                    with open(cpp_path, "w", encoding="utf-8") as f:
                        f.write(new_cpp)
                    st.success(
                        f"Wrote Kp={kp:.4f}, Ki={ki:.4f}, Kd={kd:.6f} into firmware/stm32/aria_main.cpp."
                    )
            except Exception as exc:
                st.error(f"Failed to update firmware file: {exc}")

    # ---------- HARDWARE BRING-UP ----------
    elif setup.startswith("Hardware Bring-Up"):
        st.markdown("#### Hardware bring-up checklist (before first power-on)")
        st.caption(
            "Work through each step in order before powering the full system. "
            "Results are stored locally in `bring_up_log.json` next to this dashboard script."
        )

        steps = [
            {
                "key": "load_cell_wiring",
                "label": "Load cell wiring verified",
                "doc": "docs/ARIA_SETUP.md#load-cell-wiring",
            },
            {
                "key": "encoder_wiring",
                "label": "Encoder wiring verified",
                "doc": "docs/ARIA_SETUP.md#encoder-wiring",
            },
            {
                "key": "uart_loopback",
                "label": "UART loopback test (STM32 ↔ ESP32)",
                "doc": "docs/ARIA_SETUP.md#uart-loopback-test",
            },
            {
                "key": "brake_gpio",
                "label": "Brake GPIO test (brake engages on boot)",
                "doc": "docs/ARIA_SETUP.md#brake-gpio-test",
            },
            {
                "key": "motor_direction",
                "label": "Motor direction test (UP/DOWN matches rope motion)",
                "doc": "docs/ARIA_SETUP.md#motor-direction-test",
            },
            {
                "key": "estop_circuit",
                "label": "E-stop circuit test (opens power / forces ESTOP)",
                "doc": "docs/REAL_TESTING_CHECKLIST.md#e-stop-circuit-test",
            },
        ]

        log = _load_bring_up_log()

        status_map = {
            "pass": "✅ Pass",
            "fail": "❌ Fail",
            "skip": "➖ Skip",
        }

        st.markdown("##### Steps")
        updated_log = dict(log)

        for step in steps:
            key = step["key"]
            current = log.get(key, "pending")

            with st.expander(step["label"], expanded=False):
                st.markdown(
                    f"[Open related docs]({step['doc']})  \n"
                    "Follow the instructions there, then record the outcome below."
                )

                cols = st.columns(4)
                with cols[0]:
                    st.write("Status:")
                    st.write(status_map.get(current, "Not set"))
                with cols[1]:
                    if st.button("Pass", key=f"{key}_pass"):
                        updated_log[key] = "pass"
                with cols[2]:
                    if st.button("Fail", key=f"{key}_fail"):
                        updated_log[key] = "fail"
                with cols[3]:
                    if st.button("Skip", key=f"{key}_skip"):
                        updated_log[key] = "skip"

        # Compute readiness
        total = len(steps)
        passed = sum(1 for s in steps if updated_log.get(s["key"]) == "pass")
        failed = sum(1 for s in steps if updated_log.get(s["key"]) == "fail")
        skipped = sum(1 for s in steps if updated_log.get(s["key"]) == "skip")
        pending = total - passed - failed - skipped

        readiness = 0.0 if total == 0 else (passed / total) * 100.0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Ready steps", f"{passed}/{total}")
        col_m2.metric("Failed", str(failed))
        col_m3.metric("Skipped", str(skipped))
        col_m4.metric("Readiness", f"{readiness:.0f}%")

        if pending > 0:
            st.info(f"{pending} step(s) still pending. Aim for 100% pass before first full-power test.")
        elif failed > 0:
            st.warning("At least one step is marked FAIL. Resolve issues before proceeding.")
        else:
            st.success("All steps are marked PASS or SKIP — hardware is ready from a checklist perspective.")

        # Persist any changes
        if updated_log != log:
            _save_bring_up_log(updated_log)
