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
    # PID gains (from aria_pid_tuner; safe Kp for 10V limit at 360N error)
    'tensionPID_kp':            {'value': 0.022,  'unit': '-',   'description': 'Tension PID Kp'},
    'tensionPID_ki':            {'value': 0.413,  'unit': '-',   'description': 'Tension PID Ki'},
    'tensionPID_kd':            {'value': 0.0005, 'unit': '-',   'description': 'Tension PID Kd'},
}

# ── CEM constants (firmware names) — used when --from-cem or --cem-json ───────
# These map to actual firmware constant names in aria_main.cpp
CEM_CONSTANT_NAMES = [
    'SPOOL_R', 'GEAR_RATIO', 'MOTOR_VELOCITY_LIMIT',
    'T_BASELINE', 'T_RETRACT', 'SPD_RETRACT', 'SPD_FALL',
    'VOICE_CONF_MIN', 'CLIP_CONF_MIN', 'CLIP_SLACK_M',
    'T_TAKE', 'T_FALL', 'T_GROUND',
]
# Constants that must never be auto-patched (engineering review required)
NEVER_PATCH = {
    "T_FALL",        # hard safety limit
    "T_TAKE",        # ANSI confirmation threshold
    "SPD_FALL",      # motor yield speed, not clutch engagement
    "VOLTAGE_LIMIT", # hardware limit
    "v_mag_limit",   # hardware limit
    "tensionPID_kp", "tensionPID_ki", "tensionPID_kd",  # from aria_pid_tuner hardware testing
    "UART_BAUD",     # comms constant
}
# For reporting only: CEM reference value for never-patch constants (firmware may differ by design)
DESIGN_DECISION_CEM = {"SPD_FALL": 1.275}

# ── ESP32 sync constants (must match STM32) ───────────────────────────────────
ESP32_SYNC_CONSTANTS = {
    "VOICE_CONF_MIN": 0.85,
    "CLIP_CONF_MIN": 0.75,
    "CLIP_SLACK_M": 0.65,
    "FALL_TENSION_DELTA": 15.0,
}

# Shared comms constants (checked, never auto-patched)
SHARED_COMMS = {"UART_BAUD": 115200}

# CEM constant metadata (unit, description) for sync report
CEM_CONSTANT_META = {
    'SPOOL_R':            {'unit': 'm',   'description': 'Effective rope wrap radius'},
    'GEAR_RATIO':         {'unit': '-',   'description': 'Motor-to-spool gear ratio'},
    'MOTOR_VELOCITY_LIMIT': {'unit': 'rad/s', 'description': 'Motor shaft velocity limit'},
    'T_BASELINE':         {'unit': 'N',   'description': 'Target climbing tension'},
    'T_RETRACT':          {'unit': 'N',   'description': 'Retract tension'},
    'SPD_RETRACT':        {'unit': 'm/s', 'description': 'Max retract speed'},
    'SPD_FALL':           {'unit': 'm/s', 'description': 'Fall detection speed threshold'},
    'VOICE_CONF_MIN':     {'unit': '-',   'description': 'Voice confidence minimum'},
    'CLIP_CONF_MIN':      {'unit': '-',   'description': 'CV clip confidence minimum'},
    'CLIP_SLACK_M':       {'unit': 'm',   'description': 'Clip rope payout'},
    'T_TAKE':             {'unit': 'N',   'description': 'Take confirmation threshold'},
    'T_FALL':             {'unit': 'N',   'description': 'Fall detection tension'},
    'T_GROUND':           {'unit': 'N',   'description': 'Ground/idle threshold'},
}

