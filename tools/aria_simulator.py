"""
ARIA - Autonomous Rope Intelligence Architecture
Full Python State Machine Simulator
Jonathan Kofman — Lead Auto Belay Project

Run: python aria_simulator.py
Interactive CLI lets you inject sensor events and voice commands
to test all state transitions before hardware arrives.
"""

import time
import random
import threading
import sys
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import deque


# ─────────────────────────────────────────────
# CONSTANTS — tune these before flashing hardware
# ─────────────────────────────────────────────

TENSION_BASELINE_N        = 40.0   # Normal climbing tension (N)
TENSION_TAKE_THRESHOLD_N  = 200.0  # Load cell threshold to confirm TAKE (N)
TENSION_FALL_THRESHOLD_N  = 400.0  # Threshold indicating active fall (N)
TENSION_GROUND_N          = 15.0   # Below this = climber on ground
TENSION_WATCH_ME_N        = 60.0   # Tighter slack in WATCH ME mode (N) — must match TENSION_TIGHT_N in state_machine.py

ROPE_SPEED_CLIMB_MS       = 0.3    # Normal climbing rope speed (m/s)
ROPE_SPEED_LOWER_MS       = 0.5    # Controlled lower speed (m/s)
ROPE_SPEED_RETRACT_MS     = 0.8    # TAKE retraction speed (m/s)
ROPE_SPEED_FALL_MS        = 2.0    # Speed threshold indicating fall (m/s)

CLIP_SLACK_M              = 0.65   # Rope paid out for clipping (m)
CLIP_DETECT_CONFIDENCE    = 0.75   # CV confidence to trigger CLIPPING state

VOICE_CONFIDENCE_MIN      = 0.85   # Minimum wake word confidence to act
TAKE_CONFIRM_WINDOW_MS    = 500    # ms window to confirm TAKE with load cell
WATCH_ME_TIMEOUT_S        = 180    # Auto-exit WATCH ME after 3 min
REST_TIMEOUT_S            = 600    # Auto-exit REST after 10 min

PID_KP                    = 2.5    # Tension PID proportional gain
PID_KI                    = 0.8    # Tension PID integral gain
PID_KD                    = 0.1    # Tension PID derivative gain


# ─────────────────────────────────────────────
# STATE DEFINITIONS
# ─────────────────────────────────────────────

class State(Enum):
    IDLE         = auto()   # No climber, device standby
    CLIMBING     = auto()   # Active climbing, tension mode
    CLIPPING     = auto()   # Feeding slack for clip
    TAKE         = auto()   # Rope locked, climber hanging
    REST         = auto()   # Climber resting, holding position
    LOWER        = auto()   # Controlled descent to ground
    WATCH_ME     = auto()   # High attention, tight slack
    UP           = auto()   # Motor assist upward
    FALL_ARREST  = auto()   # Post-fall hold — brake engaged, requires explicit ack
    ESTOP        = auto()   # Emergency stop — all outputs disabled, requires reset


class VoiceCommand(Enum):
    TAKE        = "take"
    SLACK       = "slack"
    LOWER       = "lower"
    UP          = "up"
    WATCH_ME    = "watch me"
    REST        = "rest"
    CLIMBING    = "climbing"   # exit from REST/TAKE back to climbing
    RESET       = "reset"      # exit from FALL_ARREST / ESTOP
    NONE        = "none"


# ─────────────────────────────────────────────
# SENSOR DATA (simulated hardware readings)
# ─────────────────────────────────────────────

@dataclass
class SensorData:
    load_cell_n: float        = 0.0    # Rope tension in Newtons
    rope_speed_ms: float      = 0.0    # + = paying out, - = retracting
    rope_position_m: float    = 0.0    # Total rope deployed (m)
    cv_climber_height_m: float= 0.0    # Camera: climber height on wall
    cv_clip_confidence: float = 0.0    # Camera: confidence climber is clipping
    cv_climber_detected: bool = False  # Camera: climber on wall
    voice_command: VoiceCommand = VoiceCommand.NONE
    voice_confidence: float   = 0.0
    timestamp_ms: float       = 0.0
    _estop: bool              = False  # E-stop button pressed


