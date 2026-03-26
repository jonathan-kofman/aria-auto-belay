# ARIA Known Failures & Fixes
# Read this FIRST before writing any Fusion 360 script.
# Agent: if you hit a new failure, append it here before retrying.

---

## FAILURE 001 — Interior Cut: No target body found
**Script:** aria_housing_complete.py (v1–v6)
**Error:** `3 : No target body found to cut or intersect!`
**Root cause:** Annular profile (outer rect minus inner rect) was being used to
extrude the hollow box in one shot. Fusion fails to find a target body for
subsequent cuts when the profile is non-simple.
**Fix:** Build a SOLID box first (simple rectangle profile → extrude). Then cut
the interior void as a SEPARATE boolean cut operation on the solid body.
Never use annular/donut profiles for the initial housing extrusion.
**Status:** Resolved in v7

---

## FAILURE 002 — Left Bore: No target body found
**Script:** aria_housing_complete.py (v1–v6)
**Error:** `3 : No target body found to cut or intersect!`
**Root cause:** Script was constructing sketch planes from scratch for the bore
rather than selecting an existing face of the housing body. When the body
reference was lost, sketch had nothing to cut into.
**Fix:** Always sketch bores on an EXISTING FACE of an existing body.
Use `body.faces` to find the correct face by normal direction, do not
construct planes independently.
**Manual workaround:** Sketch on front face → Ø47.2mm circle at (350, 330) →
Extrude Cut 12mm.
**Status:** Workaround documented; programmatic fix pending

---

## FAILURE 003 — RightShoulder: InternalValidationError
**Script:** aria_housing_complete.py (v1–v6)
**Error:** `2 : InternalValidationError : !extrudes.empty()`
**Root cause:** Attempting to join shoulder geometry to a body that had failed
operations upstream. Fusion's internal state was inconsistent.
**Fix:** Ensure all upstream operations succeed before attempting join operations.
Add explicit body existence checks before any JOIN operation.
**Status:** Workaround — build right shoulder manually if upstream state is uncertain

---

## FAILURE 004 — Parametric vs Direct Design mode conflict
**Script:** All housing scripts
**Root cause:** Scripts were running against a Parametric design, causing timeline
conflicts with programmatic operations.
**Fix:** Always force Direct Design mode at script start:
```python
if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
    des.designType = adsk.fusion.DesignTypes.DirectDesignType
```
**Status:** Resolved — included in all v5+ scripts

---

## FAILURE 005 — Multiple housing components stacking
**Symptom:** Running script multiple times adds new `ARIA_Housing` component
on top of old ones rather than replacing.
**Root cause:** Scripts always create a new component occurrence; they don't
check for or delete existing ones.
**Fix:** Before running any housing script, manually delete all existing
`ARIA_Housing` components in the browser (right-click → Delete).
Or add a pre-run cleanup loop that searches for and deletes existing components
by name before creating new ones.
**Status:** Manual workaround in place

---

## FAILURE 006 — Face reference lost after failed operation
**Symptom:** Feature that previously worked stops finding face after an upstream
failure is introduced.
**Root cause:** Fusion's face indices are not stable — they change when body
topology changes. Scripts that hardcode face indices (e.g., `faces[0]`) break
when upstream geometry changes.
**Fix:** Always select faces by their normal vector direction, not by index.
Example: find face with normal pointing in +Z direction for top face.
**Status:** Partially fixed — some scripts still use index-based selection

---

## PATTERN: Safe Fusion Script Template
```python
# 1. Force Direct Design
if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
    des.designType = adsk.fusion.DesignTypes.DirectDesignType

# 2. Create new component
occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
comp = occ.component

# 3. Build solid box FIRST (simple rectangle, no annular profiles)
# 4. Cut interior void as separate operation
# 5. All subsequent features: sketch on existing body faces
# 6. Wrap every operation in try/except, collect errors[], report at end
# 7. Never hardcode geometry — import from constants
```

---
## Template for logging new failures (append below):
## FAILURE XXX — [Short name]
## **Script:** 
## **Error:** 
## **Root cause:** 
## **Fix:** 
## **Status:** 

---
## FAILURE 099 — CEM static stress model: all catch parts fail SF < 2.0
**Script:** aria_models/static_tests.py + aria_os/cem_checks.py
**Error:** All 13 catch mechanism parts (pawl, lever, trip, blocker, ratchet ring, housing) show SF < 2.0 at 16 kN proof load in the closed-form static model.
**Root cause (2026-03):**
1. Meta JSON files in `outputs/cad/meta/` carry placeholder dims from early iterations, not final CEM-derived geometry.
2. The bending/shear model does NOT account for load sharing across engaged teeth or distributed contact along the pawl face — it assumes worst-case single-tooth / single-contact-point loading.
3. `aria_models/static_tests.py` yield constants (`YIELD_PAWL_MPA`, `YIELD_RATCHET_MPA`) were set conservatively; actual A2 tool steel heat-treated yield is ~1800 MPa not the ~1300 MPa default.
**Calibration path:**
- Run hardware drop tests at 1× / 2× / 4× ANSI proof load; record deflection and strain gauge data.
- Back-calculate actual SF from measured failure onset vs predicted.
- Update `aria_models/static_tests.py` load-sharing factor (`N_EFFECTIVE_TEETH`, contact distribution constants).
- Update yield constants to match actual material cert.
- Re-run `python aria_models/static_tests.py` and verify ≥ 2.0 SF across all load steps.
**Interim fix (2026-03):** `cem_checks._enrich_meta_with_cem()` pre-fills meta dims from CEM physics before static checks run, replacing placeholder values with CEM-correct geometry. This reduces false-fail rate but does not substitute for hardware calibration.
**Status:** Open — hardware testing required for final sign-off.
