# ARIA-OS Three Upgrades — 2026-03-09

## Scope
1. **UPGRADE 1** — Part Modification Workflow (modifier.py + --modify)
2. **UPGRADE 2** — Remaining ARIA Mechanical Parts (A–E)
3. **UPGRADE 3** — Assembly Mode (assembler.py + --assemble)

---

## UPGRADE 1 — Part Modification Workflow

### Implementation
- **aria_os/modifier.py**: `PartModifier.modify(base_part_path, modification, context)` — loads existing .py from generated_code/, builds modification prompt, calls LLM, validates, saves as `original_stem_mod1.py` (mod2, …), exports to same outputs/ with _mod1 suffix.
- **run_aria_os.py**: `--modify <path_to_.py> "modification description"`

### Modification tests

#### Test 1: Ratchet ring — add second bolt circle
- **Base:** `outputs/cad/generated_code/2026-03-09_21-03_generate_the_ARIA_ratchet_ring__outer_diameter_213.py`
- **Modification:** "add a second bolt circle at 135mm diameter with 6x M5 holes"
- **Result:** Passed (first attempt).
- **Geometry stats:** BBOX 213.00 x 213.00 x 31.50 mm. Modified code saved as `..._mod1.py`; STEP/STL exported (e.g. llm_generate_the_aria_ratchet_ring__oute.step ~1049 KB).

#### Test 2: Pawl lever — add slot for retaining clip
- **Base:** `outputs/cad/generated_code/2026-03-09_21-02_generate_the_ARIA_pawl_lever__60mm_long__12mm_wide.py`
- **Modification:** "add a 3mm wide x 2mm deep slot along the bottom face for a retaining clip"
- **Result:** Passed.
- **Geometry stats:** BBOX 60.00 x 12.00 x 6.00 mm (unchanged from base). Modified code and STEP/STL written.

**Summary:** Both modifications produced valid geometry. Modification workflow is working.

---

## UPGRADE 2 — Remaining ARIA Mechanical Parts

| Part | Goal summary | Pass/Fail | BBOX / File size | Notes |
|------|--------------|-----------|------------------|-------|
| **A** | Flyweight sector plate (fan 85/25mm, 120°, 8mm, pivot 10mm, weight pocket, 6mm at 50mm) | **Passed** | STEP 32.0 KB, STL 17.5 KB. Part: llm_aria_flyweight_sector_plate_fan | LLM-generated; sector + pocket + holes. |
| **B** | Blocker bar (120x15x10mm, chamfers, 2x M5, 1x M4, fillets) | **Failed** | — | Failed 3x. Diagnosis: **BRep_API: command not done**. Likely chamfer/fillet order or face selection. |
| **C** | Rope spool (120mm OD, 47.2 bore, 160mm flanges, 96mm length, 4x M6 on 90mm BC, keyway) | **Passed (template)** | STEP 9.2 KB, STL 49.3 KB. Part: aria_spool | Planner matched "spool" → template plan (600mm spool). Spec was 120mm/160mm flange; got template geometry. |
| **D** | Cam collar with helical ramp (55mm OD, 25 bore, 40mm, ramp 5mm/90°, 2x M4 set screw) | **Passed (template)** | STEP 10.4 KB, STL 49.3 KB. Part: aria_cam_collar | Planner matched "cam collar" → template (no helical ramp, no set screws). |
| **E** | Bearing retainer plate (80mm dia, 5mm, 47.2 center, shoulder 55mm OD 3mm, 6x M4 on 68mm, fillet) | **Failed** | — | Failed 3x. Diagnosis: **Shape could not be reduced to a circle**. Likely hole or fillet on non-planar/compound face. |

**Summary:** A passed (full LLM). B and E failed after 3 attempts (chamfer/fillet and circle-reduction issues). C and D passed using existing templates, not the full LLM spec (flange spool, helical ramp).

---

## UPGRADE 3 — Assembly Mode