# ── Firmware constant name patterns ───────────────────────────────────────────
# Maps constant names to regex patterns (capture group 1 = numeric value).
# Handles constexpr float, #define, and bare float styles.
_ALL_SYNC_NAMES = list(PYTHON_CONSTANTS) + CEM_CONSTANT_NAMES
FIRMWARE_PATTERNS = {
    name: [
        rf'constexpr\s+\w+\s+{name}\s*=\s*([\d.]+)',
        rf'#\s*define\s+{name}\s+([\d.]+)',
        rf'(?:static\s+)?const\s+\w+\s+{name}\s*=\s*([\d.]+)',
        rf'(?:^|\s)\w+\s+{name}\s*=\s*([\d.]+)',
    ]
    for name in _ALL_SYNC_NAMES
}
# PID struct member patterns (tensionPID.kp = ...)
FIRMWARE_PATTERNS['tensionPID_kp'] = [r'\.kp\s*=\s*([\d.]+)']
FIRMWARE_PATTERNS['tensionPID_ki'] = [r'\.ki\s*=\s*([\d.]+)']
FIRMWARE_PATTERNS['tensionPID_kd'] = [r'\.kd\s*=\s*([\d.]+)']
# ESP32 comms constant
FIRMWARE_PATTERNS['UART_BAUD'] = [r'#\s*define\s+UART_BAUD\s+([\d.]+)']

# Tolerance for float comparison (1% relative or 0.001 absolute)
REL_TOLERANCE = 0.01
ABS_TOLERANCE = 0.001


def load_cem_constants(from_cem: bool = False, cem_json_path: Path = None,
                       repo_root: Path = None) -> dict:
    """
    Load CEM-derived constants. Returns {name: {value, unit, description}}.
    When from_cem=True: run aria_cem.compute_aria + export_sync_constants.
    When cem_json_path: load from JSON file.
    """
    if cem_json_path and cem_json_path.exists():
        data = json.loads(cem_json_path.read_text())
        return {
            k: {'value': v, **CEM_CONSTANT_META.get(k, {'unit': '-', 'description': ''})}
            for k, v in data.items() if k in CEM_CONSTANT_NAMES
        }
    if from_cem:
        sys.path.insert(0, str(repo_root or Path('.')))
        from aria_cem import ARIAInputs, compute_aria, export_sync_constants
        inp = ARIAInputs()
        geom = compute_aria(inp)
        c = export_sync_constants(geom, inp)
        return {
            k: {'value': v, **CEM_CONSTANT_META.get(k, {'unit': '-', 'description': ''})}
            for k, v in c.items() if k in CEM_CONSTANT_NAMES
        }
    return {}


def get_sync_constants(from_cem: bool, cem_json_path: Path, repo_root: Path) -> dict:
    """
    Get constants to sync. CEM overrides for geometry; merge with PYTHON_CONSTANTS.
    """
    if from_cem or cem_json_path:
        cem = load_cem_constants(from_cem, cem_json_path, repo_root)
        # CEM values override. Add PYTHON_CONSTANTS for any not in CEM.
        merged = dict(PYTHON_CONSTANTS)
        for k, v in cem.items():
            merged[k] = v
        return merged
    return PYTHON_CONSTANTS


def find_firmware_files(repo_root: Path) -> list[Path]:
    """Find all .cpp and .h files under firmware/stm32/"""
    fw_dir = repo_root / 'firmware' / 'stm32'
    if not fw_dir.exists():
        return []
    files = list(fw_dir.rglob('*.cpp')) + list(fw_dir.rglob('*.h'))
    return sorted(files)

def find_esp32_files(repo_root: Path) -> list[Path]:
    """Find all .ino and .cpp/.h files under firmware/esp32/"""
    esp32_dir = repo_root / "firmware" / "esp32"
    if not esp32_dir.exists():
        return []
    files: list[Path] = []
    for ext in ("*.ino", "*.cpp", "*.h"):
        files.extend(list(esp32_dir.rglob(ext)))
    return sorted(files)


def _scan_text_for_constant(name: str, text: str) -> tuple[bool, float, int, str]:
    """Scan provided text for constant patterns. Returns (found, value, line_num, raw)."""
    patterns = FIRMWARE_PATTERNS.get(name, [])
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            try:
                val = float(match.group(1))
                line_num = text[:match.start()].count("\n") + 1
                return True, val, line_num, match.group(0).strip()
            except Exception:
                continue
    return False, 0.0, 0, ""