# ─────────────────────────────────────────────
# PID CONTROLLER
# ─────────────────────────────────────────────

class PIDController:
    """PID controller with clamping anti-windup.

    Anti-windup rationale: the integral term is clamped so that
    |Ki * integral| can never exceed the actuator output range on its
    own.  This prevents unbounded accumulation during output saturation
    (e.g. motor at 100 % while error persists).

    Simulator gains  (Kp=2.5, Ki=0.8, Kd=0.1, output +/-100):
        integral_max = output_max / Ki = 100 / 0.8 = 125.0

    Firmware gains   (Kp=0.022, Ki=0.413, Kd=0.0005, output 0-10 V):
        integral_max = 10 / 0.413 ~= 24.21
        integral_min =  0 / 0.413 =   0.0
        (firmware PID must implement the same clamping scheme)
    """

    def __init__(self, kp, ki, kd, output_min=-100, output_max=100):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = time.time()

        # Anti-windup: compute integral clamp from actuator limits.
        # |Ki * integral| must stay within [output_min, output_max].
        if self.ki != 0.0:
            self._integral_min = self.output_min / self.ki
            self._integral_max = self.output_max / self.ki
            # Ensure min <= max regardless of Ki sign
            if self._integral_min > self._integral_max:
                self._integral_min, self._integral_max = (
                    self._integral_max, self._integral_min)
        else:
            self._integral_min = 0.0
            self._integral_max = 0.0

    def compute(self, setpoint, measurement):
        now = time.time()
        dt = now - self._prev_time
        if dt <= 0:
            dt = 0.001
        error = setpoint - measurement
        self._integral += error * dt

        # ── Anti-windup: clamp integral term ──
        self._integral = max(self._integral_min,
                             min(self._integral_max, self._integral))

        derivative = (error - self._prev_error) / dt
        output = (self.kp * error +
                  self.ki * self._integral +
                  self.kd * derivative)
        output = max(self.output_min, min(self.output_max, output))
        self._prev_error = error
        self._prev_time = now
        return output

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


# ─────────────────────────────────────────────
# EVENT LOG
# ─────────────────────────────────────────────

class EventLog:
    def __init__(self, maxlen=200):
        self._log = deque(maxlen=maxlen)

    def add(self, msg, level="INFO"):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] [{level}] {msg}"
        self._log.append(entry)
        color = {
            "INFO":  "\033[0m",
            "STATE": "\033[96m",
            "WARN":  "\033[93m",
            "SAFE":  "\033[91m",
            "CMD":   "\033[92m",
        }.get(level, "\033[0m")
        print(f"{color}{entry}\033[0m")

    def tail(self, n=10):
        return list(self._log)[-n:]


# ─────────────────────────────────────────────
# ARIA STATE MACHINE
# ─────────────────────────────────────────────

