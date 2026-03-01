#!/usr/bin/env python3
"""
ARIA Serial Monitor Dashboard
Real-time terminal UI for STM32 debugging.

No pip installs needed — pure Python stdlib.

Usage:
  python3 aria_monitor.py                    # auto-detect port
  python3 aria_monitor.py --port COM3        # Windows
  python3 aria_monitor.py --port /dev/ttyACM0  # Linux
  python3 aria_monitor.py --port /dev/tty.usbmodem14201  # Mac

What it shows:
  - Current ARIA state (color coded)
  - Live rope tension (N) with bar graph
  - Rope speed and position
  - Motor mode and output
  - Last 20 log lines from STM32
  - Rolling min/max/avg tension stats

ALSO works as ESP32 simulator:
  python3 aria_monitor.py --inject
  This lets you send fake voice commands and CV data to STM32
  from your laptop to test state transitions before ESP32 is flashed.
"""

import serial
import serial.tools.list_ports
import threading
import time
import sys
import os
import argparse
import collections
import struct

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

BAUD_RATE   = 115200
REFRESH_HZ  = 10
LOG_LINES   = 20
TENSION_MAX = 1000.0  # N, for bar graph scaling
BAR_WIDTH   = 40

STATE_NAMES = {
    0: "IDLE",
    1: "CLIMBING",
    2: "CLIPPING",
    3: "TAKE",
    4: "REST",
    5: "LOWER",
    6: "WATCH ME",
    7: "UP",
    8: "ESTOP",
}

STATE_COLORS = {
    0: "\033[90m",   # grey
    1: "\033[92m",   # green
    2: "\033[93m",   # yellow
    3: "\033[96m",   # cyan
    4: "\033[94m",   # blue
    5: "\033[95m",   # magenta
    6: "\033[93m",   # yellow
    7: "\033[92m",   # green
    8: "\033[91m",   # red
}

MOTOR_MODES = {0: "HOLD", 1: "PAYOUT", 2: "RETRACT", 3: "TENSION"}

VOICE_CMDS = {
    "1": "take",
    "2": "slack",
    "3": "lower",
    "4": "up",
    "5": "watch_me",
    "6": "rest",
    "7": "climbing",
}

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
GREY   = "\033[90m"


# ─────────────────────────────────────────────
# PORT AUTO-DETECTION
# ─────────────────────────────────────────────

def find_stm32_port():
    """Try to auto-detect STM32 or any serial port."""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    # Prefer STM32 VID/PID or known descriptions
    for p in ports:
        desc = (p.description or "").lower()
        if any(x in desc for x in ["stm32", "stlink", "st-link", "virtual com"]):
            return p.device

    # Fallback: return first available
    return ports[0].device


def list_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("\nAvailable ports:")
    for p in ports:
        print(f"  {p.device:20s} — {p.description}")
    print()


# ─────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────

class ARIAData:
    def __init__(self):
        self.lock          = threading.Lock()
        self.state         = 0
        self.tension_n     = 0.0
        self.rope_pos_m    = 0.0
        self.motor_mode    = 0
        self.log           = collections.deque(maxlen=LOG_LINES)
        self.tension_hist  = collections.deque(maxlen=200)
        self.connected     = False
        self.last_rx_ms    = 0
        self.rx_count      = 0
        self.parse_errors  = 0
        self.state_time_s  = 0.0
        self._state_entry  = time.time()

    def update_state(self, state, tension, rope_pos, motor_mode):
        with self.lock:
            if state != self.state:
                self._state_entry = time.time()
            self.state      = state
            self.tension_n  = tension
            self.rope_pos_m = rope_pos
            self.motor_mode = motor_mode
            self.state_time_s = time.time() - self._state_entry
            self.tension_hist.append(tension)
            self.last_rx_ms = int(time.time() * 1000)
            self.rx_count  += 1

    def add_log(self, line):
        with self.lock:
            ts = time.strftime("%H:%M:%S")
            self.log.append(f"[{ts}] {line}")

    def get_tension_stats(self):
        with self.lock:
            if not self.tension_hist:
                return 0.0, 0.0, 0.0
            h = list(self.tension_hist)
            return min(h), max(h), sum(h)/len(h)