def scan_esp32_for_constant(name: str, esp_files: list[Path]) -> dict:
    """Scan ESP32 firmware for constant. Returns first match dict like scan_firmware_for_constant()."""
    for fpath in esp_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        found, val, line_num, raw = _scan_text_for_constant(name, text)
        if found:
            return {
                "found": True,
                "value": val,
                "file": str(fpath.relative_to(fpath.parent.parent.parent)),
                "line": line_num,
                "raw": raw,
            }
    return {"found": False}


def _patch_text_constant(old_raw: str, new_val: float, text: str) -> str:
    """Patch a single matched raw string by replacing its first numeric literal."""
    new_num = f"{new_val:.6f}".rstrip("0").rstrip(".")
    if "." not in new_num:
        new_num += ".0"
    new_raw = re.sub(r"(\s)([\d.]+)(f?)(\s*;?)", lambda m: m.group(1) + new_num + m.group(3) + m.group(4), old_raw, count=1)
    return text.replace(old_raw, new_raw, 1)


def _scan_stm32_uart_baud(fw_files: list[Path]) -> float | None:
    """Extract UART baud from STM32 sources (ESP32Serial.begin(BAUD,...))."""
    pat = re.compile(r"ESP32Serial\.begin\(\s*(\d+)", re.IGNORECASE)
    for fpath in fw_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        m = pat.search(text)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
    return None


def run_esp32_sync_check(repo_root: Path, stm32_fw_files: list[Path], patch: bool = False) -> dict:
    """
    Check ESP32 constants that must stay in sync with STM32.
    ESP32 follows STM32 for threshold values; comms are checked only.
    """
    esp_files = find_esp32_files(repo_root)
    out = {
        "esp32_files_found": len(esp_files),
        "esp32_files": [str(p.name) for p in esp_files],
        "ok": [],
        "drift": [],
        "not_found": [],
        "patches_applied": [],
        "shared_comms": [],
    }
    if not esp_files:
        return out

    # Thresholds: compare ESP32 vs STM32 values (fallback to expected if STM32 symbol not present)
    for name, expected in ESP32_SYNC_CONSTANTS.items():
        stm = scan_firmware_for_constant(name, stm32_fw_files)
        esp = scan_esp32_for_constant(name, esp_files)
        if not esp.get("found"):
            out["not_found"].append({"name": name, "where": "esp32"})
            continue
        stm_val = float(stm["value"]) if stm.get("found") else float(expected)
        esp_val = float(esp["value"])
        if values_match(stm_val, esp_val):
            out["ok"].append({"name": name, "value": stm_val})
        else:
            out["drift"].append({"name": name, "stm32": stm_val, "esp32": esp_val, "esp32_loc": f"{esp['file']}:{esp['line']}"})
            if patch and name not in NEVER_PATCH:
                # Patch ESP32 to match STM32 (threshold values only)
                esp_path = repo_root / esp["file"]
                try:
                    text = esp_path.read_text(encoding="utf-8", errors="ignore")
                    new_text = _patch_text_constant(esp["raw"], stm_val, text)
                    if new_text != text:
                        esp_path.write_text(new_text, encoding="utf-8")
                        out["patches_applied"].append(name)
                except Exception:
                    pass

    # Shared comms: checked only, never patched
    stm_baud = _scan_stm32_uart_baud(stm32_fw_files)
    for cname, expected in SHARED_COMMS.items():
        esp = scan_esp32_for_constant(cname, esp_files)
        out["shared_comms"].append({
            "name": cname,
            "expected": expected,
            "stm32": stm_baud,
            "esp32": esp.get("value") if esp.get("found") else None,
            "esp32_found": bool(esp.get("found")),
        })

    return out


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