class ARIAStateMachine:

    def __init__(self):
        self.state = State.IDLE
        self.sensors = SensorData()
        self.pid = PIDController(PID_KP, PID_KI, PID_KD,
                                  output_min=0, output_max=100)
        self.log = EventLog()
        self._state_entry_time = time.time()
        self._take_voice_time = None
        self._clip_start_time = None
        self._motor_output = 0.0    # 0-100% motor effort
        self._motor_direction = 1   # 1=payout, -1=retract, 0=hold
        self._running = True
        self._lock = threading.Lock()

        self.log.add("ARIA system initialized", "INFO")
        self.log.add(f"State: {self.state.name}", "STATE")

    # ── Public sensor injection (called from CLI or real hardware) ──

    def inject_sensor(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.sensors, k):
                    setattr(self.sensors, k, v)
            self.sensors.timestamp_ms = time.time() * 1000

    def inject_voice(self, cmd_str: str, confidence: float = 0.92):
        with self._lock:
            for cmd in VoiceCommand:
                if cmd.value == cmd_str.lower():
                    self.sensors.voice_command = cmd
                    self.sensors.voice_confidence = confidence
                    self.log.add(
                        f"Voice: '{cmd_str}' confidence={confidence:.2f}",
                        "CMD"
                    )
                    return
            self.log.add(f"Unknown voice command: '{cmd_str}'", "WARN")

    def inject_estop(self, active: bool = True):
        """Trigger or release the emergency stop button."""
        with self._lock:
            self.sensors._estop = active
            if active:
                self.log.add("E-STOP button pressed", "SAFE")
            else:
                self.log.add("E-STOP button released", "INFO")

    # ── State machine tick (runs continuously) ──

    def tick(self):
        with self._lock:
            s = self.sensors
            prev_state = self.state

            # ── ESTOP — highest priority, overrides everything ──
            if s._estop and self.state != State.ESTOP:
                self._motor_output = 0.0
                self._motor_direction = 0
                self.state = State.ESTOP
                self.log.add("ESTOP TRIGGERED — all outputs disabled", "SAFE")

            # ── FALL DETECTION — overrides all active states ──
            elif (self.state not in (State.IDLE, State.ESTOP, State.FALL_ARREST)
                  and self._is_fall_in_progress(s)):
                self._motor_output = 0.0
                self._motor_direction = 0
                self.log.add(
                    f"FALL DETECTED — load={s.load_cell_n:.0f}N "
                    f"speed={s.rope_speed_ms:.2f}m/s — brake engaged, "
                    f"entering FALL_ARREST",
                    "SAFE"
                )
                self.state = State.FALL_ARREST

            else:
                # ── Normal STATE LOGIC (includes FALL_ARREST and ESTOP handlers) ──
                self._dispatch_state(s)

            # ── Clear one-shot voice command after processing ──
            self.sensors.voice_command = VoiceCommand.NONE
            self.sensors.voice_confidence = 0.0

            if self.state != prev_state:
                self._state_entry_time = time.time()
                self.log.add(
                    f"Transition: {prev_state.name} → {self.state.name}",
                    "STATE"
                )

    # ── Safety check ──

    def _is_fall_in_progress(self, s):
        return (s.rope_speed_ms > ROPE_SPEED_FALL_MS and
                s.load_cell_n > TENSION_FALL_THRESHOLD_N)

    def _time_in_state(self):
        return time.time() - self._state_entry_time

    def _valid_voice(self, s, cmd):
        return (s.voice_command == cmd and
                s.voice_confidence >= VOICE_CONFIDENCE_MIN)

    def _dispatch_state(self, s):
        """Route to the correct state handler."""
        if self.state == State.IDLE:
            self._state_idle(s)
        elif self.state == State.CLIMBING:
            self._state_climbing(s)
        elif self.state == State.CLIPPING:
            self._state_clipping(s)
        elif self.state == State.TAKE:
            self._state_take(s)
        elif self.state == State.REST:
            self._state_rest(s)
        elif self.state == State.LOWER:
            self._state_lower(s)
        elif self.state == State.WATCH_ME:
            self._state_watch_me(s)
        elif self.state == State.UP:
            self._state_up(s)
        elif self.state == State.FALL_ARREST:
            self._state_fall_arrest(s)
        elif self.state == State.ESTOP:
            self._state_estop(s)

    # ── IDLE ──
    def _state_idle(self, s):
        self._motor_output = 0.0
        self._motor_direction = 0
        self.pid.reset()
        if s.cv_climber_detected and s.load_cell_n > TENSION_GROUND_N:
            self.state = State.CLIMBING

    # ── CLIMBING ──
    def _state_climbing(self, s):
        # PID: maintain baseline tension
        target = TENSION_BASELINE_N
        pid_out = self.pid.compute(target, s.load_cell_n)
        self._motor_output = abs(pid_out)
        self._motor_direction = 1  # pay out

        # Exit conditions
        if s.load_cell_n < TENSION_GROUND_N and not s.cv_climber_detected:
            self.state = State.IDLE
            return

        # CV detects clipping gesture
        if s.cv_clip_confidence >= CLIP_DETECT_CONFIDENCE:
            self._clip_start_time = time.time()
            self.state = State.CLIPPING
            return

        # Voice: TAKE
        if self._valid_voice(s, VoiceCommand.TAKE):
            self._take_voice_time = time.time()
            # Wait for load cell confirmation (handled in next tick)
            self.state = State.TAKE
            return

        # Voice: REST
        if self._valid_voice(s, VoiceCommand.REST):
            self.state = State.REST
            return

        # Voice: LOWER
        if self._valid_voice(s, VoiceCommand.LOWER):
            self.state = State.LOWER
            return

        # Voice: WATCH ME
        if self._valid_voice(s, VoiceCommand.WATCH_ME):
            self.state = State.WATCH_ME
            return

        # Voice: UP
        if self._valid_voice(s, VoiceCommand.UP):
            self.state = State.UP
            return

    # ── CLIPPING ──
    def _state_clipping(self, s):
        # Voice overrides during clipping — climber can command TAKE or LOWER
        if self._valid_voice(s, VoiceCommand.TAKE):
            self._take_voice_time = time.time()
            self.log.add("TAKE requested during CLIPPING", "CMD")
            self.state = State.TAKE
            return
        if self._valid_voice(s, VoiceCommand.LOWER):
            self.log.add("LOWER requested during CLIPPING", "CMD")
            self.state = State.LOWER
            return

        # Pre-feed CLIP_SLACK_M of rope quickly
        elapsed = time.time() - self._clip_start_time
        clip_duration = CLIP_SLACK_M / ROPE_SPEED_CLIMB_MS

        if elapsed < clip_duration:
            self._motor_output = 80.0
            self._motor_direction = 1  # pay out fast
            self.log.add(
                f"Clipping: feeding {CLIP_SLACK_M}m slack "
                f"({elapsed:.2f}s / {clip_duration:.2f}s)",
                "INFO"
            )
        else:
            # Clip done — return to CLIMBING
            self.log.add("Clip complete — returning to CLIMBING", "INFO")
            self.state = State.CLIMBING

        # Safety: if fall detected during clipping, state machine
        # transitions to FALL_ARREST (safety override in tick)

    # ── TAKE ──
    def _state_take(self, s):
        # Two-factor confirmation: voice + load cell
        if self._take_voice_time is not None:
            elapsed_ms = (time.time() - self._take_voice_time) * 1000
            if elapsed_ms <= TAKE_CONFIRM_WINDOW_MS:
                if s.load_cell_n >= TENSION_TAKE_THRESHOLD_N:
                    # Confirmed — lock rope
                    self._motor_output = 100.0
                    self._motor_direction = -1  # retract to remove slack
                    self.log.add(
                        f"TAKE confirmed — load={s.load_cell_n:.0f}N "
                        f"({elapsed_ms:.0f}ms) — rope locked",
                        "CMD"
                    )
                    self._take_voice_time = None
                    return
            else:
                # Timeout — no load cell confirmation, cancel
                self.log.add(
                    "TAKE timed out — no weight on rope, cancelling",
                    "WARN"
                )
                self._take_voice_time = None
                self.state = State.CLIMBING
                return

        # Holding: motor holds spool locked
        self._motor_output = 100.0
        self._motor_direction = 0  # hold

        # Exit: voice says CLIMBING or encoder detects upward movement
        if self._valid_voice(s, VoiceCommand.CLIMBING):
            self.state = State.CLIMBING
            return
        if s.rope_speed_ms > 0.1 and s.load_cell_n < TENSION_TAKE_THRESHOLD_N:
            # Climber started moving up again
            self.state = State.CLIMBING
            return
        # Timeout: 10 min auto-release
        if self._time_in_state() > REST_TIMEOUT_S:
            self.log.add("TAKE timeout — auto-releasing to CLIMBING", "WARN")
            self.state = State.CLIMBING

    # ── REST ──
    def _state_rest(self, s):
        # Same as TAKE mechanically but different intent
        self._motor_output = 100.0
        self._motor_direction = 0  # hold

        self.log.add(
            f"REST — holding position, load={s.load_cell_n:.0f}N "
            f"({self._time_in_state():.0f}s)",
            "INFO"
        )

        if self._valid_voice(s, VoiceCommand.CLIMBING):
            self.state = State.CLIMBING
            return
        if s.rope_speed_ms > 0.1:
            self.state = State.CLIMBING
            return
        if self._time_in_state() > REST_TIMEOUT_S:
            self.log.add("REST timeout — returning to CLIMBING", "WARN")
            self.state = State.CLIMBING

    # ── LOWER ──
    def _state_lower(self, s):
        # Safety gate: cannot execute if fall in progress
        if s.load_cell_n > TENSION_FALL_THRESHOLD_N:
            self.log.add("LOWER blocked — fall force detected", "SAFE")
            self.state = State.CLIMBING
            return

        self._motor_output = 60.0
        self._motor_direction = 1  # pay out at controlled speed
        self.log.add(
            f"LOWER — descending at {ROPE_SPEED_LOWER_MS}m/s, "
            f"load={s.load_cell_n:.0f}N",
            "INFO"
        )

        # Exit: climber reaches ground
        if s.load_cell_n < TENSION_GROUND_N:
            self.log.add("LOWER complete — climber at ground", "INFO")
            self.state = State.IDLE

    # ── WATCH ME ──
    def _state_watch_me(self, s):
        # Tighter slack tolerance
        target = TENSION_WATCH_ME_N
        pid_out = self.pid.compute(target, s.load_cell_n)
        self._motor_output = abs(pid_out)
        self._motor_direction = 1

        self.log.add(
            f"WATCH ME — tight mode, tension={s.load_cell_n:.0f}N "
            f"target={target}N ({self._time_in_state():.0f}s)",
            "INFO"
        )

        # All the same exits as CLIMBING
        if self._valid_voice(s, VoiceCommand.TAKE):
            self._take_voice_time = time.time()
            self.state = State.TAKE
            return
        if self._valid_voice(s, VoiceCommand.LOWER):
            self.state = State.LOWER
            return
        if self._valid_voice(s, VoiceCommand.CLIMBING):
            self.state = State.CLIMBING
            return
        if self._time_in_state() > WATCH_ME_TIMEOUT_S:
            self.log.add("WATCH ME timeout — returning to CLIMBING", "WARN")
            self.state = State.CLIMBING

    # ── UP ──
    def _state_up(self, s):
        # Reduce rope tension to near zero — assist upward
        # Safety: never pull climber — if tension goes negative, cut motor
        target = 5.0  # Near zero tension
        pid_out = self.pid.compute(target, s.load_cell_n)
        self._motor_output = abs(pid_out)
        self._motor_direction = 1

        if s.load_cell_n < 0:
            self.log.add("UP safety cut — motor pulling climber, stopping",
                         "SAFE")
            self._motor_output = 0.0
            self._motor_direction = 0

        if self._valid_voice(s, VoiceCommand.CLIMBING):
            self.state = State.CLIMBING
            return
        if self._valid_voice(s, VoiceCommand.TAKE):
            self._take_voice_time = time.time()
            self.state = State.TAKE

    # ── FALL_ARREST ──
    def _state_fall_arrest(self, s):
        # Brake engaged, motor off, hold position.
        # Requires explicit acknowledgment to exit.
        self._motor_output = 0.0
        self._motor_direction = 0

        if self._valid_voice(s, VoiceCommand.RESET):
            self.log.add("FALL_ARREST acknowledged via RESET — returning to IDLE", "SAFE")
            self.state = State.IDLE
            self.pid.reset()
            return
        if self._valid_voice(s, VoiceCommand.LOWER):
            self.log.add("FALL_ARREST acknowledged via LOWER — controlled descent", "SAFE")
            self.state = State.LOWER
            return

    # ── ESTOP ──
    def _state_estop(self, s):
        # All outputs disabled. Requires explicit reset to exit.
        self._motor_output = 0.0
        self._motor_direction = 0

        if self._valid_voice(s, VoiceCommand.RESET):
            self.log.add("ESTOP reset — returning to IDLE", "SAFE")
            self.state = State.IDLE
            self.pid.reset()
            return

    # ── Status report ──
    def status(self):
        s = self.sensors
        direction_str = {1: "PAYOUT", -1: "RETRACT", 0: "HOLD"}.get(
            self._motor_direction, "?"
        )
        return (
            f"\n{'='*55}\n"
            f"  STATE:        {self.state.name}\n"
            f"  Motor:        {self._motor_output:.1f}% [{direction_str}]\n"
            f"  Tension:      {s.load_cell_n:.1f} N\n"
            f"  Rope speed:   {s.rope_speed_ms:.2f} m/s\n"
            f"  Rope out:     {s.rope_position_m:.2f} m\n"
            f"  Climber H:    {s.cv_climber_height_m:.1f} m\n"
            f"  Clip conf:    {s.cv_clip_confidence:.2f}\n"
            f"  Climber det:  {s.cv_climber_detected}\n"
            f"  Time in state:{self._time_in_state():.1f}s\n"
            f"{'='*55}"
        )


