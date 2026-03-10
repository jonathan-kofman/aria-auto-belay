#!/usr/bin/env python3
"""
aria_hil_test.py — ARIA Hardware-in-the-Loop Test Runner
=========================================================
Run after every STM32 flash before trusting hardware with real loads.

Usage:
    python tools/aria_hil_test.py --port COM3
    python tools/aria_hil_test.py --port /dev/ttyUSB0 --baud 115200
    python tools/aria_hil_test.py --port COM3 --suite quick
    python tools/aria_hil_test.py --port COM3 --suite full
    python tools/aria_hil_test.py --mock   # run against Python model (no hardware)

What it does:
  1. Connects to STM32 over serial
  2. Sends scripted UART commands simulating sensor readings
  3. Reads back state machine output
  4. Validates every transition against expected behavior
  5. Produces pass/fail report

STM32 UART protocol expected:
  TX (to STM32):   CMD:<type>:<value>\n
    CMD:TENSION:<float_N>
    CMD:VOICE:<command_string>
    CMD:CLIP:<0|1>
    CMD:ESTOP:<0|1>
    CMD:RESET        (reset state machine)
    CMD:STATUS       (request current state)

  RX (from STM32):  S:<state_int>:<tension>:<rope_pos>:<motor_mode>\n
  State int mapping must match firmware State enum order.

If your firmware uses a different protocol, update PROTOCOL below.
"""

import argparse
import sys
import time
import json
import threading
import queue
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure project root is on path when run as tools/aria_hil_test.py
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# ── Protocol config — update to match your actual firmware ────────────────────
PROTOCOL = {
    'tension_cmd':    'CMD:TENSION:{value:.2f}',
    'voice_cmd':      'CMD:VOICE:{value}',
    'clip_cmd':       'CMD:CLIP:{value}',
    'estop_cmd':      'CMD:ESTOP:{value}',
    'reset_cmd':      'CMD:RESET',
    'status_cmd':     'CMD:STATUS',
    'response_prefix':'S:',
    'state_int_map': {
        0: 'IDLE', 1: 'CLIMBING', 2: 'CLIPPING',
        3: 'TAKE', 4: 'REST',     5: 'LOWER',
        6: 'WATCH_ME', 7: 'UP',   8: 'ESTOP',
    },
}

# ── Test case definition ───────────────────────────────────────────────────────
@dataclass
class HILStep:
    """A single step in a hardware-in-the-loop test."""
    description:     str
    commands:        list         # list of (cmd_type, value) tuples
    wait_s:          float = 0.2  # wait after commands before reading state
    expect_state:    str  = ''    # expected state after this step
    expect_motor:    str  = ''    # expected motor mode (optional)
    allow_states:    list = field(default_factory=list)  # any of these is OK
    timeout_s:       float = 2.0  # max time to wait for expected state


@dataclass
class HILTest:
    """A complete HIL test case."""
    name:        str
    description: str
    steps:       list
    suite:       str = 'full'     # 'quick' or 'full'


