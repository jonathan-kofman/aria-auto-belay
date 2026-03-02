# aria_models/state_machine.py

from enum import Enum, auto
from dataclasses import dataclass

class State(Enum):
    IDLE = auto()
    CLIMBING = auto()
    CLIPPING = auto()
    TAKE = auto()
    REST = auto()
    LOWER = auto()
    WATCH_ME = auto()
    UP = auto()
    ESTOP = auto()

@dataclass
class Inputs:
    voice: str = ""          # "take", "lower", "rest", "watch me", "up", "climbing"
    tension_N: float = 0.0   # load cell reading
    cv_clip: bool = False    # clip gesture detected
    estop: bool = False      # e-stop button
    time_s: float = 0.0      # current time
    dt: float = 0.02         # step size

@dataclass
class Outputs:
    motor_mode: str          # e.g. "OFF", "TENSION", "PAYOUT_FAST", "RETRACT", etc.
    state: State

class AriaStateMachine:
    def __init__(self):
        self.state = State.IDLE
        self.last_voice = ""
        self.take_voice_time = None   # for 500 ms confirmation window
        self.rest_start_time = None
        self.watch_me_start_time = None

    def step(self, inp: Inputs) -> Outputs:
        if inp.estop:
            self.state = State.ESTOP
            return Outputs(motor_mode="OFF", state=self.state)

        s = self.state
        v = inp.voice.lower().strip()

        # --- handle "take" confirmation window ---
        if v == "take":
            self.take_voice_time = inp.time_s
            self.last_voice = "take"

        # IDLE
        if s == State.IDLE:
            if inp.tension_N > 15:   # climber present
                self.state = State.CLIMBING
                return Outputs(motor_mode="TENSION", state=self.state)
            return Outputs(motor_mode="OFF", state=self.state)

        # CLIMBING
        if s == State.CLIMBING:
            if inp.cv_clip:
                self.state = State.CLIPPING
                return Outputs(motor_mode="PAYOUT_FAST", state=self.state)

            # TAKE two-factor: voice + >200N within 0.5s
            if self.take_voice_time is not None:
                if (inp.time_s - self.take_voice_time) < 0.5 and inp.tension_N > 200:
                    self.state = State.TAKE
                    self.take_voice_time = None
                    return Outputs(motor_mode="RETRACT_HOLD", state=self.state)
                # window expired with no load
                if (inp.time_s - self.take_voice_time) >= 0.5:
                    self.take_voice_time = None

            if v == "rest":
                self.state = State.REST
                self.rest_start_time = inp.time_s
                return Outputs(motor_mode="HOLD", state=self.state)

            if v == "lower":
                self.state = State.LOWER
                return Outputs(motor_mode="PAYOUT_SLOW", state=self.state)

            if v == "watch me":
                self.state = State.WATCH_ME
                self.watch_me_start_time = inp.time_s
                return Outputs(motor_mode="TENSION_TIGHT", state=self.state)

            if v == "up":
                self.state = State.UP
                return Outputs(motor_mode="UP_DRIVE", state=self.state)

            # default: keep climbing with 40 N tension
            return Outputs(motor_mode="TENSION", state=self.state)

        # CLIPPING -> back to CLIMBING after fixed time (handled by caller)
        if s == State.CLIPPING:
            if v == "take":
                # allow TAKE even during clipping if load present
                self.state = State.CLIMBING
                return self.step(inp)
            # otherwise caller will switch back to CLIMBING after a timeout
            return Outputs(motor_mode="PAYOUT_FAST", state=self.state)

        # TAKE
        if s == State.TAKE:
            if v == "climbing":
                self.state = State.CLIMBING
                return Outputs(motor_mode="TENSION", state=self.state)
            if v == "lower":
                self.state = State.LOWER
                return Outputs(motor_mode="PAYOUT_SLOW", state=self.state)
            return Outputs(motor_mode="RETRACT_HOLD", state=self.state)

        # REST
        if s == State.REST:
            if v == "climbing":
                self.state = State.CLIMBING
                return Outputs(motor_mode="TENSION", state=self.state)
            # 10-minute timeout handled by caller with time_s
            return Outputs(motor_mode="HOLD", state=self.state)

        # LOWER
        if s == State.LOWER:
            if inp.tension_N < 15:   # ground
                self.state = State.IDLE
                return Outputs(motor_mode="OFF", state=self.state)
            return Outputs(motor_mode="PAYOUT_SLOW", state=self.state)

        # WATCH_ME
        if s == State.WATCH_ME:
            if v == "climbing":
                self.state = State.CLIMBING
                return Outputs(motor_mode="TENSION", state=self.state)
            # 3-minute timeout handled by caller
            return Outputs(motor_mode="TENSION_TIGHT", state=self.state)

        # UP
        if s == State.UP:
            if v == "climbing":
                self.state = State.CLIMBING
                return Outputs(motor_mode="TENSION", state=self.state)
            return Outputs(motor_mode="UP_DRIVE", state=self.state)

        # ESTOP
        if s == State.ESTOP:
            return Outputs(motor_mode="OFF", state=self.state)
