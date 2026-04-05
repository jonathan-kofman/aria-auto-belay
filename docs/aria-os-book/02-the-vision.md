[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Why](./01-the-why.md) | [Next: The Map -->](./03-the-map.md)

---

# The Vision

## Product Vision

ARIA-OS becomes the default way hardware teams go from idea to machinable part. You describe what you need. The system generates it, validates it, quotes it, and pushes it to your CAD workspace and your manufacturer --- in under a minute.

The end state is not "AI writes CadQuery code." The end state is a pipeline where text input produces manufacturing-ready output with the same reliability as a human engineer, at 100x the speed and near-zero marginal cost.

---

## User Stories

### Hardware Startup Engineer

> "I need a motor mount for a NEMA 23 stepper. It should be 6061 aluminium, 8mm thick, with 4x M5 mounting holes on the NEMA 23 bolt pattern."

The engineer types this into the CLI or the Streamlit dashboard. ARIA-OS:
1. Recognizes `motor_mount` -> `flange` template
2. Extracts NEMA 23 bolt pattern dimensions from web research
3. Generates the STEP file in 3 seconds (template path)
4. Produces an engineering drawing, DFM report, and CNC setup sheet
5. Uploads to Onshape as a live parametric model
6. Returns a cost estimate for single-piece CNC machining

Total time: under 30 seconds. The engineer reviews the Onshape model, adjusts one dimension, and sends the drawing to the shop.

### Job Shop Estimator

> Customer sends a PDF drawing of a bracket. The estimator runs:
> `python run_aria_os.py --image bracket_drawing.jpg "it's a mounting bracket"`

ARIA-OS uses vision AI to extract a goal description from the image, generates the 3D model, runs machinability analysis, and produces a cost estimate with setup sheet. The estimator has a quote-ready package in 60 seconds instead of 30 minutes.

### Solo Builder (Hobbyist / Maker)

> "I want to 3D print a phone stand with a 75-degree viewing angle."

The builder has no CAD experience. ARIA-OS generates the STL, renders a preview, and the builder sends it straight to the slicer. If the angle is wrong, they say "make it 60 degrees" and get a new file.

---

## Success Metrics

| Metric | Current | 6-Month Target | 12-Month Target |
|---|---|---|---|
| Template coverage | 49 part types | 80 part types | 150 part types |
| First-attempt pass rate (template) | 100% | 100% | 100% |
| First-attempt pass rate (LLM) | ~60% | ~75% | ~85% |
| Pass rate after refinement (LLM) | ~80% | ~90% | ~95% |
| Avg generation time (template) | 2-8s | 2-5s | 1-3s |
| Avg generation time (full pipeline) | 30-90s | 20-60s | 10-30s |
| Onshape integration success | 90% | 98% | 99.5% |
| Visual verification coverage | Feature checklist | Per-dimension check | Tolerance-band check |
| Manufacturing output coverage | CAM + DFM + drawing | + nesting + toolpath sim | + G-code post |

---

## What It Will Look Like in 1 Year

**Template library:** 150+ part types covering structural, fastener, enclosure, drivetrain, and fluid system categories. Every common mechanical part has a template.

**Assembly generation:** Multi-part assemblies from a single description. "Design a 2-stage planetary gearbox, 5:1 ratio, NEMA 17 input" produces all gears, the housing, shafts, and bearing seats as an assembled STEP with Onshape mates.

**Cloud API:** A hosted REST endpoint where external tools (Slack bots, ERP systems, quoting platforms) submit text descriptions and receive STEP files, drawings, and cost estimates.

**Manufacturer integration:** Direct bridge to MillForge, Xometry, or Protolabs for instant quoting and ordering. The pipeline goes from text to purchase order.

**Visual verification v2:** Not just feature presence/absence, but dimensional verification from rendered views. The vision model measures the bore diameter in the image and compares it to the spec.

---

## What ARIA-OS Is Not

- **Not a parametric CAD replacement.** Onshape, Fusion, and SolidWorks are better for iterative design with history trees and constraints. ARIA-OS generates the first version; humans refine it.
- **Not a simulation tool.** The built-in FEA is a screening check (beam bending, hoop stress, bolt shear). Real FEA still requires Ansys, Abaqus, or SimScale.
- **Not a slicer.** It produces STL files but does not generate G-code for 3D printers. Use PrusaSlicer, Cura, or BambuStudio for that.

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: The Why](./01-the-why.md) | [Next: The Map -->](./03-the-map.md)
