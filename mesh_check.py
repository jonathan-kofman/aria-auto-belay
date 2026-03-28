"""
mesh_check.py — Gear mesh validator.
Checks if gear pairs are compatible (matching module, correct center distance).

Usage:
    python mesh_check.py --gear1 "80t m1.0" --gear2 "8t m1.0" --center 44.0
    python mesh_check.py parts/clock_parts.json

For each pair:
- Checks modules match
- Calculates theoretical center distance = (N1 + N2) * module / 2
- Compares vs provided center distance (warns if >5% off)
- Calculates gear ratio
- Prints a table: Pair | Ratio | Theoretical CD | Actual CD | Status

When reading from a parts JSON:
  Detects gear pairs by pairing consecutive gear stages (wheel on arbor N meshes
  with pinion on arbor N+1). Wheels and pinions are identified by 'spoke_style'
  and naming conventions.
"""
import sys
import re
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Tolerance for center distance mismatch (5%)
CD_TOLERANCE = 0.05


# ── Gear descriptor parsing ────────────────────────────────────────────────────

def _parse_gear_desc(desc: str) -> dict:
    """
    Parse a short gear descriptor string like:
        "80t m1.0"     -> {n_teeth: 80, module_mm: 1.0}
        "p8 mod0.5"    -> {n_teeth: 8, module_mm: 0.5}
        "15t 1.5mod"   -> {n_teeth: 15, module_mm: 1.5}
    Returns dict with keys 'n_teeth' and 'module_mm'. Raises ValueError on bad input.
    """
    desc = desc.strip()

    # Extract tooth count — patterns: "80t", "p8", "8t", "t8"
    teeth_match = re.search(r'\b(?:p|t)?(\d+)t?\b', desc, re.IGNORECASE)
    if not teeth_match:
        raise ValueError(f"Cannot parse tooth count from: '{desc}'")
    n_teeth = int(teeth_match.group(1))

    # Extract module — patterns: "m1.0", "mod1.0", "1.0mod", "1.0m", "module=1.0"
    mod_match = re.search(
        r'(?:mod(?:ule)?[=\s]*|m)(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)(?:\s*mod(?:ule)?|m\b)',
        desc,
        re.IGNORECASE,
    )
    if not mod_match:
        raise ValueError(f"Cannot parse module from: '{desc}'")
    module_mm = float(mod_match.group(1) or mod_match.group(2))

    return {"n_teeth": n_teeth, "module_mm": module_mm}


# ── Center distance calculation ────────────────────────────────────────────────

def theoretical_cd(n1: int, n2: int, module: float) -> float:
    """Standard spur gear center distance: (N1+N2)*m/2."""
    return (n1 + n2) * module / 2.0


# ── Single pair check ──────────────────────────────────────────────────────────

def check_pair(
    label1: str,
    n1: int,
    m1: float,
    label2: str,
    n2: int,
    m2: float,
    actual_cd: float | None = None,
) -> dict:
    """
    Check a gear pair for module compatibility and center distance.
    Returns a result dict.
    """
    modules_match = abs(m1 - m2) < 1e-6
    ratio = n1 / n2 if n2 != 0 else float("inf")
    theo_cd = theoretical_cd(n1, n2, m1)  # use m1; if mismatch it's flagged separately

    cd_ok = None
    cd_error_pct = None
    if actual_cd is not None:
        cd_error_pct = abs(actual_cd - theo_cd) / theo_cd if theo_cd != 0 else 0.0
        cd_ok = cd_error_pct <= CD_TOLERANCE

    status_parts = []
    if not modules_match:
        status_parts.append(f"MODULE MISMATCH (m={m1} vs m={m2})")
    if cd_ok is False:
        status_parts.append(f"CD OFF {cd_error_pct*100:.1f}%")
    if not status_parts:
        status_parts.append("OK")

    return {
        "label1":       label1,
        "n1":           n1,
        "m1":           m1,
        "label2":       label2,
        "n2":           n2,
        "m2":           m2,
        "ratio":        ratio,
        "theo_cd":      theo_cd,
        "actual_cd":    actual_cd,
        "modules_match": modules_match,
        "cd_ok":        cd_ok,
        "status":       " | ".join(status_parts),
        "pass":         modules_match and (cd_ok is not False),
    }


# ── Parts JSON pair detection ──────────────────────────────────────────────────

def _is_gear(entry: dict) -> bool:
    """Return True if a parts-list entry looks like a gear."""
    pid = entry.get("part_id", "").lower()
    label = entry.get("label", "").lower()
    params = entry.get("params", {})
    if params.get("n_teeth"):
        return True
    if any(k in pid or k in label for k in ("wheel", "pinion", "cannon", "escape")):
        return True
    return False


def _is_pinion(entry: dict) -> bool:
    pid = entry.get("part_id", "").lower()
    label = entry.get("label", "").lower()
    return "pinion" in pid or "pinion" in label or "cannon" in pid


def _is_wheel(entry: dict) -> bool:
    pid = entry.get("part_id", "").lower()
    label = entry.get("label", "").lower()
    return ("wheel" in pid or "wheel" in label) and not _is_pinion(entry)


def _gear_params(entry: dict) -> tuple[int, float]:
    """Return (n_teeth, module_mm) from a parts-list entry."""
    params = entry.get("params", {})
    n = int(params.get("n_teeth", 0))
    m = float(params.get("module_mm", 1.0))
    return n, m