# ─────────────────────────────────────────────
# AUTO-TICK LOOP (background thread)
# ─────────────────────────────────────────────

def run_tick_loop(aria: ARIAStateMachine, hz=20):
    """Runs the state machine at `hz` Hz in background."""
    interval = 1.0 / hz
    while aria._running:
        aria.tick()
        time.sleep(interval)


# ─────────────────────────────────────────────
# SCENARIO SCRIPTS (automated test sequences)
# ─────────────────────────────────────────────

def scenario_normal_climb(aria: ARIAStateMachine):
    """Simulates a full climb: attach → climb → clip × 3 → take → lower."""
    print("\n>> Running scenario: Normal Climb\n")
    steps = [
        (1.0,  dict(cv_climber_detected=True, load_cell_n=50.0,
                    cv_climber_height_m=0.5, rope_speed_ms=0.3),
               None, "Climber attaches, starts climbing"),
        (2.0,  dict(load_cell_n=45.0, cv_climber_height_m=2.0,
                    rope_position_m=2.0),
               None, "Climbing to first bolt"),
        (1.0,  dict(cv_clip_confidence=0.9, rope_speed_ms=0.1),
               None, "CV detects clip gesture at bolt 1"),
        (2.0,  dict(cv_clip_confidence=0.0, rope_speed_ms=0.3,
                    cv_climber_height_m=4.0, rope_position_m=4.0),
               None, "Clipped — continuing up"),
        (1.0,  dict(cv_clip_confidence=0.88, rope_speed_ms=0.1,
                    cv_climber_height_m=5.0),
               None, "CV detects clip gesture at bolt 2"),
        (2.0,  dict(cv_clip_confidence=0.0, rope_speed_ms=0.3,
                    cv_climber_height_m=8.0, rope_position_m=8.0),
               None, "Clipped — continuing up"),
        (0.5,  dict(rope_speed_ms=0.1), "take",
               "Climber yells TAKE — pumped at top"),
        (0.5,  dict(load_cell_n=680.0), None,
               "Load cell confirms climber weighting rope"),
        (3.0,  dict(load_cell_n=650.0, rope_speed_ms=0.0),
               None, "Hanging, resting"),
        (0.5,  dict(load_cell_n=300.0), "lower",
               "Climber yells LOWER"),
        (3.0,  dict(load_cell_n=200.0, rope_speed_ms=0.5,
                    cv_climber_height_m=3.0),
               None, "Descending..."),
        (2.0,  dict(load_cell_n=5.0, cv_climber_height_m=0.0,
                    cv_climber_detected=False),
               None, "Climber reaches ground"),
    ]
    for delay, sensors, voice, description in steps:
        print(f"\n  -> {description}")
        aria.inject_sensor(**sensors)
        if voice:
            aria.inject_voice(voice)
        time.sleep(delay)
    print(aria.status())


