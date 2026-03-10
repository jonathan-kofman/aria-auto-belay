from __future__ import annotations

from pathlib import Path
import shutil
import sys


def main() -> int:
    base = Path("outputs") / "cad" / "step"
    mapping = {
        "llm_aria_ratchet_ring.step": "llm_aria_ratchet_ring_outer_inner.step",
        "llm_aria_pawl_lever.step": "llm_aria_pawl_lever_60mm_12mm.step",
        "llm_aria_blocker_bar.step": "llm_aria_blocker_bar_tall_chamfer.step",
        "llm_aria_bearing_retainer.step": "llm_aria_bearing_retainer_plate_circular.step",
    }

    if not base.exists():
        print(f"MISSING_DIR {base}")
        return 2

    missing_sources: list[str] = []
    for dst_name, src_name in mapping.items():
        src = base / src_name
        dst = base / dst_name
        if not src.exists():
            missing_sources.append(str(src))
            continue
        if dst.exists():
            print(f"OK {dst.name} exists ({dst.stat().st_size} bytes)")
            continue
        shutil.copyfile(src, dst)
        print(f"COPIED {src.name} -> {dst.name} ({dst.stat().st_size} bytes)")

    if missing_sources:
        print("MISSING_SOURCES")
        for p in missing_sources:
            print(p)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