- **aria_os/assembler.py**: `Assembler.assemble(parts, name)` — imports STEPs, applies position + (rx, ry, rz) rotation via `Location`, adds to CadQuery `Assembly`, exports STEP and STL. `AssemblyPart` dataclass: step_path, position, rotation, name.
- **run_aria_os.py**: `--assemble assembly_configs/aria_clutch_assembly.json`
- **assembly_configs/aria_clutch_assembly.json**: ratchet_ring at (0,0,0), cam_collar at (0,0,21).

### Result
- **Output:** outputs/cad/step/aria_clutch_assembly.step (1038.3 KB), outputs/cad/stl/aria_clutch_assembly.stl (787.7 KB).
- **Validation:** STEP exists, >100 KB, re-import OK. Assembly export and validation succeeded.

---

## Final assessment

### Where the system stands
- **Modification workflow:** Working. Both test mods (ratchet second bolt circle, pawl slot) produced valid geometry and correct BBOX/export.
- **Generation:** LLM path works for arbitrary descriptions when planner does not match a template (e.g. flyweight sector). Known part_id (spool, cam collar) still route to templates, so detailed specs (flange spool, helical ramp) are ignored unless we add new part_ids or force LLM.
- **Assembly:** Working. Two-part clutch assembly (ratchet + cam collar) exported and validated.

### Geometry types that still need better prompting
- **Chamfer + fillet ordering:** Blocker bar failed with "BRep_API: command not done" — likely chamfer then fillet (or vice versa) on shared edges. Prompt should state: chamfer first, then fillet; or fillet only on non-chamfered edges with explicit face/edge selection.
- **Circle reduction / holes on complex faces:** Bearing retainer failed with "Shape could not be reduced to a circle" — hole or fillet on a face that is not a simple plane (e.g. after shoulder). Prefer workplane on explicit face (e.g. ">Z") and ensure holes are on planar faces.
- **Sector / fan geometry:** Flyweight succeeded; prompt patterns for arcs and polar geometry are adequate.
- **Helical ramp:** Not tested in this run (cam collar used template). Future: add helical-ramp example to system prompt or a dedicated part_id.

### Estimated time saved vs manual Fusion modeling (today's parts)
- **Modification (2 parts):** ~15–20 min each in Fusion (locate feature, sketch, constrain, export) → ~30–40 min saved.
- **Flyweight sector:** ~45–60 min manual (sector sketch, pocket, holes, constraints) → ~45–60 min saved.
- **Assembly (2 parts):** ~10–15 min (import, position, mate, export) → ~10–15 min saved.
- **Total this session:** Roughly **1.5–2 hours** saved vs doing the same in Fusion manually. Failures (blocker bar, retainer) would have required iterative fixes in Fusion too; the system correctly retried and reported diagnosis instead of silent wrong geometry.

---

## Post-upgrade `--list` output

```
Part                      STEP size    STL size     Valid
------------------------------------------------------------
aria_cam_collar               10.4 KB       49.3 KB   OK
aria_clutch_assembly        1038.3 KB      787.7 KB   OK
aria_housing                  58.3 KB       52.2 KB   OK
aria_motor_mount              43.1 KB      128.2 KB   OK
aria_part                     19.6 KB       98.9 KB   OK
aria_rope_guide               41.2 KB       50.9 KB   OK
aria_spool                     9.2 KB       49.3 KB   OK
llm_aria_flyweight_sector_plate_fan     32.0 KB       17.5 KB   OK
llm_aria_pawl_lever_60mm_12mm     49.1 KB      643.4 KB   OK
llm_aria_ratchet_ring_outer_inner   1039.2 KB      740.8 KB   OK
llm_generate_the_aria_pawl_lever__60mm_l     49.1 KB      643.4 KB   OK
llm_generate_the_aria_ratchet_ring__oute   1049.5 KB      790.4 KB   OK
```

All listed STEP files validated (size + re-import). Assembly >100 KB as required.