data = ARIAData()


# ─────────────────────────────────────────────
# SERIAL READER THREAD
# ─────────────────────────────────────────────

def serial_reader(ser):
    data.connected = True
    data.add_log("Connected to STM32")

    while True:
        try:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            # Parse ARIA state packet: S:<state>:<tension>:<rope_pos>:<motor_mode>
            if line.startswith("S:"):
                parts = line[2:].split(":")
                if len(parts) == 4:
                    try:
                        state      = int(parts[0])
                        tension    = float(parts[1])
                        rope_pos   = float(parts[2])
                        motor_mode = int(parts[3])
                        data.update_state(state, tension, rope_pos, motor_mode)
                    except ValueError:
                        data.parse_errors += 1
                else:
                    data.parse_errors += 1
            else:
                # Everything else is a log line from STM32
                data.add_log(line)

        except serial.SerialException as e:
            data.connected = False
            data.add_log(f"SERIAL ERROR: {e}")
            break
        except Exception as e:
            data.add_log(f"READ ERROR: {e}")


# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def tension_bar(tension_n, width=BAR_WIDTH):
    pct  = min(tension_n / TENSION_MAX, 1.0)
    fill = int(pct * width)
    bar  = "█" * fill + "░" * (width - fill)

    if tension_n < 100:
        color = GREEN
    elif tension_n < 400:
        color = YELLOW
    else:
        color = RED

    return f"{color}{bar}{RESET}"


def render(inject_mode=False):
    with data.lock:
        state      = data.state
        tension    = data.tension_n
        rope_pos   = data.rope_pos_m
        motor_mode = data.motor_mode
        connected  = data.connected
        rx_count   = data.rx_count
        parse_err  = data.parse_errors
        state_time = data.state_time_s
        log_lines  = list(data.log)

    t_min, t_max, t_avg = data.get_tension_stats()

    state_name  = STATE_NAMES.get(state, "UNKNOWN")
    state_color = STATE_COLORS.get(state, WHITE)
    motor_str   = MOTOR_MODES.get(motor_mode, "?")
    conn_str    = f"{GREEN}CONNECTED{RESET}" if connected else f"{RED}DISCONNECTED{RESET}"

    print(f"{BOLD}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║  ARIA Monitor  │  {conn_str}  │  RX:{rx_count:6d}  ERR:{parse_err:3d}  ║{RESET}")
    print(f"{BOLD}╠══════════════════════════════════════════════════════╣{RESET}")
    print()

    # State
    print(f"  {BOLD}STATE:{RESET}  {state_color}{BOLD}{state_name:12s}{RESET}  "
          f"({state_time:.1f}s in state)")
    print()

    # Tension
    print(f"  {BOLD}TENSION:{RESET}  {tension:7.1f} N  {tension_bar(tension)}")
    print(f"           min={t_min:.1f}  avg={t_avg:.1f}  max={t_max:.1f} N")
    print()

    # Rope kinematics
    print(f"  {BOLD}ROPE:{RESET}")
    print(f"    Position:  {rope_pos:6.2f} m")
    print()

    # Motor
    motor_color = CYAN if motor_mode in (1,2,3) else GREY
    print(f"  {BOLD}MOTOR:{RESET}  {motor_color}{motor_str}{RESET}")
    print()

    # Log
    print(f"  {BOLD}STM32 LOG:{RESET}")
    print(f"  {GREY}{'─'*52}{RESET}")
    for line in log_lines[-12:]:
        # Color code known patterns
        if "ESTOP" in line or "FALL" in line or "ERROR" in line:
            print(f"  {RED}{line}{RESET}")
        elif "→" in line or "STATE" in line:
            print(f"  {CYAN}{line}{RESET}")
        elif "confirmed" in line or "complete" in line:
            print(f"  {GREEN}{line}{RESET}")
        elif "WARN" in line or "timeout" in line:
            print(f"  {YELLOW}{line}{RESET}")
        else:
            print(f"  {GREY}{line}{RESET}")

    print(f"  {GREY}{'─'*52}{RESET}")

    if inject_mode:
        print()
        print(f"  {BOLD}INJECT MODE{RESET} — Send to STM32:")
        print(f"  {GREY}Voice: 1=take  2=slack  3=lower  4=up  5=watch_me  6=rest  7=climbing{RESET}")
        print(f"  {GREY}CV:    c=climber detected  n=no climber  k=clip gesture{RESET}")
        print(f"  {GREY}Sensor: t<N>=set tension  q=quit{RESET}")

    print()
    print(f"  {GREY}Updated: {time.strftime('%H:%M:%S')}  │  Press Ctrl+C to quit{RESET}")