# ── Test suite definition ──────────────────────────────────────────────────────
HIL_TESTS = [

    HILTest(
        name='boot_state',
        description='Device powers on in IDLE with motor OFF',
        suite='quick',
        steps=[
            HILStep('Reset to known state', [('reset', '')], wait_s=0.5,
                    expect_state='IDLE', expect_motor='OFF'),
            HILStep('Verify IDLE with no tension', [('tension', 0.0)], wait_s=0.2,
                    expect_state='IDLE'),
        ]
    ),

    HILTest(
        name='idle_to_climbing',
        description='Tension above threshold transitions IDLE -> CLIMBING',
        suite='quick',
        steps=[
            HILStep('Reset', [('reset', '')], wait_s=0.5, expect_state='IDLE'),
            HILStep('Apply climbing tension (45N)', [('tension', 45.0)], wait_s=0.3,
                    expect_state='CLIMBING', expect_motor='TENSION'),
            HILStep('Verify stays CLIMBING', [('tension', 45.0)], wait_s=0.3,
                    expect_state='CLIMBING'),
        ]
    ),

    HILTest(
        name='take_two_factor',
        description='TAKE requires both voice AND load >200N within 500ms window',
        suite='quick',
        steps=[
            HILStep('Reset, enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Voice "take" with no load', [('voice', 'take')], wait_s=0.6,
                    expect_state='CLIMBING',  # window expires — should NOT go to TAKE
                    allow_states=['CLIMBING']),
            HILStep('Voice "take" + load confirmation', [('voice', 'take')], wait_s=0.1),
            HILStep('Load confirms within window', [('tension', 250.0)], wait_s=0.3,
                    expect_state='TAKE', expect_motor='RETRACT_HOLD'),
        ]
    ),

    HILTest(
        name='estop_overrides_all',
        description='ESTOP button overrides any active state immediately',
        suite='quick',
        steps=[
            HILStep('Reset, enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Trigger ESTOP', [('estop', 1)], wait_s=0.2,
                    expect_state='ESTOP', expect_motor='OFF'),
            HILStep('ESTOP persists under tension', [('tension', 100.0)], wait_s=0.3,
                    expect_state='ESTOP'),
            HILStep('ESTOP persists with voice', [('voice', 'climbing')], wait_s=0.3,
                    expect_state='ESTOP'),
        ]
    ),

    HILTest(
        name='take_to_lower_to_idle',
        description='Full descent cycle: TAKE -> LOWER -> IDLE',
        suite='quick',
        steps=[
            HILStep('Reset, climb, take', [('reset', ''), ('tension', 45.0)], wait_s=0.5),
            HILStep('Initiate TAKE', [('voice', 'take')], wait_s=0.1),
            HILStep('Confirm TAKE with load', [('tension', 250.0)], wait_s=0.3,
                    expect_state='TAKE'),
            HILStep('Hold tension', [('tension', 300.0)], wait_s=0.3,
                    expect_state='TAKE'),
            HILStep('Voice lower', [('voice', 'lower')], wait_s=0.3,
                    expect_state='LOWER', expect_motor='PAYOUT_SLOW'),
            HILStep('Reduce tension — approaching ground', [('tension', 20.0)], wait_s=0.3,
                    expect_state='LOWER'),
            HILStep('Tension drops to ground level', [('tension', 5.0)], wait_s=0.3,
                    expect_state='IDLE', expect_motor='OFF'),
        ]
    ),

    HILTest(
        name='clip_detection',
        description='CV clip signal triggers CLIPPING state and payout',
        suite='full',
        steps=[
            HILStep('Reset, enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Clip gesture detected', [('clip', 1)], wait_s=0.3,
                    expect_state='CLIPPING', expect_motor='PAYOUT_FAST'),
            HILStep('Clip gesture ends', [('clip', 0)], wait_s=0.3,
                    allow_states=['CLIPPING', 'CLIMBING']),
        ]
    ),

    HILTest(
        name='rest_and_resume',
        description='REST state holds position, voice "climbing" resumes',
        suite='full',
        steps=[
            HILStep('Reset, enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Voice rest', [('voice', 'rest')], wait_s=0.3,
                    expect_state='REST', expect_motor='HOLD'),
            HILStep('Tension changes — should stay REST', [('tension', 80.0)], wait_s=0.3,
                    expect_state='REST'),
            HILStep('Voice climbing resumes', [('voice', 'climbing')], wait_s=0.3,
                    expect_state='CLIMBING', expect_motor='TENSION'),
        ]
    ),

    HILTest(
        name='watch_me',
        description='WATCH_ME tightens tension, voice "climbing" releases',
        suite='full',
        steps=[
            HILStep('Reset, enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Voice watch me', [('voice', 'watch me')], wait_s=0.3,
                    expect_state='WATCH_ME', expect_motor='TENSION_TIGHT'),
            HILStep('Voice climbing', [('voice', 'climbing')], wait_s=0.3,
                    expect_state='CLIMBING'),
        ]
    ),

    HILTest(
        name='motor_off_in_idle',
        description='Motor is OFF whenever in IDLE state',
        suite='full',
        steps=[
            HILStep('Reset', [('reset', '')], wait_s=0.5,
                    expect_state='IDLE', expect_motor='OFF'),
            HILStep('Brief tension then release', [('tension', 45.0)], wait_s=0.3),
            HILStep('Back to idle', [('tension', 0.0)], wait_s=1.0,
                    allow_states=['IDLE', 'LOWER']),
        ]
    ),

    HILTest(
        name='watchdog_recovery',
        description='State machine recovers to safe state after simulated watchdog timeout',
        suite='full',
        steps=[
            HILStep('Enter CLIMBING', [('reset', ''), ('tension', 45.0)],
                    wait_s=0.5, expect_state='CLIMBING'),
            HILStep('Send reset (simulates watchdog)', [('reset', '')], wait_s=0.5,
                    expect_state='IDLE', expect_motor='OFF'),
        ]
    ),
]