def scenario_fall(aria: ARIAStateMachine):
    """Simulates a lead fall above last bolt."""
    print("\n>> Running scenario: Lead Fall\n")
    steps = [
        (1.0, dict(cv_climber_detected=True, load_cell_n=45.0,
                   cv_climber_height_m=6.0, rope_position_m=6.0,
                   rope_speed_ms=0.3), None, "Climbing at 6m"),
        (0.1, dict(load_cell_n=900.0, rope_speed_ms=3.5),
              None, "FALL — high load and speed detected"),
        (0.5, dict(load_cell_n=450.0, rope_speed_ms=1.8),
              None, "Clutch engaging — decelerating"),
        (1.0, dict(load_cell_n=680.0, rope_speed_ms=0.0),
              None, "Caught — hanging on rope"),
        (2.0, dict(load_cell_n=650.0), None, "Hanging stable"),
        (0.5, dict(load_cell_n=300.0), "lower", "Yells LOWER"),
        (3.0, dict(load_cell_n=5.0, cv_climber_detected=False),
              None, "Back on ground"),
    ]
    for delay, sensors, voice, description in steps:
        print(f"\n  -> {description}")
        aria.inject_sensor(**sensors)
        if voice:
            aria.inject_voice(voice)
        time.sleep(delay)
    print(aria.status())