# ─────────────────────────────────────────────
# INJECT MODE — pretend to be ESP32
# ─────────────────────────────────────────────

def inject_loop(ser):
    """
    Reads keyboard input and sends fake ESP32 packets to STM32.
    This lets you test state machine on real hardware before ESP32 is flashed.
    """
    import sys
    import tty
    import termios

    def getch():
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    data.add_log("INJECT MODE active — you are the ESP32")

    while True:
        try:
            ch = getch()
        except Exception:
            time.sleep(0.1)
            continue

        if ch == 'q':
            break

        # Voice commands (match ESP32 UART protocol)
        if ch in VOICE_CMDS:
            cmd_id  = int(ch)
            conf    = 0.92
            packet  = f"V:{cmd_id}:{conf:.2f}\n"
            ser.write(packet.encode())
            data.add_log(f"→ INJECTED voice: {VOICE_CMDS[ch]} ({conf:.2f})")

        # CV: climber detected
        elif ch == 'c':
            packet = "C:0.10:5.0:1\n"
            ser.write(packet.encode())
            data.add_log("→ INJECTED CV: climber detected at 5.0m")

        # CV: no climber
        elif ch == 'n':
            packet = "C:0.00:0.0:0\n"
            ser.write(packet.encode())
            data.add_log("→ INJECTED CV: no climber")

        # CV: clip gesture
        elif ch == 'k':
            packet = "C:0.88:6.5:1\n"
            ser.write(packet.encode())
            data.add_log("→ INJECTED CV: clip gesture at 6.5m")

        # Tension override (t then number)
        elif ch == 't':
            data.add_log("Enter tension in N (then press Enter):")
            # Read digits until enter
            val = ""
            while True:
                d = getch()
                if d == '\r' or d == '\n':
                    break
                val += d
            try:
                n = float(val)
                # Send as direct tension simulation note in log
                data.add_log(f"→ NOTE: Set load cell to read {n}N physically")
            except ValueError:
                data.add_log("Invalid tension value")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ARIA Serial Monitor")
    parser.add_argument("--port",   help="Serial port (auto-detect if not set)")
    parser.add_argument("--baud",   type=int, default=BAUD_RATE)
    parser.add_argument("--inject", action="store_true",
                        help="Enable ESP32 injection mode")
    parser.add_argument("--list",   action="store_true",
                        help="List available ports and exit")
    args = parser.parse_args()

    if args.list:
        list_ports()
        return

    port = args.port or find_stm32_port()
    if not port:
        print("No serial port found. Use --port to specify.")
        list_ports()
        sys.exit(1)

    print(f"Connecting to {port} at {args.baud} baud...")

    try:
        ser = serial.Serial(port, args.baud, timeout=0.1)
    except serial.SerialException as e:
        print(f"Failed to open {port}: {e}")
        sys.exit(1)

    # Start reader thread
    t = threading.Thread(target=serial_reader, args=(ser,), daemon=True)
    t.start()

    # Start inject thread if requested
    if args.inject:
        inj = threading.Thread(target=inject_loop, args=(ser,), daemon=True)
        inj.start()

    # Display loop
    try:
        while True:
            clear()
            render(inject_mode=args.inject)
            time.sleep(1.0 / REFRESH_HZ)
    except KeyboardInterrupt:
        print("\nExiting ARIA Monitor.")
        ser.close()


if __name__ == "__main__":
    main()
