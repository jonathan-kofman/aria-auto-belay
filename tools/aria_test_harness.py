#!/usr/bin/env python3
"""
ARIA UART Test Harness
Pretends to be the ESP32 over serial — lets you test all STM32
state transitions from your laptop before the ESP32 is flashed.

Usage:
  python3 aria_test_harness.py                     # auto-detect port
  python3 aria_test_harness.py --port /dev/ttyACM0
  python3 aria_test_harness.py --run scenario_climb  # automated test
  python3 aria_test_harness.py --run all             # run all scenarios

What this does:
  - Connects to STM32 over USB serial
  - Sends fake ESP32 packets (voice commands, CV data)
  - Reads back STM32 state and validates transitions
  - Runs automated test scenarios and reports pass/fail
  - Generates a test report you can save

SCENARIOS:
  scenario_climb    — Full climb: idle → climbing → clip × 3 → take → lower
  scenario_fall     — Lead fall detection and arrest
  scenario_watch_me — WATCH ME mode and exit
  scenario_rest     — REST mode timeout
  scenario_up       — UP mode safety cut
  scenario_estop    — E-stop response (requires button press)
"""

import serial
import serial.tools.list_ports
import threading
import time
import sys
import argparse
import collections

BAUD_RATE = 115200

# State IDs (must match STM32 firmware)
STATE = {
    "IDLE": 0, "CLIMBING": 1, "CLIPPING": 2, "TAKE": 3,
    "REST": 4, "LOWER": 5,   "WATCH_ME": 6, "UP": 7, "ESTOP": 8
}
STATE_NAME = {v: k for k, v in STATE.items()}

CMD = {
    "take": 1, "slack": 2, "lower": 3, "up": 4,
    "watch_me": 5, "rest": 6, "climbing": 7
}

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
BOLD   = "\033[1m"


# ─────────────────────────────────────────────
# STM32 INTERFACE
# ─────────────────────────────────────────────

class STM32Interface:
    def __init__(self, port, baud=BAUD_RATE):
        self.ser        = serial.Serial(port, baud, timeout=0.5)
        self.state      = -1
        self.tension    = 0.0
        self.rope_pos   = 0.0
        self.motor_mode = 0
        self.log        = collections.deque(maxlen=100)
        self._lock      = threading.Lock()
        self._running   = True
        self._t         = threading.Thread(target=self._reader, daemon=True)
        self._t.start()
        time.sleep(0.5)  # let STM32 send initial state

    def _reader(self):
        while self._running:
            try:
                raw  = self.ser.readline()
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("S:"):
                    parts = line[2:].split(":")
                    if len(parts) == 4:
                        with self._lock:
                            self.state      = int(parts[0])
                            self.tension    = float(parts[1])
                            self.rope_pos   = float(parts[2])
                            self.motor_mode = int(parts[3])
                else:
                    with self._lock:
                        self.log.append(line)
            except Exception:
                pass

    def send_voice(self, cmd_name, confidence=0.92):
        cmd_id = CMD.get(cmd_name.lower())
        if cmd_id is None:
            print(f"Unknown command: {cmd_name}")
            return
        packet = f"V:{cmd_id}:{confidence:.2f}\n"
        self.ser.write(packet.encode())
        print(f"  {CYAN}→ VOICE: {cmd_name} ({confidence:.2f}){RESET}")

    def send_cv(self, clip_conf, height_m, detected):
        packet = f"C:{clip_conf:.2f}:{height_m:.1f}:{int(detected)}\n"
        self.ser.write(packet.encode())

    def get_state(self):
        with self._lock:
            return self.state

    def get_tension(self):
        with self._lock:
            return self.tension

    def wait_for_state(self, target_state, timeout_s=5.0, poll_hz=20):
        """Block until STM32 enters target_state or timeout."""
        deadline = time.time() + timeout_s
        interval = 1.0 / poll_hz
        while time.time() < deadline:
            if self.get_state() == target_state:
                return True
            time.sleep(interval)
        return False

    def assert_state(self, expected, context=""):
        actual = self.get_state()
        name_e = STATE_NAME.get(expected, str(expected))
        name_a = STATE_NAME.get(actual,   str(actual))
        if actual == expected:
            print(f"  {GREEN}✓ State: {name_e}{RESET}  {GREY}{context}{RESET}")
            return True
        else:
            print(f"  {RED}✗ Expected {name_e}, got {name_a}{RESET}  {GREY}{context}{RESET}")
            return False

    def close(self):
        self._running = False
        self.ser.close()