def scenario_watch_me(aria: ARIAStateMachine):
    """Simulates WATCH ME mode on a hard move."""
    print("\n>> Running scenario: Watch Me Mode\n")
    steps = [
        (1.0, dict(cv_climber_detected=True, load_cell_n=45.0,
                   cv_climber_height_m=5.0, rope_speed_ms=0.2),
              None, "Climbing — approaching crux"),
        (0.5, dict(load_cell_n=45.0), "watch me",
              "Yells WATCH ME — about to attempt crux"),
        (3.0, dict(load_cell_n=30.0, rope_speed_ms=0.1,
                   cv_climber_height_m=6.0),
              None, "On crux — tight slack management active"),
        (0.5, dict(load_cell_n=40.0), "take",
              "Didn't make it — yells TAKE"),
        (0.3, dict(load_cell_n=700.0), None, "Weighted rope"),
        (2.0, dict(load_cell_n=660.0, rope_speed_ms=0.0),
              None, "Hanging, recovering"),
        (0.5, dict(load_cell_n=200.0), "climbing",
              "Ready to try again — yells CLIMBING"),
        (1.0, dict(load_cell_n=45.0, rope_speed_ms=0.2),
              None, "Back to climbing"),
    ]
    for delay, sensors, voice, description in steps:
        print(f"\n  -> {description}")
        aria.inject_sensor(**sensors)
        if voice:
            aria.inject_voice(voice)
        time.sleep(delay)
    print(aria.status())