# ── Mock serial interface (runs against Python model) ─────────────────────────
class MockSerial:
    """Simulates STM32 responses using the Python state machine model."""

    def __init__(self):
        from aria_models.state_machine import AriaStateMachine, Inputs, State
        self._sm      = AriaStateMachine()
        self._Inputs  = Inputs
        self._State   = State
        self._tension = 0.0
        self._clip    = False
        self._t       = 0.0
        self._dt      = 0.05
        self._rx_q    : queue.Queue = queue.Queue()

    def _step(self, voice='', estop=False):
        """Step state machine and enqueue response line."""
        inp = self._Inputs(
            voice=voice, tension_N=self._tension,
            cv_clip=self._clip, estop=estop,
            time_s=self._t, dt=self._dt)
        out = self._sm.step(inp)
        self._t += self._dt

        state_int = list(PROTOCOL['state_int_map'].values()).index(out.state.name)
        line = f"S:{state_int}:{self._tension:.2f}:0.00:{out.motor_mode}\n"
        self._rx_q.put(line.encode())

    def write(self, data: bytes):
        text = data.decode().strip()
        if text == PROTOCOL['reset_cmd']:
            from aria_models.state_machine import AriaStateMachine
            self._sm = AriaStateMachine()
            self._tension = 0.0; self._clip = False; self._t = 0.0
            # drain stale responses
            while not self._rx_q.empty():
                try: self._rx_q.get_nowait()
                except: break
            self._step()
        elif text.startswith('CMD:TENSION:'):
            self._tension = float(text.split(':')[2])
            self._step()
        elif text.startswith('CMD:VOICE:'):
            voice = ':'.join(text.split(':')[2:])
            self._step(voice=voice)
        elif text.startswith('CMD:CLIP:'):
            self._clip = bool(int(text.split(':')[2]))
            self._step()
        elif text.startswith('CMD:ESTOP:'):
            estop = bool(int(text.split(':')[2]))
            self._step(estop=estop)
        elif text == PROTOCOL['status_cmd']:
            self._step()

    def readline(self) -> bytes:
        # Drain to most recent response (last one in queue is the current state)
        last = None
        try:
            while True:
                last = self._rx_q.get_nowait()
        except queue.Empty:
            pass
        if last is not None:
            return last
        # Queue was empty — step once and return
        self._step()
        try:
            return self._rx_q.get(timeout=0.5)
        except queue.Empty:
            return b''

    def close(self): pass


# ── Real serial interface ─────────────────────────────────────────────────────
class RealSerial:
    def __init__(self, port: str, baud: int):
        import serial as ser_mod
        self._ser = ser_mod.Serial(port, baud, timeout=0.5)
        time.sleep(2.0)  # wait for STM32 reset after serial connect

    def write(self, data: bytes):
        self._ser.write(data)
        self._ser.flush()

    def readline(self) -> bytes:
        return self._ser.readline()

    def close(self):
        self._ser.close()


