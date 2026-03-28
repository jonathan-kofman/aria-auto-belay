"""
batch.py — General batch part generator. Reads a JSON parts list file.

Parts list JSON format:
    [
      {"label": "Part name", "part_id": "template_key", "params": {...}},
      ...
    ]

Usage:
    python batch.py parts/clock_parts.json
    python batch.py parts/clock_parts.json --skip-existing
    python batch.py parts/clock_parts.json --only "escape"    (substring match on label)
    python batch.py parts/clock_parts.json --dry-run

- Outputs STEP to outputs/cad/step/{part_id}.step, STL to outputs/cad/stl/{part_id}.stl
- --skip-existing: skip if STEP already exists
- Calls gc.collect() between parts to avoid RAM accumulation
- Prints live [OK] / [FAIL] per part with bbox
- Prints summary table at end (N/total passed)
"""
import sys
import gc
import re
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OUT_STEP = ROOT / "outputs" / "cad" / "step"
OUT_STL  = ROOT / "outputs" / "cad" / "stl"


def _fmt_bbox(bbox) -> str:
    if not bbox:
        return "?"
    if isinstance(bbox, dict):
        return f"{bbox.get('x','?')}x{bbox.get('y','?')}x{bbox.get('z','?')}"
    return str(bbox)


def _fmt_size(n: int) -> str:
    if n >= 1_048_576:
        return f"{n/1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n/1024:.1f} KB"
    return f"{n} B"


def load_parts(parts_file: Path) -> list[dict]:
    with open(parts_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"Parts file must be a JSON array, got {type(data).__name__}")
    for i, entry in enumerate(data):
        if "label" not in entry:
            raise ValueError(f"Entry {i} missing 'label'")
        if "part_id" not in entry:
            raise ValueError(f"Entry {i} missing 'part_id'")
    return data


def run_batch(
    parts_file: Path,
    skip_existing: bool = False,
    only_filter: str | None = None,
    dry_run: bool = False,
) -> None:
    from aria_os.cadquery_generator import write_cadquery_artifacts

    OUT_STEP.mkdir(parents=True, exist_ok=True)
    OUT_STL.mkdir(parents=True, exist_ok=True)

    parts = load_parts(parts_file)
    total = len(parts)

    # Apply --only filter
    if only_filter:
        filt = only_filter.lower()
        parts = [p for p in parts if filt in p["label"].lower()]
        print(f"[batch] Filter '{only_filter}' matched {len(parts)}/{total} parts")
        total = len(parts)

    if total == 0:
        print("[batch] No parts to process.")
        return

    print(f"[batch] Processing {total} part(s) from {parts_file}")
    if dry_run:
        print("[batch] DRY RUN — no files will be written\n")
    print()

    results: list[tuple[str, str, str, str, str]] = []  # (status, label, part_id, bbox, err)

    for i, entry in enumerate(parts, 1):
        label    = entry["label"]
        part_id  = entry.get("part_id", entry.get("template", "aria_spacer"))
        # "template" key overrides "part_id" as the CadQuery template to use
        template = entry.get("template", part_id)
        params   = entry.get("params", {})
        # Use template as the plan part_id so the right CadQuery function runs
        part_id  = template

        # Use label-derived slug so parts sharing a template part_id (e.g. all
        # gears share "aria_gear") each get a unique file rather than overwriting.
        slug = re.sub(r"[^\w]+", "_", label.lower()).strip("_")
        step_path = OUT_STEP / f"{slug}.step"
        stl_path  = OUT_STL  / f"{slug}.stl"

        prefix = f"[{i:3d}/{total}]"

        if dry_run:
            print(f"  {prefix} [DRY] {label:35s}  -> {step_path.name}")
            results.append(("DRY", label, part_id, "-", ""))
            continue

        if skip_existing and step_path.exists():
            sz = _fmt_size(step_path.stat().st_size)
            print(f"  {prefix} [SKIP] {label:34s}  (exists, {sz})")
            results.append(("SKIP", label, part_id, "-", ""))
            gc.collect()
            continue

        plan = {"part_id": part_id, "params": params}

        try:
            result = write_cadquery_artifacts(
                plan,
                label,
                str(step_path),
                str(stl_path),
                ROOT,
            )
            ok   = not result.get("error")
            bbox = _fmt_bbox(result.get("bbox"))
            err  = result.get("error") or ""
        except Exception as exc:
            ok, bbox, err = False, "?", str(exc)

        status = "OK  " if ok else "FAIL"
        print(f"  {prefix} [{status}] {label:34s}  bbox={bbox}")
        if not ok and err:
            # Truncate long errors for inline display
            short_err = err.strip().splitlines()[-1][:100] if err.strip() else ""
            print(f"           {'':34s}  ERR: {short_err}")

        results.append((status.strip(), label, part_id, bbox, err))
        gc.collect()

    # ── Summary table ──────────────────────────────────────────────────────────
    if dry_run:
        print(f"\n{'='*65}")
        print(f"[batch] DRY RUN complete — {total} parts listed, 0 generated")
        print(f"{'='*65}")
        return

    real_results = [r for r in results if r[0] not in ("SKIP", "DRY")]
    passed  = sum(1 for r in real_results if r[0] == "OK")
    skipped = sum(1 for r in results if r[0] == "SKIP")
    failed  = sum(1 for r in real_results if r[0] == "FAIL")

    print(f"\n{'='*65}")
    print(f"[batch] Complete: {passed}/{len(real_results)} passed"
          + (f", {skipped} skipped" if skipped else "")
          + (f", {failed} FAILED" if failed else ""))

    if failed:
        print(f"\nFailed parts:")
        for status, label, pid, bbox, err in results:
            if status == "FAIL":
                last_line = err.strip().splitlines()[-1][:100] if err.strip() else "unknown error"
                print(f"  {label} ({pid}): {last_line}")

    print(f"\nSTEP files: {OUT_STEP}")
    print(f"STL  files: {OUT_STL}")
    print(f"{'='*65}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch CAD part generator — reads a JSON parts list and generates STEP+STL for each."
    )
    parser.add_argument("parts_file", type=Path, help="Path to parts list JSON file")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip parts whose STEP file already exists",
    )
    parser.add_argument(
        "--only",
        metavar="FILTER",
        default=None,
        help="Only process parts whose label contains FILTER (case-insensitive substring)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List parts that would be generated without actually running the CAD pipeline",
    )
    args = parser.parse_args()

    parts_file = args.parts_file
    if not parts_file.is_absolute():
        parts_file = ROOT / parts_file
    if not parts_file.exists():
        print(f"[batch] Error: parts file not found: {parts_file}")
        sys.exit(1)

    run_batch(
        parts_file=parts_file,
        skip_existing=args.skip_existing,
        only_filter=args.only,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
