from dataclasses import dataclass


@dataclass
class ARIAInputs:
    mass_kg: float = 140.0
    drop_height_m: float = 0.040
    rope_k_n_per_m: float = 80000.0
    ansi_peak_n: float = 8000.0
    ansi_avg_n: float = 6000.0
    ansi_dist_mm: float = 813.0
