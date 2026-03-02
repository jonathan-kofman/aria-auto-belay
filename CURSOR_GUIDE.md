# ARIA — Cursor Developer Guide
### Everything you need to know to work on this repo in Cursor

---

## Repo Structure at a Glance

```
aria-auto-belay/
├── cad/fusion_scripts/        ← Fusion 360 Python scripts (run inside Fusion, not Cursor)
├── docs/                      ← Setup and hardware guides (reference only)
├── firmware/
│   ├── esp32/                 ← AI brain (voice + CV) firmware
│   └── stm32/                 ← Motor control + safety firmware
└── tools/                     ← Python dev tools (run from Cursor terminal)
```

---

## cad/fusion_scripts/ — 6 files

These are NOT run from Cursor. They run inside Fusion 360 via the Scripts panel.

| File | What it builds |
|---|---|
| `aria_housing_complete.py` | Main housing box, bearing bores, boss features |
| `aria_rope_spool_complete.py` | Hub, flanges, bolt circle for ratchet ring |
| `aria_ratchet_shaft_complete.py` | Ratchet ring (24 teeth) + main shaft together |
| `aria_cam_collar_complete.py` | Cam collar with two 180°-opposite ramp blocks |
| `aria_small_parts_complete.py` | Flyweight, trip lever, blocker bar, 2× pawls |
| `aria_support_complete.py` | End cap, wall bracket, motor mount, rope guide |

**When to open in Cursor:** Only if you need to edit geometry parameters (e.g., change
tooth count, ramp rise from 3.5 mm to 4 mm, adjust spool OD). Cursor's AI can help you
find and change the right variable.

---

## docs/ — 2 files

Pure reference markdown. Read these; don't run them.

### ARIA_SETUP.md
- Full first-time setup guide for flashing and wiring the hardware.
- Covers STM32 flash order, calibration sequence, ESP32 flash, serial port setup.
- **When to use:** Any time you sit down with new hardware or a fresh STM32/ESP32 and
  need the exact step-by-step sequence to get ARIA running.

### REAL_TESTING_CHECKLIST.md
- Checklist for real (hardware) testing: what to run before/during test day.
- Maps dashboard Setups 1/2/3 to physical tests and lists tools (monitor, test harness, PID tuner).
- **When to use:** Before a physical test day; when checking that nothing is missing for real testing.

### edge_impulse_setup.md
- Instructions for training and deploying the Edge Impulse ML model on the ESP32-S3.
- Covers audio dataset collection, model training, export to `.zip`, and flashing to ESP32.
- **When to use:** When you're ready to train or retrain the voice recognition model
  (e.g., you want to add a new command or improve accuracy).

---

## firmware/stm32/ — 5 files

This is the motor brain. Runs on the STM32 microcontroller. Handles the state machine,
motor control, safety, and load cell. Flashed via Arduino IDE or PlatformIO — edit in
Cursor, flash externally.

### aria_main.cpp ← START HERE for STM32
- **What it is:** Main entry point. Ties together state machine, SimpleFOC motor control,
  load cell readings (HX711), serial comms with ESP32, and safety watchdog.
- **What it does every loop tick:**
  1. Reads load cell tension.
  2. Receives voice/CV commands from ESP32 over UART.
  3. Runs the state machine (IDLE → CLIMBING → CLIPPING → TAKE → REST → LOWER → WATCH_ME → UP).
  4. Sends motor commands to SimpleFOC.
  5. Prints status to serial at 115200 baud.
- **First time setup order** (written in the file header):
  1. Flash firmware.
  2. Open serial at 115200.
  3. Type `cal` within 3 seconds → calibrates load cell.
  4. Copy printed `HX711_OFFSET` / `HX711_SCALE` constants back into `calibration.cpp`.
  5. Reflash → motor alignment runs once automatically.
  6. Normal operation begins.
- **Output to watch:** Serial prints show current state, tension (N), motor output %,
  and any fault codes. If tension reads 0 constantly, calibration hasn't been run yet.

### calibration.cpp
- **What it is:** HX711 load cell calibration routine + motor encoder alignment.
- **When to run:** Only on first flash or if you swap out the load cell or motor.
- **Output:** Prints `HX711_OFFSET = XXXXX` and `HX711_SCALE = X.XXX` to serial.
  Copy those exact numbers back into this file before your next flash.
- **To force motor re-alignment:** Uncomment `#define MOTOR_ALIGN_MODE` and reflash.

### safety.cpp + safety.h
- **What it is:** Watchdog and fault recovery logic. Runs as a parallel safety layer.
- **What it watches for:**
  - Load cell over 8,000 N → ESTOP.
  - Rope speed > 2.0 m/s + tension > 400 N → fall detection → motor cuts to 0%,
    mechanical clutch takes over.
  - State stuck in TAKE or REST longer than timeout → auto-release.
  - Serial comms from ESP32 lost > 2 seconds → safe hold mode.
