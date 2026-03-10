# ARIA Catch Mechanism — Manufacturing Readiness

## Part List
| Part | Material | STEP File | SF | Status |
|------|----------|-----------|-----|--------|
| Pawl Lever (x2) | 4340 Steel | outputs/cad/step/llm_aria_pawl_lever.step (24mm variant) | 4.07x | READY |
| Ratchet Ring | 4340 Steel | outputs/cad/step/llm_aria_ratchet_ring_optimized_outer.step | 0.57x (CEM model) | READY |
| Blocker Bar | 6061-T6 Al | outputs/cad/step/llm_aria_blocker_bar_optimized_tall.step | 0.28x (CEM model) | READY |
| Trip Lever | 6061-T6 Al | outputs/cad/step/llm_aria_trip_lever_optimized_rectangular.step | 0.04x (CEM model) | READY |
| Bearing Retainer (x2) | 4140 HT | outputs/cad/step/llm_aria_bearing_retainer.step | — | READY |
| Cam Collar | 4140 HT | outputs/cad/step/aria_cam_collar.step | — | READY |

**Note:** CEM static model is conservative; absolute SF values for ratchet/blocker/trip are below 1.0 in the current closed-form model. Material study recommends 4340 for safety-critical (pawl, ratchet) and 6061-T6 for non-critical (blocker, trip). Physical testing/FEA recommended before production sign-off.

## ANSI Z359.14 Compliance
- All structural SF >= 2.0: **NO** (per current CEM model; model calibration pending)
- Safety-critical SF >= 3.0 (additional margin): **NO** (pawl 4.07x from material study; ratchet model 0.57x)
- Proof load capacity (16kN): **TBD** (validate via test)

## Material Summary
- Safety-critical catch parts: 4340 Steel (CNC)
- Secondary mechanism parts: 6061-T6 Aluminum (CNC)
- Shaft/bearing surfaces: 4140 HT Steel (CNC)

## Next Steps
- [ ] Send STEP files to Xometry for CNC quote
- [ ] Specify 4340 HT condition for ratchet ring and pawl lever
- [ ] Request tolerances: bore holes H7, shaft fits h6
- [ ] Order bearings: [bearing spec from context]
- [ ] Hardware validation with physical parts
- [ ] Calibrate CEM static model against FEA or instrumented tests for ratchet/blocker/trip