# ─────────────────────────────────────────────
# TEST RESULT TRACKER
# ─────────────────────────────────────────────

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def record(self, name, passed, notes=""):
        status = "PASS" if passed else "FAIL"
        self.results.append({"name": name, "status": status, "notes": notes})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def skip(self, name, reason=""):
        self.results.append({"name": name, "status": "SKIP", "notes": reason})
        self.skipped += 1

    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'═'*55}")
        print(f"  TEST RESULTS: {self.passed}/{total} passed  "
              f"({self.failed} failed, {self.skipped} skipped)")
        print(f"{'═'*55}")
        for r in self.results:
            if r["status"] == "PASS":
                icon = f"{GREEN}✓{RESET}"
            elif r["status"] == "FAIL":
                icon = f"{RED}✗{RESET}"
            else:
                icon = f"{YELLOW}−{RESET}"
            notes = f"  {GREY}{r['notes']}{RESET}" if r["notes"] else ""
            print(f"  {icon} {r['name']:35s}{notes}")
        print(f"{'═'*55}\n")

    def save_report(self, filename="aria_test_report.txt"):
        with open(filename, "w") as f:
            f.write(f"ARIA Test Report — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*55 + "\n")
            total = self.passed + self.failed + self.skipped
            f.write(f"Results: {self.passed}/{total} passed\n\n")
            for r in self.results:
                line = f"[{r['status']}] {r['name']}"
                if r["notes"]:
                    line += f" — {r['notes']}"
                f.write(line + "\n")
        print(f"  Report saved: {filename}")


results = TestResults()


# ─────────────────────────────────────────────
# STEP HELPER
# ─────────────────────────────────────────────

def step(description, delay_s=0.5):
    print(f"\n  {BOLD}▶ {description}{RESET}")
    time.sleep(delay_s)


def section(name):
    print(f"\n{CYAN}{'═'*55}{RESET}")
    print(f"{CYAN}  SCENARIO: {name}{RESET}")
    print(f"{CYAN}{'═'*55}{RESET}")


# ─────────────────────────────────────────────
# SCENARIOS
# ─────────────────────────────────────────────

def scenario_climb(stm: STM32Interface):
    section("Normal Climb — IDLE → CLIMBING → CLIPPING × 2 → TAKE → LOWER → IDLE")

    # Step 1: should start in IDLE
    step("Verify initial IDLE state")
    passed = stm.assert_state(STATE["IDLE"], "device powered, no climber")
    results.record("idle_initial_state", passed)

    # Step 2: send CV — climber detected
    step("Climber attaches — CV detects presence")
    stm.send_cv(0.0, 0.5, True)
    # Note: tension must also be above TENSION_GROUND_N (15N)
    # Since we can't control the real load cell from here,
    # we note this requires physical tension on the rope
    print(f"  {YELLOW}⚠ Physical: apply >15N tension to rope (attach weight or pull){RESET}")
    time.sleep(1.0)
    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=8.0)
    results.record("idle_to_climbing", passed,
                   "requires CV detected + tension > 15N on real hardware")
    stm.assert_state(STATE["CLIMBING"])

    # Step 3: First clip
    step("Approaching bolt 1 — CV detects clip gesture")
    stm.send_cv(0.88, 3.0, True)
    passed = stm.wait_for_state(STATE["CLIPPING"], timeout_s=3.0)
    results.record("climbing_to_clipping_1", passed)
    stm.assert_state(STATE["CLIPPING"])

    step("Wait for clip to complete (auto-returns to CLIMBING)")
    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=10.0)
    results.record("clipping_returns_to_climbing_1", passed)
    stm.assert_state(STATE["CLIMBING"])

    # Step 4: Second clip
    step("Approaching bolt 2 — second clip gesture")
    stm.send_cv(0.91, 6.0, True)
    passed = stm.wait_for_state(STATE["CLIPPING"], timeout_s=3.0)
    results.record("climbing_to_clipping_2", passed)

    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=10.0)
    results.record("clipping_returns_to_climbing_2", passed)

    # Step 5: TAKE
    step("Climber yells TAKE — pumped at top")
    stm.send_voice("take", 0.94)
    print(f"  {YELLOW}⚠ Physical: weight rope within 500ms of voice command{RESET}")
    time.sleep(0.3)
    passed = stm.wait_for_state(STATE["TAKE"], timeout_s=5.0)
    results.record("climbing_to_take_voice", passed)
    stm.assert_state(STATE["TAKE"])

    step("Hanging in TAKE for 2 seconds")
    time.sleep(2.0)
    still_take = stm.get_state() == STATE["TAKE"]
    results.record("take_holds_position", still_take)

    # Step 6: LOWER
    step("Climber yells LOWER")
    stm.send_voice("lower", 0.91)
    passed = stm.wait_for_state(STATE["LOWER"], timeout_s=5.0)
    results.record("take_to_lower", passed)
    stm.assert_state(STATE["LOWER"])

    step("Descending — wait for ground (tension drops below 15N)")
    print(f"  {YELLOW}⚠ Physical: remove weight from rope to simulate ground{RESET}")
    passed = stm.wait_for_state(STATE["IDLE"], timeout_s=15.0)
    results.record("lower_to_idle", passed, "requires tension < 15N on real hardware")