def scenario_rest(aria: ARIAStateMachine):
    """Simulates REST: climb -> rest -> hold -> climbing to resume."""
    print("\n>> Running scenario: Rest (hold then resume)\n")
    steps = [
        (1.0, dict(cv_climber_detected=True, load_cell_n=50.0,
                   cv_climber_height_m=1.0, rope_speed_ms=0.3),
              None, "Climber attaches, starts climbing"),
        (2.0, dict(load_cell_n=45.0, cv_climber_height_m=4.0,
                   rope_position_m=4.0, rope_speed_ms=0.2),
              None, "Climbing to mid-wall"),
        (0.5, dict(load_cell_n=45.0), "rest",
              "Yells REST - need to shake out"),
        (3.0, dict(load_cell_n=45.0, rope_speed_ms=0.0,
                   cv_climber_height_m=4.0),
              None, "Holding position in REST"),
        (0.5, dict(load_cell_n=45.0), "climbing",
              "Ready - yells CLIMBING"),
        (1.0, dict(load_cell_n=45.0, rope_speed_ms=0.2),
              None, "Back to climbing"),
    ]
    for delay, sensors, voice, description in steps:
        print(f"\n  -> {description}")
        aria.inject_sensor(**sensors)
        if voice:
            aria.inject_voice(voice)
        time.sleep(delay)
    print(aria.status())


def scenario_up(aria: ARIAStateMachine):
    """Simulates UP (slack): climb -> up -> slack -> climbing to resume."""
    print("\n>> Running scenario: Up (slack then resume)\n")
    steps = [
        (1.0, dict(cv_climber_detected=True, load_cell_n=50.0,
                   cv_climber_height_m=2.0, rope_speed_ms=0.3),
              None, "Climber climbing"),
        (1.0, dict(load_cell_n=45.0, cv_climber_height_m=5.0,
                   rope_position_m=5.0),
              None, "At bolt, needs slack to clip"),
        (0.5, dict(load_cell_n=45.0), "up",
              "Yells UP for slack"),
        (2.0, dict(load_cell_n=20.0, rope_speed_ms=0.4,
                   cv_climber_height_m=5.5, rope_position_m=5.5),
              None, "Motor paying slack"),
        (0.5, dict(load_cell_n=40.0), "climbing",
              "Clipped - yells CLIMBING"),
        (1.0, dict(load_cell_n=45.0, rope_speed_ms=0.2),
              None, "Back to tension control"),
    ]
    for delay, sensors, voice, description in steps:
        print(f"\n  -> {description}")
        aria.inject_sensor(**sensors)
        if voice:
            aria.inject_voice(voice)
        time.sleep(delay)
    print(aria.status())


