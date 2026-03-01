#!/usr/bin/env python3
"""
ARIA PID Auto-Tuner
Connects to STM32 over serial, runs step-response tests,
and calculates optimal PID gains for rope tension control.

Two methods available:
  - Ziegler-Nichols: classic, good for well-behaved systems
  - Cohen-Coon: better when there's significant dead time (HX711 latency)

Usage:
  python3 aria_pid_tuner.py                     # auto-detect port
  python3 aria_pid_tuner.py --port /dev/ttyACM0
  python3 aria_pid_tuner.py --method zn         # Ziegler-Nichols
  python3 aria_pid_tuner.py --method cc         # Cohen-Coon
  python3 aria_pid_tuner.py --method relay      # Relay/Ultimate gain method

HOW TO USE:
  1. Wire motor + load cell + encoder to STM32
  2. Flash aria_stm32_complete.cpp
  3. Attach a weight to the rope (or person pulling)
  4. Run this script
  5. Script sends tension step commands and records response
  6. Script outputs Kp, Ki, Kd values
  7. Paste values into aria_stm32_complete.cpp and reflash

WHAT IT MEASURES:
  Step response from TENSION_HOLD at 40N → 80N:
  - Rise time (T_r): time from 10% to 90% of step
  - Dead time (T_d): time before response starts
  - Time constant (T_c): time to reach 63.2% of final value
  - Process gain (K): steady-state output / input ratio

SAFETY NOTE:
  This script only adjusts PID gains, not motor limits.
  Motor voltage and current limits in firmware are your
  physical safety boundary — this script cannot exceed them.
"""

import serial
import serial.tools.list_ports
import threading
import time
import sys
import math
import argparse
import collections

BAUD_RATE = 115200

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
GREY   = "\033[90m"


# ─────────────────────────────────────────────
# SERIAL DATA COLLECTOR
# ─────────────────────────────────────────────

class TensionCollector:
    """
    Connects to STM32 and continuously reads tension data.
    Records timestamped tension values for analysis.
    """
    def __init__(self, port, baud=BAUD_RATE):
        self.ser      = serial.Serial(port, baud, timeout=0.1)
        self.tension  = 0.0
        self.state    = 0
        self.history  = []           # list of (timestamp, tension_n)
        self._lock    = threading.Lock()
        self._running = True
        self._t       = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        while self._running:
            try:
                raw  = self.ser.readline()
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("S:"):
                    parts = line[2:].split(":")
                    if len(parts) == 4:
                        with self._lock:
                            self.state   = int(parts[0])
                            self.tension = float(parts[1])
                            self.history.append(
                                (time.perf_counter(), self.tension)
                            )
            except Exception:
                pass

    def get_tension(self):
        with self._lock:
            return self.tension

    def get_state(self):
        with self._lock:
            return self.state

    def clear_history(self):
        with self._lock:
            self.history.clear()

    def get_history(self):
        with self._lock:
            return list(self.history)

    def send_pid(self, kp, ki, kd):
        """Send new PID gains to STM32 via serial protocol."""
        # ARIA firmware listens for: P:<kp>:<ki>:<kd>\n
        packet = f"P:{kp:.6f}:{ki:.6f}:{kd:.6f}\n"
        self.ser.write(packet.encode())
        print(f"  → Sent PID: Kp={kp:.4f} Ki={ki:.4f} Kd={kd:.4f}")

    def send_setpoint(self, tension_n):
        """Send new tension setpoint to STM32."""
        # ARIA firmware listens for: T:<tension_n>\n
        packet = f"T:{tension_n:.1f}\n"
        self.ser.write(packet.encode())

    def close(self):
        self._running = False
        self.ser.close()


# ─────────────────────────────────────────────
# STEP RESPONSE ANALYSIS
# ─────────────────────────────────────────────