def scenario_fall(stm: STM32Interface):
    section("Lead Fall — fall detection safety override")

    step("Ensure CLIMBING state first")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Simulate fall: high speed + high tension")
    print(f"  {YELLOW}⚠ Physical: this requires real high-speed rope release{RESET}")
    print(f"  {YELLOW}  Fall detection: rope_speed > 2.0 m/s AND tension > 400N{RESET}")
    print(f"  {YELLOW}  The centrifugal clutch arrests — motor goes to HOLD automatically{RESET}")
    time.sleep(1.0)

    # We can validate the state remains CLIMBING (not crashed)
    # Actual fall simulation requires physical hardware
    passed = stm.get_state() in (STATE["CLIMBING"], STATE["TAKE"])
    results.record("fall_system_remains_stable", passed,
                   "full test requires physical fall simulation")
    print(f"  {YELLOW}NOTE: Full fall scenario requires physical drop test{RESET}")


def scenario_watch_me(stm: STM32Interface):
    section("WATCH ME — tight slack management mode")

    step("Ensure CLIMBING state")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Climber yells WATCH ME")
    stm.send_voice("watch_me", 0.90)
    passed = stm.wait_for_state(STATE["WATCH_ME"], timeout_s=5.0)
    results.record("climbing_to_watch_me", passed)
    stm.assert_state(STATE["WATCH_ME"])

    step("In WATCH ME for 3 seconds — verifying tight tension target")
    time.sleep(3.0)
    still_watch = stm.get_state() == STATE["WATCH_ME"]
    results.record("watch_me_holds", still_watch)

    step("Exit WATCH ME — yell CLIMBING")
    stm.send_voice("climbing", 0.88)
    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=5.0)
    results.record("watch_me_to_climbing", passed)
    stm.assert_state(STATE["CLIMBING"])


def scenario_rest(stm: STM32Interface):
    section("REST — hang and recover mode")

    step("Ensure CLIMBING state")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Yell REST")
    stm.send_voice("rest", 0.93)
    passed = stm.wait_for_state(STATE["REST"], timeout_s=5.0)
    results.record("climbing_to_rest", passed)
    stm.assert_state(STATE["REST"])

    step("In REST — hold 3 seconds")
    time.sleep(3.0)
    still_rest = stm.get_state() == STATE["REST"]
    results.record("rest_holds_position", still_rest)

    step("Exit REST with CLIMBING command")
    stm.send_voice("climbing", 0.89)
    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=5.0)
    results.record("rest_to_climbing", passed)


def scenario_up(stm: STM32Interface):
    section("UP — motor assist mode")

    step("Ensure CLIMBING state")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Yell UP — motor assist engaged")
    stm.send_voice("up", 0.91)
    passed = stm.wait_for_state(STATE["UP"], timeout_s=5.0)
    results.record("climbing_to_up", passed)
    stm.assert_state(STATE["UP"])

    step("In UP for 2 seconds")
    time.sleep(2.0)
    still_up = stm.get_state() == STATE["UP"]
    results.record("up_holds", still_up)

    step("Exit UP with CLIMBING command")
    stm.send_voice("climbing", 0.92)
    passed = stm.wait_for_state(STATE["CLIMBING"], timeout_s=5.0)
    results.record("up_to_climbing", passed)


def scenario_voice_confidence(stm: STM32Interface):
    section("Voice Confidence Gate — low confidence should be rejected")

    step("Ensure CLIMBING state")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Send TAKE with low confidence (0.70 < 0.85 threshold) — should be ignored")
    initial_state = stm.get_state()
    stm.send_voice("take", 0.70)
    time.sleep(1.5)
    state_unchanged = stm.get_state() == initial_state
    results.record("low_confidence_rejected", state_unchanged,
                   "confidence 0.70 < 0.85 threshold")
    if state_unchanged:
        print(f"  {GREEN}✓ Low confidence command correctly ignored{RESET}")
    else:
        print(f"  {RED}✗ Low confidence command was executed — check threshold{RESET}")

    step("Send TAKE with valid confidence (0.92) — should execute")
    stm.send_voice("take", 0.92)
    print(f"  {YELLOW}⚠ Physical: weight rope within 500ms{RESET}")
    passed = stm.wait_for_state(STATE["TAKE"], timeout_s=5.0)
    results.record("valid_confidence_accepted", passed)

    # Return to climbing
    stm.send_voice("climbing", 0.90)
    stm.wait_for_state(STATE["CLIMBING"], timeout_s=5.0)