# ─────────────────────────────────────────────
# INTERACTIVE CLI
# ─────────────────────────────────────────────

HELP_TEXT = """
ARIA Simulator - Commands:
-----------------------------------------------
  status              Print current system status
  voice <cmd>         Inject voice command
                      Commands: take, slack, lower, up, watch me, rest, climbing
  sensor <key>=<val>  Inject sensor value
                      Keys: load_cell_n, rope_speed_ms, rope_position_m,
                            cv_climber_height_m, cv_clip_confidence,
                            cv_climber_detected
  scenario <name>     Run automated test scenario
                      Scenarios: climb, fall, watch_me, rest, up
  log                 Show last 10 log entries
  help                Show this message
  quit / exit         Exit simulator
-----------------------------------------------
Examples:
  voice take
  voice watch me
  sensor load_cell_n=680
  sensor cv_climber_detected=True
  sensor cv_clip_confidence=0.9
  scenario climb
"""

def parse_sensor_value(key, val_str):
    if val_str.lower() in ("true", "false"):
        return val_str.lower() == "true"
    try:
        return float(val_str)
    except ValueError:
        return val_str


def run_cli(aria: ARIAStateMachine):
    print("\n+==================================================+")
    print("|   ARIA - Autonomous Rope Intelligence System  |")
    print("|   Lead Auto Belay Simulator v0.1                |")
    print("|   Type 'help' for commands                     |")
    print("+==================================================+\n")

    while True:
        try:
            raw = input("\nARIA> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            aria._running = False
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit"):
            aria._running = False
            print("ARIA system shutdown.")
            break

        elif cmd == "help":
            print(HELP_TEXT)

        elif cmd == "status":
            print(aria.status())

        elif cmd == "log":
            for entry in aria.log.tail(10):
                print(entry)

        elif cmd == "voice":
            voice_str = " ".join(parts[1:]).lower()
            if voice_str:
                aria.inject_voice(voice_str)
            else:
                print("Usage: voice <command>")

        elif cmd == "sensor":
            if len(parts) < 2 or "=" not in parts[1]:
                print("Usage: sensor <key>=<value>")
            else:
                for arg in parts[1:]:
                    if "=" in arg:
                        key, val_str = arg.split("=", 1)
                        val = parse_sensor_value(key, val_str)
                        aria.inject_sensor(**{key: val})
                        print(f"  Set {key} = {val}")

        elif cmd == "scenario":
            if len(parts) < 2:
                print("Usage: scenario <climb|fall|watch_me|rest|up>")
            else:
                name = parts[1].lower()
                if name == "climb":
                    t = threading.Thread(
                        target=scenario_normal_climb, args=(aria,), daemon=True
                    )
                    t.start()
                elif name == "fall":
                    t = threading.Thread(
                        target=scenario_fall, args=(aria,), daemon=True
                    )
                    t.start()
                elif name == "watch_me":
                    t = threading.Thread(
                        target=scenario_watch_me, args=(aria,), daemon=True
                    )
                    t.start()
                elif name == "rest":
                    t = threading.Thread(
                        target=scenario_rest, args=(aria,), daemon=True
                    )
                    t.start()
                elif name == "up":
                    t = threading.Thread(
                        target=scenario_up, args=(aria,), daemon=True
                    )
                    t.start()
                else:
                    print(f"Unknown scenario: {name}")
        else:
            print(f"Unknown command: '{cmd}'. Type 'help'.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    aria = ARIAStateMachine()

    # Start tick loop in background thread
    tick_thread = threading.Thread(
        target=run_tick_loop, args=(aria, 20), daemon=True
    )
    tick_thread.start()

    # Run interactive CLI on main thread
    run_cli(aria)