def detect_pairs_from_parts(parts: list[dict]) -> list[tuple[dict, dict]]:
    """
    Detect meshing pairs from a parts list.

    Pairing strategy:
      - Separate gears into wheels and pinions.
      - In a standard clock gear train the wheel on arbor N drives the pinion
        on arbor N+1. We pair them in natural list order: wheel[0]→pinion[0],
        wheel[1]→pinion[1], etc.
      - Any leftover wheels or pinions are reported unpaired.
    """
    gears = [p for p in parts if _is_gear(p)]
    wheels  = [g for g in gears if _is_wheel(g)]
    pinions = [g for g in gears if _is_pinion(g)]

    pairs = []
    for w, p in zip(wheels, pinions):
        pairs.append((w, p))

    # Any remaining unpaired gears
    unpaired = wheels[len(pinions):] + pinions[len(wheels):]
    if unpaired:
        names = [u.get("label", u.get("part_id", "?")) for u in unpaired]
        print(f"[mesh_check] Note: {len(unpaired)} unpaired gear(s): {', '.join(names)}")

    return pairs


# ── Table printing ─────────────────────────────────────────────────────────────

_COL_PAIR  = 42
_COL_RATIO =  7
_COL_THEO  = 14
_COL_ACT   = 10
_COL_STAT  = 24

def _print_header() -> None:
    print(f"\n{'Pair':{_COL_PAIR}}  {'Ratio':>{_COL_RATIO}}  {'Theo CD (mm)':{_COL_THEO}}  {'Actual CD':>{_COL_ACT}}  {'Status':{_COL_STAT}}")
    print("-" * (_COL_PAIR + _COL_RATIO + _COL_THEO + _COL_ACT + _COL_STAT + 10))


def _print_row(result: dict) -> None:
    pair_str = f"{result['label1']} ({result['n1']}t m{result['m1']}) ↔ {result['label2']} ({result['n2']}t m{result['m2']})"
    ratio_str = f"{result['ratio']:.3f}:1"
    theo_str  = f"{result['theo_cd']:.2f}"
    act_str   = f"{result['actual_cd']:.2f}" if result['actual_cd'] is not None else "—"
    status    = result["status"]

    # Truncate pair string if too long
    if len(pair_str) > _COL_PAIR:
        pair_str = pair_str[:_COL_PAIR - 1] + "…"

    print(f"{pair_str:{_COL_PAIR}}  {ratio_str:>{_COL_RATIO}}  {theo_str:{_COL_THEO}}  {act_str:>{_COL_ACT}}  {status:{_COL_STAT}}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gear mesh validator — checks module compatibility and center distances."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--gear1",
        metavar="DESC",
        help='First gear descriptor, e.g. "80t m1.0"',
    )
    group.add_argument(
        "parts_file",
        nargs="?",
        type=Path,
        default=None,
        help="Parts list JSON to auto-detect and validate all gear pairs",
    )
    parser.add_argument(
        "--gear2",
        metavar="DESC",
        default=None,
        help='Second gear descriptor, e.g. "8t m1.0"',
    )
    parser.add_argument(
        "--center",
        type=float,
        default=None,
        metavar="MM",
        help="Actual center distance in mm (optional; compared against theoretical)",
    )
    args = parser.parse_args()

    results: list[dict] = []

    if args.gear1:
        # Single pair mode
        if not args.gear2:
            parser.error("--gear2 is required when --gear1 is used")
        try:
            g1 = _parse_gear_desc(args.gear1)
            g2 = _parse_gear_desc(args.gear2)
        except ValueError as e:
            print(f"[mesh_check] Error: {e}")
            sys.exit(1)

        result = check_pair(
            label1=args.gear1,
            n1=g1["n_teeth"],
            m1=g1["module_mm"],
            label2=args.gear2,
            n2=g2["n_teeth"],
            m2=g2["module_mm"],
            actual_cd=args.center,
        )
        results.append(result)

    else:
        # Parts file mode
        parts_file = args.parts_file
        if not parts_file.is_absolute():
            parts_file = ROOT / parts_file
        if not parts_file.exists():
            print(f"[mesh_check] Error: file not found: {parts_file}")
            sys.exit(1)

        with open(parts_file, "r", encoding="utf-8") as fh:
            parts = json.load(fh)

        print(f"[mesh_check] Loaded {len(parts)} parts from {parts_file}")

        pairs = detect_pairs_from_parts(parts)
        if not pairs:
            print("[mesh_check] No gear pairs detected.")
            sys.exit(0)

        print(f"[mesh_check] Detected {len(pairs)} gear pair(s)")

        for wheel_entry, pinion_entry in pairs:
            n1, m1 = _gear_params(wheel_entry)
            n2, m2 = _gear_params(pinion_entry)
            if n1 == 0 or n2 == 0:
                print(f"[mesh_check] Skipping pair with missing tooth count: "
                      f"{wheel_entry.get('label')} / {pinion_entry.get('label')}")
                continue
            result = check_pair(
                label1=wheel_entry.get("label", wheel_entry.get("part_id", "?")),
                n1=n1,
                m1=m1,
                label2=pinion_entry.get("label", pinion_entry.get("part_id", "?")),
                n2=n2,
                m2=m2,
                actual_cd=None,   # parts list doesn't carry center-to-center data
            )
            results.append(result)

    # Print table
    _print_header()
    for r in results:
        _print_row(r)
    print()

    # Summary
    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed
    print(f"[mesh_check] {passed}/{len(results)} pair(s) OK"
          + (f", {failed} FAILED" if failed else ""))

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