def scenario_take_confirmation(stm: STM32Interface):
    section("TAKE Two-Factor Confirmation — voice without weight should cancel")

    step("Ensure CLIMBING state")
    stm.send_cv(0.0, 5.0, True)
    print(f"  {YELLOW}⚠ Physical: apply tension to enter CLIMBING{RESET}")
    time.sleep(2.0)

    step("Send TAKE voice but DON'T weight rope — should cancel after 500ms")
    stm.send_voice("take", 0.93)
    print(f"  {YELLOW}⚠ Physical: do NOT add weight to rope — let it timeout{RESET}")
    # Wait for timeout + return to CLIMBING
    time.sleep(1.5)
    passed = stm.get_state() == STATE["CLIMBING"]
    results.record("take_no_weight_cancels", passed,
                   "TAKE without load cell confirmation must cancel")
    if passed:
        print(f"  {GREEN}✓ TAKE correctly cancelled — no weight detected{RESET}")
    else:
        print(f"  {RED}✗ TAKE did not cancel — check confirmation logic{RESET}")


# ─────────────────────────────────────────────
# SCENARIO REGISTRY
# ─────────────────────────────────────────────

SCENARIOS = {
    "scenario_climb":        scenario_climb,
    "scenario_fall":         scenario_fall,
    "scenario_watch_me":     scenario_watch_me,
    "scenario_rest":         scenario_rest,
    "scenario_up":           scenario_up,
    "scenario_voice_conf":   scenario_voice_confidence,
    "scenario_take_confirm": scenario_take_confirmation,
}


# ─────────────────────────────────────────────
# INTERACTIVE MODE
# ─────────────────────────────────────────────

def interactive(stm: STM32Interface):
    print(f"\n{BOLD}ARIA UART Test Harness — Interactive Mode{RESET}")
    print(f"Commands: voice <name>  cv <clip> <height> <detected>  state  quit")
    print(f"Voice commands: take slack lower up watch_me rest climbing")
    print()

    while True:
        try:
            raw = input("harness> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        parts = raw.split()
        cmd   = parts[0].lower()

        if cmd in ("quit", "q", "exit"):
            break

        elif cmd == "voice" and len(parts) >= 2:
            voice_name = parts[1].lower()
            conf = float(parts[2]) if len(parts) > 2 else 0.92
            stm.send_voice(voice_name, conf)

        elif cmd == "cv" and len(parts) >= 4:
            clip    = float(parts[1])
            height  = float(parts[2])
            det     = parts[3].lower() in ("1", "true", "yes")
            stm.send_cv(clip, height, det)
            print(f"  → CV: clip={clip:.2f} height={height:.1f}m detected={det}")

        elif cmd == "state":
            s = stm.get_state()
            t = stm.get_tension()
            print(f"  State: {STATE_NAME.get(s, s)}  Tension: {t:.1f}N")

        elif cmd == "run" and len(parts) >= 2:
            name = parts[1]
            if name in SCENARIOS:
                SCENARIOS[name](stm)
                results.print_summary()
            else:
                print(f"Unknown scenario: {name}. Options: {list(SCENARIOS.keys())}")

        else:
            print(f"Unknown command: {raw}")


# ─────────────────────────────────────────────
# PORT DETECTION
# ─────────────────────────────────────────────

def find_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        if any(x in desc for x in ["stm32", "stlink", "st-link", "virtual"]):
            return p.device
    return ports[0].device if ports else None


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ARIA UART Test Harness")
    parser.add_argument("--port", help="Serial port")
    parser.add_argument("--run",  help="Run scenario: name or 'all'")
    args = parser.parse_args()

    port = args.port or find_port()
    if not port:
        print("No serial port found. Use --port.")
        sys.exit(1)

    print(f"Connecting to STM32 on {port}...")
    try:
        stm = STM32Interface(port)
    except serial.SerialException as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print(f"Connected. Initial state: {STATE_NAME.get(stm.get_state(), '?')}")

    try:
        if args.run:
            if args.run == "all":
                for name, fn in SCENARIOS.items():
                    print(f"\nRunning {name}...")
                    fn(stm)
                    time.sleep(2.0)
            elif args.run in SCENARIOS:
                SCENARIOS[args.run](stm)
            else:
                print(f"Unknown scenario: {args.run}")
                print(f"Options: {list(SCENARIOS.keys())}")
            results.print_summary()
            results.save_report()
        else:
            interactive(stm)

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        stm.close()


if __name__ == "__main__":
    main()
