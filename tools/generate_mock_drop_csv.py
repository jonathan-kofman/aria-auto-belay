#!/usr/bin/env python3
"""
Generate mock drop-test CSVs for ARIA (no hardware).
Use for: Drop Test Parser tab, Test Data pipeline, or CLI:
  python tools/aria_drop_parser.py dataset/sample_drop_tests/mock_drop_pass.csv

Writes to dataset/sample_drop_tests/ (created if missing).
"""

import numpy as np
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dataset" / "sample_drop_tests"
RNG = np.random.default_rng(42)


def make_drop_curve(dt_s=0.001, duration_s=1.5, peak_N=4200, baseline_N=2, seed=42):
    """Realistic arrest shape: baseline -> ramp -> peak -> decay + oscillation."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, duration_s, dt_s)
    n = len(t)
    tension = np.zeros(n)
    rope_pos = np.zeros(n)
    for i, ti in enumerate(t):
        if ti < 0.20:
            tension[i] = rng.normal(baseline_N, 0.5)
            rope_pos[i] = ti * 1.5
        elif ti < 0.25:
            frac = (ti - 0.20) / 0.05
            tension[i] = max(0, peak_N * np.sin(np.pi * frac) + rng.normal(0, 50))
            rope_pos[i] = rope_pos[i - 1] + 0.001
        else:
            decay = np.exp(-(ti - 0.25) / 0.3)
            tension[i] = 40 + 200 * decay * np.cos(2 * np.pi * 8 * (ti - 0.25)) + rng.normal(0, 5)
            rope_pos[i] = rope_pos[i - 1]
    return t, tension, rope_pos


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Pass case (peak ~4.2 kN < 6 kN)
    t, tension, rope_pos = make_drop_curve(peak_N=4200, seed=42)
    df_pass = pd.DataFrame({"time_s": t, "tension_N": tension, "rope_pos_m": rope_pos})
    path_pass = OUTPUT_DIR / "mock_drop_pass.csv"
    df_pass.to_csv(path_pass, index=False)
    print(f"Wrote {path_pass} ({len(df_pass)} rows)")

    # 2. Fail case (peak ~6.5 kN > 6 kN) for testing ANSI fail path
    t2, tension2, rope_pos2 = make_drop_curve(peak_N=6500, seed=99)
    df_fail = pd.DataFrame({"time_s": t2, "tension_N": tension2, "rope_pos_m": rope_pos2})
    path_fail = OUTPUT_DIR / "mock_drop_fail_peak.csv"
    df_fail.to_csv(path_fail, index=False)
    print(f"Wrote {path_fail} ({len(df_fail)} rows)")

    print(f"\nUse in dashboard: Drop Test Parser -> Upload one of these files.")
    print(f"Or CLI: python tools/aria_drop_parser.py {path_pass}")


if __name__ == "__main__":
    main()