def analyze_step_response(history, t_step, initial_n, final_n):
    """
    Analyze step response data.

    Args:
        history:   list of (timestamp, tension_n)
        t_step:    timestamp when step was applied
        initial_n: tension before step (N)
        final_n:   commanded tension after step (N)

    Returns dict with:
        K:      process gain
        T_d:    dead time (s)
        T_c:    time constant (s)
        T_r:    rise time 10%-90% (s)
        T_s:    settling time ±5% (s)
        overshoot_pct: percent overshoot
        steady_state_n: measured steady state
    """
    step_size = final_n - initial_n
    if abs(step_size) < 1.0:
        return None

    # Filter to post-step data
    post = [(t, v) for t, v in history if t >= t_step]
    if len(post) < 10:
        print(f"  {RED}Not enough data after step ({len(post)} points){RESET}")
        return None

    t0       = post[0][0]
    times    = [t - t0 for t, _ in post]
    tensions = [v for _, v in post]

    # Steady state: average of last 20% of data
    n_tail = max(5, len(tensions) // 5)
    steady = sum(tensions[-n_tail:]) / n_tail

    # Process gain K = delta_output / delta_input
    K = (steady - initial_n) / step_size

    # Dead time: find when response first moves > 5% of step
    threshold_5pct = initial_n + 0.05 * step_size
    T_d = None
    for i, (t, v) in enumerate(zip(times, tensions)):
        if (step_size > 0 and v >= threshold_5pct) or \
           (step_size < 0 and v <= threshold_5pct):
            T_d = t
            break
    if T_d is None:
        T_d = 0.0

    # 63.2% point for time constant
    target_63 = initial_n + 0.632 * step_size
    T_63 = None
    for t, v in zip(times, tensions):
        if (step_size > 0 and v >= target_63) or \
           (step_size < 0 and v <= target_63):
            T_63 = t
            break
    T_c = (T_63 - T_d) if (T_63 is not None and T_d is not None) else None
    if T_c is None or T_c <= 0:
        T_c = 0.5  # fallback

    # Rise time: 10% to 90%
    t_10 = t_90 = None
    for t, v in zip(times, tensions):
        if t_10 is None and (
            (step_size > 0 and v >= initial_n + 0.1*step_size) or
            (step_size < 0 and v <= initial_n + 0.1*step_size)
        ):
            t_10 = t
        if t_90 is None and (
            (step_size > 0 and v >= initial_n + 0.9*step_size) or
            (step_size < 0 and v <= initial_n + 0.9*step_size)
        ):
            t_90 = t
    T_r = (t_90 - t_10) if (t_10 and t_90) else T_c

    # Overshoot
    if step_size > 0:
        peak    = max(tensions)
        overshoot_pct = max(0, (peak - steady) / step_size * 100)
    else:
        peak    = min(tensions)
        overshoot_pct = max(0, (steady - peak) / abs(step_size) * 100)

    # Settling time: ±5% of steady state
    band = 0.05 * abs(step_size)
    T_s  = times[-1]
    for i in range(len(times)-1, -1, -1):
        if abs(tensions[i] - steady) > band:
            T_s = times[i]
            break

    return {
        "K":              K,
        "T_d":            T_d,
        "T_c":            T_c,
        "T_r":            T_r,
        "T_s":            T_s,
        "overshoot_pct":  overshoot_pct,
        "steady_state_n": steady,
        "n_points":       len(post),
    }


def print_step_analysis(params):
    if not params:
        print(f"  {RED}Analysis failed — insufficient data{RESET}")
        return
    print(f"\n  {BOLD}Step Response Analysis:{RESET}")
    print(f"  Process gain K:       {params['K']:.3f}")
    print(f"  Dead time T_d:        {params['T_d']*1000:.1f} ms")
    print(f"  Time constant T_c:    {params['T_c']*1000:.1f} ms")
    print(f"  Rise time T_r:        {params['T_r']*1000:.1f} ms  (10%-90%)")
    print(f"  Settling time T_s:    {params['T_s']*1000:.1f} ms  (±5%)")
    print(f"  Overshoot:            {params['overshoot_pct']:.1f}%")
    print(f"  Steady state:         {params['steady_state_n']:.1f} N")
    print(f"  Data points:          {params['n_points']}")


# ─────────────────────────────────────────────
# TUNING METHODS
# ─────────────────────────────────────────────

def tune_ziegler_nichols(K, T_d, T_c):
    """
    Ziegler-Nichols step response method (Cohen-Coon variant for PI/PID).
    Good for systems where T_d/T_c < 0.5
    Returns (Kp, Ki, Kd) for PID controller.
    Note: ZN tends to be aggressive — apply 0.5-0.7x scaling for safety.
    """
    if K <= 0 or T_c <= 0:
        return None

    tau = T_d / T_c if T_c > 0 else 0.1

    # ZN-PID rules (process reaction curve method)
    # Conservative ZN: multiply Kp by 0.6 for less aggressive response
    Kp = (1.2 / K) * (T_c / T_d) if T_d > 0 else 1.0 / K
    Ti = 2.0 * T_d    # integral time constant
    Td = 0.5 * T_d    # derivative time constant

    Ki = Kp / Ti if Ti > 0 else 0
    Kd = Kp * Td

    # Apply conservative scaling for safety-critical tension control
    SAFETY_SCALE = 0.6
    return Kp * SAFETY_SCALE, Ki * SAFETY_SCALE, Kd * SAFETY_SCALE


def tune_cohen_coon(K, T_d, T_c):
    """
    Cohen-Coon method — handles systems with dead time better.
    Better choice when HX711 latency (5-10ms) is significant.
    Returns (Kp, Ki, Kd).
    """
    if K <= 0 or T_c <= 0 or T_d <= 0:
        return None

    r = T_d / T_c  # dead time ratio

    # Cohen-Coon PID formulas
    Kp = (1.35 / K) * (T_c / T_d) * (1 + 0.18 * r / (1 + r))
    Ti = T_d * (2.5 - 2.0*r) / (1.0 - 0.39*r) if (1.0 - 0.39*r) > 0 else 2.0*T_d
    Td = T_d * 0.37 / (1.0 - 0.81*r) if (1.0 - 0.81*r) > 0 else 0.3*T_d

    Ki = Kp / Ti if Ti > 0 else 0
    Kd = Kp * Td

    SAFETY_SCALE = 0.65
    return Kp * SAFETY_SCALE, Ki * SAFETY_SCALE, Kd * SAFETY_SCALE


def tune_relay(collector: TensionCollector, setpoint_n=40.0):
    """
    Relay/Åström-Hägglund method: applies bang-bang control,
    measures ultimate gain (Ku) and period (Tu), then uses
    ZN rules to get PID gains.

    More accurate than step response but takes longer.
    """
    print(f"\n  {BOLD}Relay Tuning — Measuring Ultimate Gain{RESET}")
    print(f"  Applying relay control (±10N around setpoint)...")
    print(f"  This will take ~30 seconds. Keep weight on rope.\n")

    relay_amplitude = 10.0  # N
    HIGH_SP = setpoint_n + relay_amplitude
    LOW_SP  = setpoint_n - relay_amplitude

    oscillations = []
    last_cross_time = None
    last_cross_dir  = None
    n_oscillations  = 0
    TARGET_OSC      = 5

    t_start = time.time()
    TIMEOUT = 45.0

    # Apply relay
    current_sp = HIGH_SP
    collector.send_setpoint(current_sp)

    while n_oscillations < TARGET_OSC and (time.time() - t_start) < TIMEOUT:
        tension = collector.get_tension()

        # Relay switching logic
        if current_sp == HIGH_SP and tension >= setpoint_n:
            current_sp = LOW_SP
            collector.send_setpoint(current_sp)
            t_cross = time.time()
            if last_cross_time and last_cross_dir == "up":
                oscillations.append(t_cross - last_cross_time)
                n_oscillations += 1
                print(f"  Oscillation {n_oscillations}: "
                      f"period = {oscillations[-1]*1000:.0f}ms")
            last_cross_time = t_cross
            last_cross_dir  = "down"

        elif current_sp == LOW_SP and tension <= setpoint_n:
            current_sp = HIGH_SP
            collector.send_setpoint(current_sp)
            t_cross = time.time()
            if last_cross_time and last_cross_dir == "down":
                pass  # only count full periods
            last_cross_time = t_cross
            last_cross_dir  = "up"

        time.sleep(0.05)

    # Restore normal setpoint
    collector.send_setpoint(setpoint_n)

    if len(oscillations) < 3:
        print(f"  {RED}Not enough oscillations — relay tuning failed{RESET}")
        print(f"  Try step response method instead (--method zn)")
        return None

    Tu = sum(oscillations) / len(oscillations)  # ultimate period
    Ku = 4 * relay_amplitude / (math.pi * relay_amplitude)  # ultimate gain

    print(f"\n  Ultimate period Tu: {Tu*1000:.0f} ms")
    print(f"  Ultimate gain Ku:   {Ku:.3f}")

    # ZN rules from Ku, Tu
    Kp = 0.6  * Ku
    Ki = Kp / (0.5 * Tu)
    Kd = Kp * (0.125 * Tu)

    SAFETY_SCALE = 0.6
    return Kp*SAFETY_SCALE, Ki*SAFETY_SCALE, Kd*SAFETY_SCALE


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate_gains(collector: TensionCollector, kp, ki, kd,
                   setpoint_n=40.0, duration_s=10.0):
    """
    Apply new gains and measure resulting response quality.
    Returns metrics: settling time, overshoot, steady-state error.
    """
    print(f"\n  {BOLD}Validating gains...{RESET}")
    collector.send_pid(kp, ki, kd)
    time.sleep(0.5)

    # Step: 40N → 70N
    collector.clear_history()
    t_step = time.perf_counter()
    collector.send_setpoint(70.0)
    time.sleep(duration_s)

    history = collector.get_history()
    params  = analyze_step_response(history, t_step, setpoint_n, 70.0)

    if params:
        print_step_analysis(params)

        grade = "EXCELLENT"
        if params["overshoot_pct"] > 20 or params["T_s"] > 2.0:
            grade = "POOR — consider reducing Kp"
        elif params["overshoot_pct"] > 10 or params["T_s"] > 1.0:
            grade = "ACCEPTABLE — may improve with tuning"
        elif params["overshoot_pct"] < 5 and params["T_s"] < 0.5:
            grade = "EXCELLENT"

        color = GREEN if "EXCELLENT" in grade else (
                YELLOW if "ACCEPTABLE" in grade else RED)
        print(f"\n  {color}{BOLD}Assessment: {grade}{RESET}")

    # Restore baseline
    collector.send_setpoint(setpoint_n)
    return params


# ─────────────────────────────────────────────
# MAIN TUNING FLOW
# ─────────────────────────────────────────────

def run_step_tuning(collector: TensionCollector, method="cc",
                    initial_n=40.0, final_n=80.0, record_s=15.0):
    print(f"\n{BOLD}═══════════════════════════════════════════{RESET}")
    print(f"{BOLD}  ARIA PID Tuner — Method: {method.upper()}{RESET}")
    print(f"{BOLD}═══════════════════════════════════════════{RESET}\n")

    print(f"  Setpoint step: {initial_n}N → {final_n}N")
    print(f"  Recording for: {record_s}s")
    print()
    print(f"  {YELLOW}PREREQUISITES:{RESET}")
    print(f"  1. Motor is powered and spooled correctly")
    print(f"  2. Load cell is calibrated (run CALIBRATION_MODE first)")
    print(f"  3. Rope has a consistent weight attached (~{initial_n/10:.0f}kg)")
    print(f"  4. STM32 is in TENSION_HOLD state")
    print()

    input(f"  Press ENTER when ready to start step test...")

    # Pre-step: record baseline for 3 seconds
    print(f"\n  Recording baseline at {initial_n}N...")
    collector.send_setpoint(initial_n)
    collector.clear_history()
    time.sleep(3.0)

    baseline_tensions = [v for _, v in collector.get_history()]
    baseline_n = sum(baseline_tensions[-20:]) / max(len(baseline_tensions[-20:]), 1)
    print(f"  Baseline tension: {baseline_n:.1f}N")

    # Apply step
    print(f"\n  Applying step to {final_n}N...")
    collector.clear_history()
    t_step = time.perf_counter()
    collector.send_setpoint(final_n)

    # Progress bar while recording
    for i in range(int(record_s * 10)):
        pct = int((i / (record_s * 10)) * 30)
        bar = "█" * pct + "░" * (30 - pct)
        t   = collector.get_tension()
        print(f"\r  Recording: [{bar}] {t:.1f}N", end="", flush=True)
        time.sleep(0.1)
    print()

    # Restore baseline
    collector.send_setpoint(initial_n)
    print(f"  Restored to {initial_n}N")

    # Analyze
    history = collector.get_history()
    print(f"\n  Collected {len(history)} data points")
    params  = analyze_step_response(history, t_step, baseline_n, final_n)
    print_step_analysis(params)

    if not params:
        print(f"\n  {RED}Tuning failed — check connections and retry{RESET}")
        return None, None, None

    # Calculate gains
    K   = params["K"]
    T_d = params["T_d"]
    T_c = params["T_c"]

    if method == "zn":
        gains = tune_ziegler_nichols(K, T_d, T_c)
    elif method == "cc":
        gains = tune_cohen_coon(K, T_d, T_c)
    else:
        gains = tune_ziegler_nichols(K, T_d, T_c)

    if not gains:
        print(f"  {RED}Could not calculate gains from measurements{RESET}")
        return None, None, None

    Kp, Ki, Kd = gains

    print(f"\n{BOLD}{'═'*45}{RESET}")
    print(f"{BOLD}  CALCULATED PID GAINS ({method.upper()} method):{RESET}")
    print(f"{BOLD}{'═'*45}{RESET}")
    print(f"  Kp = {Kp:.6f}")
    print(f"  Ki = {Ki:.6f}")
    print(f"  Kd = {Kd:.6f}")
    print(f"{BOLD}{'═'*45}{RESET}")
    print()
    print(f"  Paste into aria_stm32_complete.cpp:")
    print(f"  {CYAN}PID tensionPID {{")
    print(f"    .kp = {Kp:.6f}f,")
    print(f"    .ki = {Ki:.6f}f,")
    print(f"    .kd = {Kd:.6f}f,")
    print(f"  }};{RESET}")

    # Validate
    validate_choice = input(f"\n  Apply and validate these gains now? (y/n): ").strip().lower()
    if validate_choice == 'y':
        validate_gains(collector, Kp, Ki, Kd, setpoint_n=initial_n)

    # Save
    save_choice = input(f"\n  Save gains to file? (y/n): ").strip().lower()
    if save_choice == 'y':
        filename = f"aria_pid_gains_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w") as f:
            f.write(f"ARIA PID Tuning Results\n")
            f.write(f"Method: {method.upper()}\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Step response parameters:\n")
            for k, v in params.items():
                f.write(f"  {k}: {v}\n")
            f.write(f"\nCalculated gains:\n")
            f.write(f"  Kp = {Kp:.6f}\n")
            f.write(f"  Ki = {Ki:.6f}\n")
            f.write(f"  Kd = {Kd:.6f}\n")
            f.write(f"\nCode snippet:\n")
            f.write(f"PID tensionPID {{\n")
            f.write(f"  .kp = {Kp:.6f}f,\n")
            f.write(f"  .ki = {Ki:.6f}f,\n")
            f.write(f"  .kd = {Kd:.6f}f,\n")
            f.write(f"}};\n")
        print(f"  {GREEN}Saved: {filename}{RESET}")

    return Kp, Ki, Kd


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
    parser = argparse.ArgumentParser(description="ARIA PID Auto-Tuner")
    parser.add_argument("--port",   help="Serial port")
    parser.add_argument("--method", default="cc",
                        choices=["zn", "cc", "relay"],
                        help="Tuning method: zn=Ziegler-Nichols, "
                             "cc=Cohen-Coon, relay=Relay method")
    parser.add_argument("--initial", type=float, default=40.0,
                        help="Initial tension setpoint (N)")
    parser.add_argument("--final",   type=float, default=80.0,
                        help="Step target tension (N)")
    parser.add_argument("--duration", type=float, default=15.0,
                        help="Recording duration after step (s)")
    args = parser.parse_args()

    port = args.port or find_port()
    if not port:
        print("No serial port found. Use --port.")
        sys.exit(1)

    print(f"\nConnecting to STM32 on {port}...")
    try:
        collector = TensionCollector(port)
    except serial.SerialException as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print(f"Connected. Current tension: {collector.get_tension():.1f}N")
    print()
    print(f"NOTE: For this script to work, add these serial command handlers")
    print(f"to aria_stm32_complete.cpp in the uart_read() function:")
    print()
    print(f"  {CYAN}// In uart_parse() function, add:")
    print(f"  else if (p[0] == 'P') {{  // PID gains")
    print(f"    float kp, ki, kd;")
    print(f"    if (sscanf(p+2, \"%f:%f:%f\", &kp, &ki, &kd) == 3) {{")
    print(f"      tensionPID.kp = kp;")
    print(f"      tensionPID.ki = ki;")
    print(f"      tensionPID.kd = kd;")
    print(f"      tensionPID.reset();")
    print(f"    }}")
    print(f"  }}")
    print(f"  else if (p[0] == 'T') {{  // Setpoint")
    print(f"    float sp;")
    print(f"    if (sscanf(p+2, \"%f\", &sp) == 1) {{")
    print(f"      g_tension_setpoint = sp;  // add this global")
    print(f"    }}")
    print(f"  }}{RESET}")
    print()

    try:
        if args.method == "relay":
            print(f"Using relay method...")
            gains = tune_relay(collector, setpoint_n=args.initial)
            if gains:
                Kp, Ki, Kd = gains
                print(f"\n  Kp={Kp:.6f}  Ki={Ki:.6f}  Kd={Kd:.6f}")
        else:
            run_step_tuning(
                collector,
                method=args.method,
                initial_n=args.initial,
                final_n=args.final,
                record_s=args.duration
            )
    except KeyboardInterrupt:
        print("\nTuning cancelled.")
    finally:
        collector.close()


if __name__ == "__main__":
    main()