# ── Test runner ───────────────────────────────────────────────────────────────
class HILRunner:
    def __init__(self, serial_iface, verbose: bool = False):
        self._ser     = serial_iface
        self._verbose = verbose
        self._results = []

    def _send(self, cmd_type: str, value=''):
        """Send a command to the device."""
        if cmd_type == 'reset':
            line = PROTOCOL['reset_cmd'] + '\n'
        elif cmd_type == 'status':
            line = PROTOCOL['status_cmd'] + '\n'
        elif cmd_type == 'tension':
            line = PROTOCOL['tension_cmd'].format(value=float(value)) + '\n'
        elif cmd_type == 'voice':
            line = PROTOCOL['voice_cmd'].format(value=str(value)) + '\n'
        elif cmd_type == 'clip':
            line = PROTOCOL['clip_cmd'].format(value=int(value)) + '\n'
        elif cmd_type == 'estop':
            line = PROTOCOL['estop_cmd'].format(value=int(value)) + '\n'
        else:
            return
        self._ser.write(line.encode())

    def _read_state(self, timeout_s: float = 1.0) -> dict:
        """Read next state packet from device."""
        t_start = time.time()
        while time.time() - t_start < timeout_s:
            line = self._ser.readline()
            if not line:
                continue
            text = line.decode('utf-8', errors='ignore').strip()
            if text.startswith(PROTOCOL['response_prefix']):
                parts = text.split(':')
                if len(parts) >= 5:
                    try:
                        state_int  = int(parts[1])
                        tension    = float(parts[2])
                        rope_pos   = float(parts[3])
                        motor_mode = parts[4]
                        state_name = PROTOCOL['state_int_map'].get(state_int, f'UNKNOWN({state_int})')
                        return {'state': state_name, 'tension': tension,
                                'rope_pos': rope_pos, 'motor_mode': motor_mode}
                    except (ValueError, IndexError):
                        continue
        return {}  # timeout

    def run_test(self, test: HILTest) -> dict:
        """Run a single HIL test. Returns result dict."""
        result = {
            'name':       test.name,
            'description':test.description,
            'passed':     True,
            'steps':      [],
            'error':      '',
        }

        if self._verbose:
            print(f"\n  Running: {test.name}")
            print(f"  {test.description}")

        for step_idx, step in enumerate(test.steps):
            step_result = {'description': step.description, 'passed': True, 'detail': ''}

            # Send all commands for this step
            for cmd_type, value in step.commands:
                self._send(cmd_type, value)
                time.sleep(0.02)  # small inter-command gap

            # Wait
            time.sleep(step.wait_s)

            # Read state
            self._send('status')
            state_data = self._read_state(timeout_s=step.timeout_s)

            if not state_data:
                step_result['passed'] = False
                step_result['detail'] = f'Timeout - no response within {step.timeout_s}s'
                result['passed'] = False
                if self._verbose:
                    print(f"    Step {step_idx+1}: [FAIL] TIMEOUT - {step.description}")
                result['steps'].append(step_result)
                continue

            actual_state = state_data.get('state', '')
            actual_motor = state_data.get('motor_mode', '')

            # Check state expectation
            if step.expect_state:
                if actual_state != step.expect_state:
                    if actual_state not in step.allow_states:
                        step_result['passed'] = False
                        step_result['detail'] = (
                            f"State: expected '{step.expect_state}' "
                            f"(or {step.allow_states}), got '{actual_state}'")
                        result['passed'] = False

            # Check motor expectation
            if step.expect_motor and actual_motor != step.expect_motor:
                step_result['passed'] = False
                step_result['detail'] += (
                    f" Motor: expected '{step.expect_motor}', got '{actual_motor}'")
                result['passed'] = False

            step_result['actual_state'] = actual_state
            step_result['actual_motor'] = actual_motor
            step_result['raw'] = state_data

            if self._verbose:
                icon = '[PASS]' if step_result['passed'] else '[FAIL]'
                print(f"    Step {step_idx+1}: {icon} {step.description}")
                print(f"           State={actual_state} Motor={actual_motor}", end='')
                if not step_result['passed']:
                    print(f"  ← {step_result['detail']}", end='')
                print()

            result['steps'].append(step_result)

        return result

    def run_suite(self, suite: str = 'quick') -> list:
        """Run all tests in the specified suite."""
        tests = [t for t in HIL_TESTS if t.suite == suite or suite == 'full']
        results = []
        for test in tests:
            result = self.run_test(test)
            results.append(result)
            self._results.append(result)
        return results


