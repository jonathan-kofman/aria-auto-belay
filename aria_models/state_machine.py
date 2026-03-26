# aria_models/state_machine.py — ARIA 9-state machine
# =====================================================
# Matches firmware/stm32/aria_main.cpp exactly.
# Run: python tools/aria_constants_sync.py --verbose  to verify alignment.
#
# Synced with root state_machine.py. CLIMBING_PAUSED state handles zone
# intrusion (unexpected body in camera frame). Motor holds. Auto-exits
# to CLIMBING after ZONE_PAUSE_TIMEOUT_S if zone clears.

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

# ── Thresholds — must match PYTHON_CONSTANTS in tools/aria_constants_sync.py ─
TENSION_CLIMB_MIN_N     = 15.0
TENSION_TAKE_CONFIRM_N  = 200.0
TENSION_LOWER_EXIT_N    = 15.0
TAKE_CONFIRM_WINDOW_S   = 0.5
VOICE_CONFIDENCE_MIN    = 0.85
CLIP_DETECT_CONFIDENCE  = 0.75
CLIP_PAYOUT_M           = 0.65
TENSION_TARGET_N        = 40.0
TENSION_TIGHT_N         = 60.0
REST_TIMEOUT_S          = 600.0
WATCH_ME_TIMEOUT_S      = 180.0
ZONE_PAUSE_TIMEOUT_S    = 10.0
ESTOP_BRAKE_DELAY_MS    = 50.0
WATCHDOG_TIMEOUT_MS     = 500.0


class State(Enum):
    IDLE            = auto()
    CLIMBING        = auto()
    CLIPPING        = auto()
    TAKE            = auto()
    REST            = auto()
    LOWER           = auto()
    WATCH_ME        = auto()
    UP              = auto()
    CLIMBING_PAUSED = auto()   # zone intrusion hold
    ESTOP           = auto()


MOTOR_MODES = {
    State.IDLE:            "OFF",
    State.CLIMBING:        "TENSION",
    State.CLIPPING:        "PAYOUT_FAST",
    State.TAKE:            "RETRACT_HOLD",
    State.REST:            "HOLD",
    State.LOWER:           "PAYOUT_SLOW",
    State.WATCH_ME:        "TENSION_TIGHT",
    State.UP:              "UP_DRIVE",
    State.CLIMBING_PAUSED: "HOLD",
    State.ESTOP:           "OFF",
}

VALID_TRANSITIONS = {
    State.IDLE:            {State.CLIMBING, State.ESTOP},
    State.CLIMBING:        {State.CLIPPING, State.TAKE, State.REST,
                            State.LOWER, State.WATCH_ME, State.UP,
                            State.CLIMBING_PAUSED, State.IDLE, State.ESTOP},
    State.CLIPPING:        {State.CLIMBING, State.ESTOP},
    State.TAKE:            {State.CLIMBING, State.LOWER, State.ESTOP},
    State.REST:            {State.CLIMBING, State.ESTOP},
    State.LOWER:           {State.IDLE, State.ESTOP},
    State.WATCH_ME:        {State.CLIMBING, State.ESTOP},
    State.UP:              {State.CLIMBING, State.ESTOP},
    State.CLIMBING_PAUSED: {State.CLIMBING, State.ESTOP},
    State.ESTOP:           set(),
}


@dataclass
class Inputs:
    voice: str       = ""
    tension_N: float = 0.0
    cv_clip: bool    = False
    cv_zone: bool    = False   # unexpected body in camera zone
    estop: bool      = False
    time_s: float    = 0.0
    dt: float        = 0.02


@dataclass
class Outputs:
    motor_mode: str
    state: State
    fault_code: str      = ""
    rope_payout_m: float = 0.0


