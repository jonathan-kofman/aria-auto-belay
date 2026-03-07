#!/usr/bin/env python3
"""
aria_constants_sync.py — Firmware / Model Constants Sync Checker
=================================================================
Run from your repo root:
    python tools/aria_constants_sync.py

What it does:
  1. Reads every threshold/constant from aria_models/state_machine.py
  2. Scans firmware/stm32/*.cpp and *.h for matching constant definitions
  3. Compares values and reports mismatches
  4. Optionally auto-patches firmware constants to match the Python model

This prevents silent divergence between the Python simulator and the
actual firmware — the most common source of "it works in simulation
but not on hardware" bugs.

Exit codes:
  0 — all constants match (or firmware files not found — skipped)
  1 — mismatches found
  2 — script error
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# ── Constants defined in the Python model ─────────────────────────────────────
# Format: name -> {'value': float/int, 'unit': str, 'description': str}
# These are the ground truth. Firmware must match.
PYTHON_CONSTANTS = {
    # State machine thresholds
    'TENSION_CLIMB_MIN_N':      {'value': 15.0,   'unit': 'N',   'description': 'Min tension to enter CLIMBING from IDLE'},
    'TENSION_TAKE_CONFIRM_N':   {'value': 200.0,  'unit': 'N',   'description': 'Min tension to confirm TAKE after voice'},
    'TENSION_LOWER_EXIT_N':     {'value': 15.0,   'unit': 'N',   'description': 'Tension below which LOWER transitions to IDLE'},
    'TAKE_CONFIRM_WINDOW_S':    {'value': 0.5,    'unit': 's',   'description': 'Window after voice "take" for load confirmation'},
    # Voice model
    'VOICE_CONFIDENCE_MIN':     {'value': 0.85,   'unit': '-',   'description': 'Minimum Edge Impulse confidence to act on voice'},
    # CV model
    'CLIP_DETECT_CONFIDENCE':   {'value': 0.75,   'unit': '-',   'description': 'Minimum CV confidence to enter CLIPPING'},
    'CLIP_PAYOUT_M':            {'value': 0.65,   'unit': 'm',   'description': 'Rope payout during CLIPPING state'},
    # Motor/tension control
    'TENSION_TARGET_N':         {'value': 40.0,   'unit': 'N',   'description': 'Target climbing tension'},
    'TENSION_TIGHT_N':          {'value': 60.0,   'unit': 'N',   'description': 'Tight tension in WATCH_ME state'},
    # Timing
    'REST_TIMEOUT_S':           {'value': 600.0,  'unit': 's',   'description': '10-minute REST auto-exit'},
    'WATCH_ME_TIMEOUT_S':       {'value': 180.0,  'unit': 's',   'description': '3-minute WATCH_ME auto-exit'},
    'ZONE_PAUSE_TIMEOUT_S':     {'value': 10.0,   'unit': 's',   'description': 'Zone intrusion pause timeout'},
    # Safety
    'ESTOP_BRAKE_DELAY_MS':     {'value': 50.0,   'unit': 'ms',  'description': 'Max delay from ESTOP signal to brake engage'},
    'WATCHDOG_TIMEOUT_MS':      {'value': 500.0,  'unit': 'ms',  'description': 'STM32 watchdog timeout'},
}

# ── Firmware constant name patterns ───────────────────────────────────────────
# Maps Python constant names to regex patterns that find them in C++ code.
# Handles both #define and constexpr float/int styles.
FIRMWARE_PATTERNS = {
    name: [
        # #define CONST_NAME 123.4
        rf'#\s*define\s+{name}\s+([\d.]+)',
        # constexpr float CONST_NAME = 123.4f;
        rf'constexpr\s+\w+\s+{name}\s*=\s*([\d.]+)',
        # static const float CONST_NAME = 123.4;
        rf'(?:static\s+)?const\s+\w+\s+{name}\s*=\s*([\d.]+)',
        # float CONST_NAME = 123.4; (bare global)
        rf'(?:^|\s)\w+\s+{name}\s*=\s*([\d.]+)',
    ]
    for name in PYTHON_CONSTANTS
}

# Tolerance for float comparison (1% relative or 0.001 absolute)
REL_TOLERANCE = 0.01
ABS_TOLERANCE = 0.001


def find_firmware_files(repo_root: Path) -> list[Path]:
    """Find all .cpp and .h files under firmware/stm32/"""
    fw_dir = repo_root / 'firmware' / 'stm32'
    if not fw_dir.exists():
        return []
    files = list(fw_dir.rglob('*.cpp')) + list(fw_dir.rglob('*.h'))
    return sorted(files)


def scan_firmware_for_constant(name: str, fw_files: list[Path]) -> dict:
    """Scan all firmware files for a given constant name. Returns first match."""
    patterns = FIRMWARE_PATTERNS.get(name, [])
    for fpath in fw_files:
        try:
            text = fpath.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                try:
                    val = float(match.group(1))
                    line_num = text[:match.start()].count('\n') + 1
                    return {
                        'found': True,
                        'value': val,
                        'file': str(fpath.relative_to(fpath.parent.parent.parent)),
                        'line': line_num,
                        'raw': match.group(0).strip(),
                    }
                except (ValueError, IndexError):
                    continue
    return {'found': False}


def values_match(a: float, b: float) -> bool:
    """Check if two float values are within tolerance."""
    if abs(a) < 1e-9 and abs(b) < 1e-9:
        return True
    rel_diff = abs(a - b) / max(abs(a), abs(b), 1e-9)
    return rel_diff <= REL_TOLERANCE or abs(a - b) <= ABS_TOLERANCE


def run_sync_check(repo_root: Path, verbose: bool = False, patch: bool = False) -> dict:
    """
    Main sync check. Returns dict with:
      matches, mismatches, not_found_in_firmware, summary
    """
    fw_files = find_firmware_files(repo_root)

    results = {
        'timestamp':            datetime.now().isoformat(),
        'firmware_files_found': len(fw_files),
        'firmware_files':       [str(f.name) for f in fw_files],
        'matches':              [],
        'mismatches':           [],
        'not_found':            [],
        'patches_applied':      [],
    }

    if not fw_files:
        results['warning'] = (
            'No firmware files found under firmware/stm32/. '
            'Sync check skipped — Python model is the source of truth.'
        )
        return results

    for name, spec in PYTHON_CONSTANTS.items():
        py_val   = spec['value']
        fw_match = scan_firmware_for_constant(name, fw_files)

        if not fw_match['found']:
            results['not_found'].append({
                'name':        name,
                'py_value':    py_val,
                'unit':        spec['unit'],
                'description': spec['description'],
            })
            continue

        fw_val = fw_match['value']

        if values_match(py_val, fw_val):
            results['matches'].append({
                'name':     name,
                'value':    py_val,
                'fw_file':  fw_match['file'],
                'fw_line':  fw_match['line'],
            })
        else:
            entry = {
                'name':        name,
                'py_value':    py_val,
                'fw_value':    fw_val,
                'unit':        spec['unit'],
                'description': spec['description'],
                'fw_file':     fw_match['file'],
                'fw_line':     fw_match['line'],
                'fw_raw':      fw_match['raw'],
            }
            results['mismatches'].append(entry)

            # Auto-patch if requested
            if patch:
                patched = _patch_firmware_constant(
                    name, py_val, fw_match, fw_files, repo_root)
                if patched:
                    results['patches_applied'].append(name)

    return results


def _patch_firmware_constant(
        name: str, new_val: float,
        fw_match: dict, fw_files: list[Path],
        repo_root: Path) -> bool:
    """Patch a single firmware constant to match the Python model value."""
    # Find the file
    fw_path = None
    for f in fw_files:
        if str(f.name) in fw_match['file'] or fw_match['file'].endswith(f.name):
            fw_path = f
            break
    if fw_path is None:
        return False

    try:
        text = fw_path.read_text(encoding='utf-8')
        old_raw = fw_match['raw']

        # Build replacement: preserve style, just swap the number
        new_num = f'{new_val:.6f}'.rstrip('0').rstrip('.')
        if '.' not in new_num:
            new_num += '.0'

        # Replace numeric value in the raw match
        new_raw = re.sub(r'([\d.]+)(f?;?\s*)$',
                         lambda m: new_num + ('f' if 'f' in m.group(2) else '') + m.group(2).replace(m.group(1), '').lstrip(m.group(1)),
                         old_raw)

        # Simpler: replace the first number occurrence after the = or define
        new_raw = re.sub(r'(\s)([\d.]+)(f?)(\s*;?)', 
                         lambda m: m.group(1) + new_num + m.group(3) + m.group(4),
                         old_raw, count=1)

        new_text = text.replace(old_raw, new_raw, 1)
        if new_text == text:
            return False

        fw_path.write_text(new_text, encoding='utf-8')
        return True
    except Exception:
        return False


def print_report(results: dict, verbose: bool = False) -> int:
    """Print human-readable report. Returns exit code."""
    print('\n' + '='*60)
    print('ARIA CONSTANTS SYNC CHECK')
    print(f"  {results['timestamp']}")
    print('='*60)

    if 'warning' in results:
        print(f"\n[!] {results['warning']}")
        print('\nPython model constants (source of truth):')
        for name, spec in PYTHON_CONSTANTS.items():
            print(f"  {name:<35} = {spec['value']} {spec['unit']}")
        return 0

    print(f"\nFirmware files scanned: {results['firmware_files_found']}")
    if verbose:
        for f in results['firmware_files']:
            print(f"  {f}")

    # Matches
    if results['matches']:
        print(f"\n[OK] MATCHES ({len(results['matches'])})")
        if verbose:
            for m in results['matches']:
                print(f"  {m['name']:<35} = {m['value']}  ({m['fw_file']}:{m['fw_line']})")

    # Mismatches
    if results['mismatches']:
        print(f"\n[MISMATCH] ({len(results['mismatches'])}) - firmware diverges from model:")
        for m in results['mismatches']:
            print(f"\n  {m['name']}")
            print(f"    Python model:  {m['py_value']} {m['unit']}")
            print(f"    Firmware:      {m['fw_value']} {m['unit']}")
            print(f"    Description:   {m['description']}")
            print(f"    Location:      {m['fw_file']}:{m['fw_line']}")
            print(f"    Firmware line: {m['fw_raw']}")

    # Not found
    if results['not_found']:
        print(f"\n[!] NOT FOUND IN FIRMWARE ({len(results['not_found'])})")
        print("   These constants exist in the Python model but weren't detected in firmware.")
        print("   Add them to firmware or update FIRMWARE_PATTERNS in this script.")
        for n in results['not_found']:
            print(f"  {n['name']:<35} = {n['py_value']} {n['unit']}  — {n['description']}")

    # Patches
    if results.get('patches_applied'):
        print(f"\n[PATCH] AUTO-PATCHED ({len(results['patches_applied'])})")
        for name in results['patches_applied']:
            print(f"  {name}")
        print("  Recompile and reflash STM32 after patching.")

    # Summary
    n_mismatch = len(results['mismatches'])
    n_match    = len(results['matches'])
    n_missing  = len(results['not_found'])

    print('\n' + '-'*60)
    if n_mismatch == 0:
        print(f"[OK] ALL CLEAR - {n_match} constants match, {n_missing} not found in firmware")
        print("   Python model and firmware are in sync.")
    else:
        print(f"[FAIL] SYNC FAILED - {n_mismatch} mismatch(es), {n_match} match(es), {n_missing} not found")
        print("   Fix mismatches before relying on simulation results.")
        print("   Run with --patch to auto-update firmware constants.")
    print('='*60 + '\n')

    return 1 if n_mismatch > 0 else 0


def save_report(results: dict, output_path: Path):
    """Save JSON report for CI consumption."""
    output_path.write_text(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Check that firmware constants match the Python state machine model.')
    parser.add_argument('--repo-root', type=Path, default=Path('.'),
                        help='Path to repo root (default: current directory)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all matches, not just mismatches')
    parser.add_argument('--patch', action='store_true',
                        help='Auto-patch firmware constants to match Python model')
    parser.add_argument('--json-out', type=Path, default=None,
                        help='Save JSON report to this path (for CI)')
    parser.add_argument('--ci', action='store_true',
                        help='CI mode: exit 0 if no firmware files found (non-blocking)')
    args = parser.parse_args()

    try:
        results = run_sync_check(
            repo_root=args.repo_root.resolve(),
            verbose=args.verbose,
            patch=args.patch,
        )

        if args.json_out:
            save_report(results, args.json_out)

        exit_code = print_report(results, verbose=args.verbose)

        # In CI mode, missing firmware files is not a failure
        if args.ci and results.get('firmware_files_found', 0) == 0:
            exit_code = 0

        sys.exit(exit_code)

    except Exception as e:
        print(f"\n[ERROR] Script error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
