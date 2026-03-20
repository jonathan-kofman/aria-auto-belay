from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .inputs import ARIAInputs


@dataclass
class ARIAModule:
    inputs: ARIAInputs
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def compute(self) -> Dict[str, Any]:
        from aria_models.dynamic_drop import simulate_drop_test

        _, summary = simulate_drop_test(
            mass_kg=self.inputs.mass_kg,
            drop_height_m=self.inputs.drop_height_m,
            rope_k=self.inputs.rope_k_n_per_m,
        )
        self.summary = dict(summary)
        self.warnings = []
        peak = float(summary.get("peak_force_N", 0.0))
        avg = float(summary.get("avg_force_N", 0.0))
        dist = float(summary.get("arrest_distance_mm", 0.0))
        if peak >= 0.9 * self.inputs.ansi_peak_n:
            self.warnings.append(f"Peak force near ANSI limit: {peak:.0f} N")
        if avg >= 0.9 * self.inputs.ansi_avg_n:
            self.warnings.append(f"Average force near ANSI limit: {avg:.0f} N")
        if dist >= 0.9 * self.inputs.ansi_dist_mm:
            self.warnings.append(f"Arrest distance near ANSI limit: {dist:.1f} mm")
        return self.summary

    def validate(self) -> bool:
        if not self.summary:
            self.compute()
        peak = float(self.summary.get("peak_force_N", 0.0))
        dist = float(self.summary.get("arrest_distance_mm", 0.0))
        return peak <= self.inputs.ansi_peak_n and dist <= self.inputs.ansi_dist_mm