def run_sync_check(repo_root: Path, constants: dict = None,
                   verbose: bool = False, patch: bool = False) -> dict:
    """
    Main sync check. Returns dict with:
      matches, mismatches, not_found_in_firmware, summary
    constants: {name: {value, unit, description}}. Defaults to PYTHON_CONSTANTS.
    """
    constants = constants or PYTHON_CONSTANTS
    fw_files = find_firmware_files(repo_root)

    results = {
        'timestamp':            datetime.now().isoformat(),
        'firmware_files_found': len(fw_files),
        'firmware_files':       [str(f.name) for f in fw_files],
        'matches':              [],
        'mismatches':           [],
        'not_found':            [],
        'patches_applied':      [],
        'design_decisions':     [],
    }

    if not fw_files:
        results['warning'] = (
            'No firmware files found under firmware/stm32/. '
            'Sync check skipped — Python model is the source of truth.'
        )
        return results

    for name, spec in constants.items():
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

            # Auto-patch if requested (skip never-patch constants)
            if patch and name not in NEVER_PATCH:
                patched = _patch_firmware_constant(
                    name, py_val, fw_match, fw_files, repo_root)
                if patched:
                    results['patches_applied'].append(name)

    # Design-decision constants: report firmware vs CEM, never patch
    for name, cem_val in DESIGN_DECISION_CEM.items():
        fw_match = scan_firmware_for_constant(name, fw_files)
        if fw_match['found']:
            results['design_decisions'].append({
                'name': name,
                'fw_value': fw_match['value'],
                'cem_value': cem_val,
            })

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
        src = results.get('constants_source', PYTHON_CONSTANTS)
        print('\nConstants (source of truth):')
        for name, spec in src.items():
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

    # Design decisions (never-patch; firmware vs CEM for reference)
    if results.get('design_decisions'):
        print(f"\n[DESIGN DECISION] (not auto-patched — requires engineering review)")
        for d in results['design_decisions']:
            print(f"  {d['name']}: firmware={d['fw_value']} CEM={d['cem_value']}")

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


def print_esp32_report(esp: dict) -> None:
    if not esp:
        return
    print("\n" + "=" * 60)
    print("ESP32 SYNC CHECK")
    print("=" * 60)
    print(f"ESP32 files scanned: {esp.get('esp32_files_found', 0)}")
    if esp.get("ok"):
        for r in esp["ok"]:
            print(f"[STM32 OK] {r['name']} = {r['value']}")
            print(f"[ESP32 OK] {r['name']} = {r['value']}  (in sync)")
    if esp.get("drift"):
        for d in esp["drift"]:
            print(f"[ESP32 DRIFT] {d['name']}: STM32={d['stm32']}, ESP32={d['esp32']}  ({d.get('esp32_loc','')})")
    if esp.get("not_found"):
        for n in esp["not_found"]:
            print(f"[ESP32 NOT FOUND] {n['name']} (missing in {n['where']})")
    if esp.get("shared_comms"):
        for c in esp["shared_comms"]:
            if c.get("esp32_found") and c.get("stm32") is not None:
                status = "OK" if float(c["esp32"]) == float(c["stm32"]) == float(c["expected"]) else "DRIFT"
                print(f"[COMMS {status}] {c['name']}: STM32={c['stm32']}, ESP32={c['esp32']} (expected {c['expected']})")
            else:
                print(f"[COMMS CHECK] {c['name']}: STM32={c.get('stm32')}, ESP32={'FOUND' if c.get('esp32_found') else 'MISSING'} (expected {c['expected']})")
    if esp.get("patches_applied"):
        print(f"[ESP32 PATCH] AUTO-PATCHED ({len(esp['patches_applied'])})")
        for name in esp["patches_applied"]:
            print(f"  {name}")


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
    parser.add_argument('--from-cem', action='store_true',
                        help='Use CEM (aria_cem) as source of truth for geometry constants')
    parser.add_argument('--cem-json', type=Path, default=None,
                        help='Load CEM constants from pre-generated JSON file')
    parser.add_argument('--esp32', action='store_true',
                        help='Also scan firmware/esp32 for shared constants')
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    constants = get_sync_constants(args.from_cem, args.cem_json, repo_root)

    try:
        results = run_sync_check(
            repo_root=repo_root,
            constants=constants,
            verbose=args.verbose,
            patch=args.patch,
        )
        results['constants_source'] = constants

        if args.esp32:
            fw_files = find_firmware_files(repo_root)
            results["esp32"] = run_esp32_sync_check(repo_root, fw_files, patch=args.patch)

        if args.json_out:
            save_report(results, args.json_out)

        exit_code = print_report(results, verbose=args.verbose)
        if args.esp32:
            print_esp32_report(results.get("esp32", {}))

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