- **Output:** Fault codes printed to serial.
- **When to edit:** If you change ANSI limits, tighten watchdog timeout, or add a new
  fault condition.

### wiring_verify.cpp + wiring_verify.h
- **What it is:** Standalone diagnostic sketch. Flash temporarily to confirm all hardware
  is wired correctly before flashing real firmware.
- **When to run:** Any time you wire up a new board or suspect a connection problem.
  Flash this first, check outputs, then flash aria_main.cpp.
- **What it checks:** Load cell responds, motor encoder counts, UART RX from ESP32 gets
  data, all GPIO pins read expected logic levels.
- **Output:** Prints PASS/FAIL per peripheral to serial at 115200. `HX711: FAIL` means
  load cell wiring is wrong before you ever try the state machine.

---

## firmware/esp32/ — 1 file

### aria_esp32_firmware.ino
- **What it is:** The AI perception brain. Runs on the ESP32-S3.
- **Handles:**
  - Voice command recognition via Edge Impulse model
    (take, lower, rest, watch me, up, climbing, slack).
  - CV clip gesture detection via camera.
  - Sends recognized commands to STM32 over UART as structured packets.
- **When it runs:** Always running alongside STM32. They communicate over a serial UART
  wire between the two boards.
- **Output:** Sends packets like `CMD:TAKE:0.92` (command : confidence) to STM32 over UART.
  Also prints debug info to its own serial port.
- **When to edit in Cursor:** When you add a new voice command, change the confidence
  threshold, or swap out the Edge Impulse model after retraining.
- **IMPORTANT:** Voice confidence threshold in `aria_simulator.py` (`VOICE_CONFIDENCE_MIN
  = 0.85`) must match the threshold in this file or you'll get mismatches between sim
  and real hardware.

---

## tools/ — 5 files

All run from Cursor terminal with `python3 <filename>`. No hardware needed for most.

---

### aria_simulator.py ← MOST IMPORTANT TOOL RIGHT NOW

- **What it is:** Full software replica of the ARIA state machine in Python.
  No hardware needed. This is what the Streamlit dashboard calls into.
- **How to run:**
  ```
  python3 tools/aria_simulator.py
  ```
- **Commands:**
  ```
  voice take                        → inject "take" voice command
  voice watch me                    → inject "watch me"
  sensor load_cell_n=680            → fake 680 N tension
  sensor cv_climber_detected=True   → fake climber on wall
  sensor cv_clip_confidence=0.9     → fake clip gesture
  scenario climb                    → run full automated climb sequence
  scenario fall                     → simulate a lead fall
  scenario watch_me                 → simulate WATCH ME crux attempt
  status                            → print all sensor values + state
  log                               → show last 10 state transitions
  ```
- **What output means:**
  - `[STATE]` cyan: state transitions e.g. `CLIMBING → TAKE`. Key logic events.
  - `[CMD]` green: confirmed commands e.g. `TAKE confirmed — load=680N (320ms)`.
  - `[WARN]` yellow: non-critical issues e.g. `TAKE timed out — no weight on rope`.
  - `[SAFE]` red: safety events e.g. `FALL DETECTED — clutch engaging`.
    If you see these unexpectedly, a threshold needs tuning.
- **Why it matters:** Every state transition, threshold, and timeout mirrors
  aria_main.cpp exactly. If something works here, it should work on hardware.
  If it doesn't work here, don't flash hardware yet.
- **Key constants to tune** (tune here first, then mirror into STM32):
  ```python
  TENSION_BASELINE_N       = 40.0   # climbing tension target
  TENSION_TAKE_THRESHOLD_N = 200.0  # load needed to confirm TAKE
  TENSION_FALL_THRESHOLD_N = 400.0  # fall detection threshold
  CLIP_DETECT_CONFIDENCE   = 0.75   # CV clip confidence minimum
  VOICE_CONFIDENCE_MIN     = 0.85   # voice minimum confidence
  TAKE_CONFIRM_WINDOW_MS   = 500    # ms to confirm TAKE with load
  PID_KP = 2.5 / PID_KI = 0.8 / PID_KD = 0.1
  ```

---

### aria_monitor.py ← USE WHEN STM32 IS CONNECTED

- **What it is:** Real-time terminal dashboard. Reads live data from STM32 over USB
  serial and displays color-coded UI.
- **How to run:**
  ```
  python3 tools/aria_monitor.py                       # auto-detect port
  python3 tools/aria_monitor.py --port COM3           # Windows
  python3 tools/aria_monitor.py --port /dev/ttyACM0   # Linux
  ```