class AriaStateMachine:

    def __init__(self):
        self.state = State.IDLE
        self.last_voice = ""
        self.take_voice_time:       Optional[float] = None
        self.rest_start_time:       Optional[float] = None
        self.watch_me_start_time:   Optional[float] = None
        self.zone_pause_start_time: Optional[float] = None
        self.pre_pause_state:       Optional[State] = None

    def _go(self, new_state: State) -> None:
        self.state = new_state

    def _out(self, payout_m: float = 0.0, fault: str = "") -> Outputs:
        return Outputs(
            motor_mode    = MOTOR_MODES[self.state],
            state         = self.state,
            fault_code    = fault,
            rope_payout_m = payout_m,
        )

    def step(self, inp: Inputs) -> Outputs:
        t = inp.time_s
        v = inp.voice.lower().strip()

        # E-stop overrides all
        if inp.estop:
            self._go(State.ESTOP)
            return self._out(fault="ESTOP_TRIGGERED")

        # Latch take voice time globally
        if v == "take":
            self.take_voice_time = t
            self.last_voice = "take"

        s = self.state

        # Zone intrusion: only interrupts CLIMBING
        if inp.cv_zone and s == State.CLIMBING:
            self.pre_pause_state       = s
            self.zone_pause_start_time = t
            self._go(State.CLIMBING_PAUSED)
            return self._out()

        if s == State.CLIMBING_PAUSED:
            elapsed   = t - (self.zone_pause_start_time or t)
            zone_gone = not inp.cv_zone
            timed_out = elapsed >= ZONE_PAUSE_TIMEOUT_S
            if zone_gone or timed_out:
                resume = self.pre_pause_state or State.CLIMBING
                self.zone_pause_start_time = None
                self.pre_pause_state       = None
                self._go(resume)
                return self._out()
            return self._out()

        if s == State.IDLE:
            if inp.tension_N > TENSION_CLIMB_MIN_N:
                self._go(State.CLIMBING)
                return self._out()
            return self._out()

        if s == State.CLIMBING:
            if inp.cv_clip:
                self._go(State.CLIPPING)
                return self._out(payout_m=CLIP_PAYOUT_M)
            if self.take_voice_time is not None:
                elapsed = t - self.take_voice_time
                if elapsed < TAKE_CONFIRM_WINDOW_S:
                    if inp.tension_N > TENSION_TAKE_CONFIRM_N:
                        self.take_voice_time = None
                        self._go(State.TAKE)
                        return self._out()
                else:
                    self.take_voice_time = None
            if v == "rest":
                self.rest_start_time = t
                self._go(State.REST)
                return self._out()
            if v == "lower":
                self._go(State.LOWER)
                return self._out()
            if v == "watch me":
                self.watch_me_start_time = t
                self._go(State.WATCH_ME)
                return self._out()
            if v == "up":
                self._go(State.UP)
                return self._out()
            return self._out()

        if s == State.CLIPPING:
            if not inp.cv_clip or v == "climbing":
                self._go(State.CLIMBING)
                return self._out()
            return self._out(payout_m=CLIP_PAYOUT_M)

        if s == State.TAKE:
            if v == "climbing":
                self._go(State.CLIMBING)
                return self._out()
            if v == "lower":
                self._go(State.LOWER)
                return self._out()
            return self._out()

        if s == State.REST:
            if v == "climbing":
                self.rest_start_time = None
                self._go(State.CLIMBING)
                return self._out()
            if self.rest_start_time is not None:
                if (t - self.rest_start_time) >= REST_TIMEOUT_S:
                    self.rest_start_time = None
                    self._go(State.CLIMBING)
                    return self._out()
            return self._out()

        if s == State.LOWER:
            if inp.tension_N < TENSION_LOWER_EXIT_N:
                self._go(State.IDLE)
                return self._out()
            return self._out()

        if s == State.WATCH_ME:
            if v == "climbing":
                self.watch_me_start_time = None
                self._go(State.CLIMBING)
                return self._out()
            if self.watch_me_start_time is not None:
                if (t - self.watch_me_start_time) >= WATCH_ME_TIMEOUT_S:
                    self.watch_me_start_time = None
                    self._go(State.CLIMBING)
                    return self._out()
            return self._out()

        if s == State.UP:
            if v == "climbing":
                self._go(State.CLIMBING)
                return self._out()
            return self._out()

        if s == State.ESTOP:
            return self._out(fault="ESTOP_LATCHED")

        return self._out(fault="UNKNOWN_STATE")

    def reset(self):
        """Reset to IDLE. Call after watchdog recovery or power cycle."""
        self.__init__()
