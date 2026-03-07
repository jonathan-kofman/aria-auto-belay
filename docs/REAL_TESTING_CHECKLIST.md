# ARIA — Real Testing Checklist

Use this to confirm you have everything for **real** (hardware) testing and to run tests in order.

---

## Before real testing (virtual)

Do these in order. All can be run without hardware.

1. **Constants sync** — Python model and firmware must match:
   ```bash
   python tools/aria_constants_sync.py
   ```
   Fix any mismatches (or run with `--patch` to auto-update firmware). See CURSOR_GUIDE.md “Golden Rule”.

2. **Simulator** — Confirm state machine behavior:
   ```bash
   python tools/aria_simulator.py
   ```
   At the `ARIA>` prompt run: `scenario climb`, `scenario fall`, `scenario watch_me`, `scenario rest`, `scenario up`, then `status`. Confirm transitions match expectations. Type `quit` to exit.

3. **Dashboard** — Virtual setups must PASS before relying on real tests:
   ```bash
   streamlit run aria_dashboard.py
   ```
   (Or double-click `START_DASHBOARD.bat` on Windows.) Run **Setup 1**, **2A**, **2B**, **3** and get **PASS** (or use design suggestions to iterate).

---

## Hardware and firmware

- [ ] **STM32** flashed (`firmware/stm32/aria_main.cpp`). Load cell calibrated (HX711_OFFSET / HX711_SCALE in calibration).
- [ ] **ESP32** flashed (`firmware/esp32/aria_esp32_firmware.ino`), or use `aria_monitor.py --inject` to fake voice/CV.
- [ ] **Wiring:** Optional: flash `wiring_verify.cpp` once and confirm all peripherals PASS (see CURSOR_GUIDE.md).
- [ ] **Docs:** `docs/ARIA_SETUP.md` for flash order and wiring; `docs/edge_impulse_setup.md` if retraining voice.

---

## Tools for real testing (no dashboard needed for these)

| Tool | When to use |
|------|-------------|
| `tools/aria_monitor.py` | Live view of STM32 state, tension, motor %. Use `--inject` to send fake voice if ESP32 not connected. |
| `tools/aria_test_harness.py --run all` | Automated STM32 scenarios (climb, fall, watch_me, rest, up). Run before a test day. |
| `tools/aria_pid_tuner.py` | Tune PID (Kp, Ki, Kd) for climbing tension; copy values to simulator and aria_main.cpp. |
| `tools/aria_collect_audio.py` | Record voice samples for Edge Impulse if improving wake words. |

---

## Physical test setups (what the dashboard simulates)

| Setup | What you do in real life | Dashboard equivalent |
|-------|---------------------------|------------------------|
| **Setup 1 – Static** | Load frame: apply loads (e.g. 500–8000 N), check no yield, SF ≥ 2. | Dashboard Setup 1: geometry sliders + load steps; calibrate geometry to match your parts. |
| **Setup 2A – False trip** | Slow movement at ~0.3g; trigger must **not** fire. | Dashboard 2A: real physics check. |
| **Setup 2B – Drop** | Drop test: measure peak force, arrest distance; compare to ANSI. | Dashboard 2B: tune absorber k/c to match one real test, then use for design changes. |
| **Setup 3 – Functional** | Bench: full state machine (IDLE→CLIMBING→TAKE→LOWER) with real motor/load cell. | Dashboard 3 + `aria_test_harness.py --run all` + `aria_monitor.py` for live data. |

---

## Optional / nice-to-have (not required for real testing)

- **Record real test results:** Note date, setup, pass/fail, measured peak (N), arrest distance (mm). Tune dashboard k/c to match, then reuse dashboard for design iteration.
- **Export constants:** When you lock firmware constants, copy them into `aria_simulator.py` and (if you add it) a config used by the dashboard so virtual and real stay in sync.

---

## Quick reference: run order for a test day

1. Flash STM32 (and ESP32 if used). Calibrate load cell if first time or new sensor.
2. `python tools/aria_test_harness.py --run all` → all scenarios PASS.
3. `python tools/aria_monitor.py` (or `--inject` if no ESP32) for live checks.
4. Run physical Setup 1 / 2 / 3 per your test plan. Use dashboard to compare or calibrate (e.g. Setup 2 k/c after first drop test).