def print_report(results: list, mock: bool = False):
    """Print final test report."""
    passed = sum(1 for r in results if r['passed'])
    failed = len(results) - passed

    print('\n' + '='*60)
    print('ARIA HIL TEST REPORT')
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'MOCK (Python model)' if mock else 'REAL HARDWARE'}")
    print('='*60)

    for r in results:
        icon = '[PASS]' if r['passed'] else '[FAIL]'
        print(f"\n{icon} {r['name']}")
        print(f"   {r['description']}")
        if not r['passed']:
            for step in r['steps']:
                if not step['passed']:
                    print(f"   FAIL at: {step['description']}")
                    print(f"           {step['detail']}")

    print('\n' + '-'*60)
    if failed == 0:
        print(f"[PASS] ALL TESTS PASSED ({passed}/{len(results)})")
        print("   Hardware matches firmware model - safe to proceed.")
    else:
        print(f"[FAIL] {failed} TEST(S) FAILED ({passed}/{len(results)} passed)")
        print("   Do NOT use this hardware until failures are resolved.")
    print('='*60 + '\n')

    return failed == 0


def save_report(results: list, mock: bool, path: Path):
    doc = {
        'timestamp': datetime.now().isoformat(),
        'mode': 'mock' if mock else 'hardware',
        'passed': sum(1 for r in results if r['passed']),
        'failed': sum(1 for r in results if not r['passed']),
        'results': results,
    }
    path.write_text(json.dumps(doc, indent=2))


def main():
    parser = argparse.ArgumentParser(description='ARIA Hardware-in-the-Loop Test Runner')
    parser.add_argument('--port',    type=str,  default='',       help='Serial port (e.g. COM3, /dev/ttyUSB0)')
    parser.add_argument('--baud',    type=int,  default=115200,   help='Baud rate')
    parser.add_argument('--mock',    action='store_true',         help='Run against Python model (no hardware needed)')
    parser.add_argument('--suite',   type=str,  default='quick',  choices=['quick', 'full'], help='Test suite')
    parser.add_argument('--verbose', '-v', action='store_true',   help='Show step-by-step output')
    parser.add_argument('--json-out',type=Path, default=None,     help='Save JSON report')
    args = parser.parse_args()

    if not args.mock and not args.port:
        print("ERROR: Specify --port <COM3> or use --mock for Python model testing.")
        print("       Example: python tools/aria_hil_test.py --port COM3 --suite quick")
        sys.exit(2)

    # Connect
    print(f"\nARIA HIL Test Runner - suite={args.suite}")
    if args.mock:
        print("Mode: MOCK - running against Python state machine model")
        serial_iface = MockSerial()
    else:
        print(f"Mode: HARDWARE - connecting to {args.port} @ {args.baud} baud")
        try:
            serial_iface = RealSerial(args.port, args.baud)
            print("Connected.")
        except Exception as e:
            print(f"ERROR: Could not connect: {e}")
            sys.exit(2)

    try:
        runner  = HILRunner(serial_iface, verbose=args.verbose)
        results = runner.run_suite(suite=args.suite)
        all_passed = print_report(results, mock=args.mock)

        if args.json_out:
            save_report(results, args.mock, args.json_out)
            print(f"Report saved to {args.json_out}")

        sys.exit(0 if all_passed else 1)

    finally:
        serial_iface.close()


if __name__ == '__main__':
    main()