- **Also works as ESP32 simulator** (no ESP32 hardware needed yet):
  ```
  python3 tools/aria_monitor.py --inject
  ```
  Type fake voice commands from your laptop → sent to real STM32 over serial.
  Useful for testing state transitions with real motor hardware but no ESP32 yet.
- **What it shows:**
  - Current ARIA state (color coded).
  - Live rope tension (N) with bar graph.
  - Rope speed and position.
  - Motor mode and output %.
  - Last 20 log lines from STM32.
  - Rolling min/max/avg tension stats.
- **Output means:**
  - Tension stuck at 0 with climber attached → calibration failed.
  - State never leaves IDLE → cv_climber_detected is false or tension below 15 N.
  - TAKE never confirms → tension not hitting 200 N, load cell needs recalibration.
- **No pip installs needed** — pure Python stdlib.

---

### aria_test_harness.py ← USE FOR AUTOMATED STM32 TESTING

- **What it is:** Pretends to be the ESP32 over serial. Sends scripted fake packets to
  STM32 and reads back responses to validate every state transition automatically.
- **How to run:**
  ```
  python3 tools/aria_test_harness.py                           # auto-detect port
  python3 tools/aria_test_harness.py --run scenario_climb      # one scenario
  python3 tools/aria_test_harness.py --run all                 # all scenarios
  ```
- **Scenarios:**
  - `scenario_climb` — full climb: idle → climbing → clip ×3 → take → lower.
  - `scenario_fall` — lead fall detection and arrest.
  - `scenario_watch_me` — WATCH ME mode and exit.
  - `scenario_rest` — REST mode timeout.
  - `scenario_up` — UP mode safety cut.
- **Output:** PASS/FAIL per scenario with timestamps. Generates a saveable test report.
  A FAIL = STM32 responded with unexpected state → check thresholds in aria_main.cpp.
- **When to run:** Before any physical test day. If all scenarios pass here, firmware
  logic is solid before you put weight on the rope.

---

### aria_pid_tuner.py

- **What it is:** Tool to tune the three PID constants (Kp, Ki, Kd) that control rope
  tension during climbing.
- **Why PID matters:** In CLIMBING mode, motor continuously adjusts to maintain 40 N
  tension. Too aggressive (high Kp) = rope jerks. Too slow = too much slack.
- **Current values:**
  ```
  PID_KP = 2.5
  PID_KI = 0.8
  PID_KD = 0.1
  ```
- **How to use:** Run it, enter a step change in tension setpoint, watch the simulated
  response. Tune until the step response settles quickly without oscillating. Copy
  winning values into both aria_simulator.py and aria_main.cpp.
- **When to run:** After hardware is assembled and you're getting oscillation or
  sluggishness in real climbing mode.

---

### aria_collect_audio.py

- **What it is:** Records audio samples from a microphone and labels them for Edge
  Impulse training dataset.
- **How to run:**
  ```
  python3 tools/aria_collect_audio.py
  ```
- **When to use:** When voice model needs more training data (e.g., "take" getting false
  positives, "watch me" not recognized reliably). Record ~50 samples per command word,
  upload `.wav` files to Edge Impulse, retrain, export, reflash ESP32.
- **Output:** Labeled `.wav` files organized by command word, ready for Edge Impulse
  dataset uploader.

---

## Workflow by Phase

### Phase 1 — No hardware yet (current phase)
```
python3 tools/aria_simulator.py       ← test all state logic in CLI
streamlit run aria_dashboard.py       ← visual test dashboard
```
Edit thresholds in aria_simulator.py, rerun, iterate until all scenarios behave
correctly before touching any hardware.

### Phase 2 — STM32 connected, no ESP32 yet
```
python3 tools/aria_monitor.py --inject   ← fake ESP32, real STM32 motor
python3 tools/aria_test_harness.py --run all
```
Flash firmware/stm32/ via Arduino IDE or PlatformIO. Use monitor to watch live state.
Use test harness to run all scenarios automatically.

### Phase 3 — Full system (both boards connected)
```
python3 tools/aria_monitor.py            ← live dashboard
python3 tools/aria_test_harness.py --run all
```
ARIA running as designed: ESP32 → UART → STM32 → motor. Monitor shows everything live.

### Phase 4 — Voice model needs improvement
```
python3 tools/aria_collect_audio.py      ← record new samples
```
Upload to Edge Impulse → retrain → export .zip → reflash ESP32.

### Phase 5 — PID feels wrong on real hardware
```
python3 tools/aria_pid_tuner.py          ← find better Kp/Ki/Kd
```
Copy winning constants into aria_simulator.py AND aria_main.cpp, reflash STM32.

---

## The Golden Rule for Cursor

Every constant in aria_simulator.py also exists in aria_main.cpp. They must always match
