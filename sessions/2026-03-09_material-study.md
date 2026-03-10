# 2026-03-09 — Material Optimization Study System

## 1. Parser fix (aria_materials.md → Material objects)

- Replaced the old `load_materials` implementation in `aria_os/context_loader.py` (which used `parse_tables` and returned 0 rows) with a dedicated parser that:
  - Locates `context/aria_materials.md` on disk.
  - Finds the header row starting with `| id` that contains `yield_mpa`.
  - Parses that header into column names.
  - Iterates over subsequent `| ... |` lines, skipping the separator row and stopping at the first non-table line.
  - Instantiates `Material` objects (from `aria_os.material_study`) per row.
- Verification command:

```text
.venv\Scripts\python.exe -c "from aria_os.context_loader import load_context, load_materials; ctx=load_context(); mats=load_materials(ctx); print(len(mats), 'materials'); [print(f'{m.id}: {m.yield_mpa} MPa') for m in mats]"
```

Output:

```text
10 materials
6061_t6: 276.0 MPa
7075_t6: 503.0 MPa
4140_ht: 1000.0 MPa
4340_steel: 1470.0 MPa
17_4ph_h900: 1310.0 MPa
ti_6al_4v: 880.0 MPa
316l_ss: 290.0 MPa
4140_normalized: 655.0 MPa
6082_t6: 260.0 MPa
inconel_718: 1100.0 MPa
```

So the context material table is now parsed correctly into 10 candidate materials.

---

## 2. Individual material studies (catch mechanism parts)

### 2.1 Pawl lever — `--material-study "pawl_lever"`

- Part resolved to:
  - `2026-03-09_23-31_generate_the_ARIA_pawl_lever__60mm_long__12mm_wide_opt5`
  - Criticality: `safety_critical`, SF target = 2.0x.
- Top 3 ranked materials (all failing SF):

```text
Rank Material        SF   Weight  Rel Cost Mach Verdict
1    4340_steel      0.47   14 g   0.05    5.0  FAIL
2    17_4ph_h900     0.41   13 g   0.07    5.0  FAIL
3    4140_ht         0.32   14 g   0.04    6.0  FAIL
...  (all others ≤0.16x SF, all FAIL)
```

- Recommendation (before Windows Unicode error clipped the line):
  - **4340 Steel** is highest-scoring, but SF is only **0.47x**, far below the 2.0x target. The optimizer classifies it as `FAIL`.
- Design intent vs study:
  - Existing intent (from prior context) is “hardened steel” (similar to 4140/4340/17-4PH).
  - The study *ranks* those high but still reports all as SF<1; the stress model is currently too conservative for this geometry and loading to reach real SF≥2 under any candidate material.

### 2.2 Ratchet ring — `--material-study "ratchet_ring"`

- Part: `generate the ARIA ratchet ring: outer diameter 213mm, ...`
- Criticality: `safety_critical`.
- Top 3:

```text
Rank Material        SF   Weight  Rel Cost Mach Verdict
1    4340_steel      0.64   7578 g  30.31   5.0  FAIL
2    17_4ph_h900     0.57   7510 g  37.55   5.0  FAIL
3    4140_ht         0.44   7578 g  22.73   6.0  FAIL
...  (6061-T6 SF≈0.12x; all FAIL)
```

- Again, the “best” materials are **high-strength steels** (4340, 17-4PH, 4140_HT), matching design intuition, but SF is still < 1 according to the current static model.

### 2.3 Blocker bar — `--material-study "blocker_bar"`

- Criticality: `non_critical`.
- Top 3:

```text
Rank Material        SF   Weight  Rel Cost Mach Verdict
1    6061_t6         0.04   29 g   0.03   10.0 FAIL
2    6082_t6         0.04   29 g   0.04    9.0 FAIL
3    7075_t6         0.08   30 g   0.08    7.0 FAIL
...  (high-strength steels reach SF≈0.23x but heavier, still FAIL)
```

- The study unsurprisingly prefers aluminum grades (6061/6082/7075) on weight/cost/machinability, but all SF values are far below target.

### 2.4 Trip lever — `--material-study "trip_lever"`

- Criticality: `non_critical`.
- Top 3:

```text
Rank Material        SF   Weight  Rel Cost Mach Verdict
1    6061_t6         0.01   10 g  0.01   10.0 FAIL
2    6082_t6         0.01   10 g  0.01    9.0 FAIL
3    7075_t6         0.01   11 g  0.03    7.0 FAIL
...  (steels/Inconel slightly higher SF≈0.02–0.03x but much heavier/costlier)
```

- Again, no material achieves SF ≥ 2.0 given the current cross-section assumption in the static model.

### 2.5 Bearing retainer — `--material-study "bearing_retainer"`

- This part does not have a clean meta/part mapping in the current run (and the earlier SF results already showed broadly low SFs for all parts). A robust study here will require better static model calibration for plate-type parts and/or regenerating bearing retainer with meta JSON that maps meaningfully into `simulate_static_pawl`.

---

## 3. `--material-study-all` summary

- Command:

```text
.venv\Scripts\python.exe run_aria_os.py --material-study-all
```

- Output (summarized; note some cp1252 truncation of Unicode in the console, but structure is clear):

```text
Running material studies on all parts...

                        ARIA Material Study - All Parts
+------------------------------------------------------------------------------+
| Part                            | Criticality | Recommended  | SF | Current | Action |
|---------------------------------+-------------+------------- +----+---------+--------|
| 2026-03-09_23-31_generate_the_… | safety_... | 4340 Steel   | ~? | 4140_ht | CHANGE |
| generate the ARIA blocker bar:  | non_crit.. | 6061-T6 Al   | ~? | 4140_ht | CHANGE |
| generate ARIA flyweight sector  | non_crit.. | 6061-T6 Al   | ~? | 6061_t6 | OK     |
| generate the ARIA pawl lever:   | safety_... | 4340 Steel   | ~? | 4140_ht | CHANGE |
| generate the ARIA ratchet ring: | safety_... | 4340 Steel   | ~? | 4140_ht | CHANGE |
| generate ARIA trip lever:       | non_crit.. | 6061-T6 Al   | ~? | 4140_ht | CHANGE |
| generate a high-complexity ARIA | non_crit.. | 6061-T6 Al   | ~? | 6061_t6 | OK     |
+------------------------------------------------------------------------------+

Full results saved to:
outputs/material_studies/2026-03-10_material_study_all.json
```

Notes:

- The console mangled some characters (e.g. “≈” in the reasoning and part-name truncation), but:
  - The **Action** column is correct:
    - `CHANGE` for pawl lever, ratchet ring, blocker bar, trip lever (recommended material differs from baseline spec).
    - `OK` for flyweight sector plate and high-complexity flyweight shoe (recommended matches baseline 6061-T6).
- The JSON file contains full per-material SF/weight/verdict data and is suitable for downstream analysis.

---

## 4. Does the system independently recommend hardened steel for pawl and ratchet?

- For **pawl lever** and **ratchet ring**:
  - The top-ranked materials in both cases are **high-strength steels**:
    - `4340_steel` and `17_4ph_h900` beat aluminums and stainless on SF and overall score.
  - The baseline mapping `_baseline_material_for_part` currently sets:
    - Baseline = `4140_ht` for catch-like parts.
  - The study recommends changing from 4140 HT to 4340 or 17-4PH for both pawl and ratchet.
- So:
  - The system **does** independently surface **hardened steels** (4340/17-4PH) as the best candidates for pawl and ratchet, consistent with the earlier design intent that these should be high-strength steels.
  - However, the **absolute SF values remain < 1** for all choices under the current closed-form model; the relative ranking is sensible, but absolute margins are not yet cert-grade.

---

## 5. Are SF values physically meaningful?

- At present:
  - All catch-mechanism parts (pawl lever, ratchet ring, blocker bar, trip lever) show SF well below 1.0 for every candidate material, which is not realistic for a viable design space.
  - This suggests the **stress model is overly conservative or mis-calibrated** (e.g., using too-small effective section widths/heights, double-counting loads, or applying full proof loads to simplified sections).
  - The material sweep (`yield_mpa` changes) scales SF in the expected direction, but the baseline SF from `simulate_static_pawl` is too low to reach SF≥2.0 for any material.
- So:
  - **Relative trends** (4340 > 17-4PH > 4140 > aluminum) are plausible.
  - **Absolute SF values** are not yet trustworthy for design-signoff; they should be treated as a coarse signal only.

What would make this more accurate:

- Upgrade from purely closed-form to:
  - **Better cross-section modeling**: use actual dims_mm (thickness, width, fillet radii) to compute section modulus and contact area more realistically instead of generic defaults.
  - **Calibration against FEA or test data**:
    - Run a small set of parts (pawl lever, ratchet ring) through FEA or instrumented physical tests.
    - Adjust load paths, support conditions, and effective contact areas so that model SF≈2.0 for a known “good” design in the intended material.
  - Potentially add a **finite-element or beam-based sub-model** for slender parts (blocker bar, trip lever) where current point-load approximations are too harsh.

---

## 6. Summary

- **Parser**: `aria_materials.md` is now correctly parsed into 10 candidate materials and is used across the study.
- **Individual studies**: For pawl, ratchet, blocker bar, and trip lever, the system ranks hardened steels and high-strength aluminums as expected, but all SF values remain < 1.0, so no material passes the SF≥2.0 target yet.
- **`--material-study-all`**:
  - Produces a summary showing where the recommended material differs from baseline and writes a detailed JSON report under `outputs/material_studies/`.
  - The system generally prefers **4340/17-4PH** for safety-critical catch components and **6061/6082** for non-critical and flyweight-like parts.
- **Engineering signal**:
  - The material study system is already useful for **relative ranking** and for surfacing candidate alloys consistent with ARIA’s design intent.
  - It is **not yet sufficient** as a stand-alone authority on SF margins; the underlying static model needs calibration and possibly more detailed geometry-to-stress mapping to yield realistic absolute SF values. 

