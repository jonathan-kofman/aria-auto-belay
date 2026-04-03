# Appendix

## Quick Reference

### All CLI Commands

#### Part Generation

```bash
# Generate a single part
python run_aria_os.py "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"

# Full pipeline: generate + FEA + drawing + render + CAM + setup sheet
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
python run_aria_os.py --full "ARIA ratchet ring" --machine "HAAS VF2"

# Generate from a photo
python run_aria_os.py --image photo.jpg
python run_aria_os.py --image photo.jpg "it's a bracket"

# 3D preview before export
python run_aria_os.py --preview "ARIA ratchet ring, 213mm OD"

# Modify an existing part
python run_aria_os.py --modify outputs/cad/generated_code/aria_spool.py "add 6x M6 bolt circle at 90mm radius"

# Render PNG preview
python run_aria_os.py "part goal" --render
```

#### Listing and Validation

```bash
python run_aria_os.py --list                   # list all parts with status
python run_aria_os.py --validate               # re-validate all STEP files
```

#### CEM Physics

```bash
python run_aria_os.py --cem-full                                    # physics check all parts
python run_aria_os.py --material-study aria_ratchet_ring            # material study
python run_aria_os.py --material-study-all                          # all parts
python run_aria_os.py --optimize aria_spool --goal minimize_weight --constraint "SF>=2.0"
python run_aria_os.py --optimize-and-regenerate aria_spool --goal minimize_weight --material 6061_al
```

#### FEA and CFD

```bash
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step --fea
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step --cfd
python run_aria_os.py --analyze-part outputs/cad/step/aria_spool.step --auto
```

#### Drawings and CAM

```bash
python run_aria_os.py --draw outputs/cad/step/aria_spool.step
python run_aria_os.py --cam outputs/cad/step/aria_housing.step --material aluminium_6061
python run_aria_os.py --cam-validate outputs/cad/step/aria_housing.step
python run_aria_os.py --setup outputs/cad/step/aria_housing.step outputs/cam/aria_housing/aria_housing_cam.py
```

#### Batch and Assembly

```bash
python batch.py parts/clock_parts.json
python batch.py parts/clock_parts.json --skip-existing --render --workers 4
python batch.py parts/clock_parts.json --verify-mesh

python assemble.py assembly_configs/aria_clutch_assembly.json
python assemble.py assembly_configs/aria_clutch_assembly.json --no-clearance
python assemble_constrain.py assembly_configs/clock_gear_train.json --proximity 80
```

#### Civil Engineering DXF

```bash
python run_aria_os.py --autocad "drainage plan" --state TX --discipline drainage
python run_aria_os.py --autocad "road plan for subdivision" --state CO
python run_aria_os.py --autocad "storm sewer layout" --state FL --out outputs/cad/dxf/project1/
```

#### ECAD PCB Generation

```bash
python run_aria_os.py --ecad "ARIA ESP32 board, 80x60mm, 12V, UART, BLE, HX711"
python run_aria_os.py --ecad-variants "ARIA ESP32 board" --variants variants/aria_board_variants.json
```

#### Lattice Generation

```bash
python run_aria_os.py --lattice --pattern honeycomb --form volumetric --width 100 --height 100 --depth 10
python run_aria_os.py --lattice-test
```

#### System-Level Generation

```bash
python run_aria_os.py --scenario "a climber takes a lead fall on a 15m route"
python run_aria_os.py --scenario-dry-run "..."
python run_aria_os.py --system "design a desktop CNC router 300x300x100mm"
python run_aria_os.py --system-dry-run "design a 6-DOF robot arm, 1kg payload"
```

#### Print Scaling

```bash
python run_aria_os.py --print-scale aria_ratchet_ring --scale 0.75
```

### Template Function List (39 unique templates)

| Function | Part Type | Key Params |
|----------|-----------|------------|
| `_cq_ratchet_ring` | Ratchet ring | od_mm, bore_mm, thickness_mm, n_teeth |
| `_cq_housing` | Housing / enclosure | width_mm, height_mm, depth_mm, wall_mm |
| `_cq_hollow_rect` | Hollow rectangular section | width_mm, height_mm, length_mm, wall_mm |
| `_cq_spool` | Rope/cable spool | od_mm, bore_mm, height_mm |
| `_cq_cam_collar` | Tapered cam collar | od_mm, bore_mm, height_mm |
| `_cq_brake_drum` | Brake drum | od_mm, height_mm, wall_mm, bore_mm |
| `_cq_catch_pawl` | Catch pawl / flat bar | length_mm, width_mm, thickness_mm, bore_mm |
| `_cq_rope_guide` | Roller guide bracket | width_mm, height_mm, thickness_mm, diameter_mm |
| `_cq_phone_case` | Phone / device case | width_mm, height_mm, depth_mm, wall_mm |
| `_cq_flat_plate` | Flat plate / panel | width_mm, height_mm, thickness_mm, n_bolts |
| `_cq_bracket` | Mounting bracket | width_mm, height_mm, thickness_mm, n_bolts, bolt_dia_mm |
| `_cq_l_bracket` | L-shaped bracket | width_mm, height_mm, thickness_mm, leg_height_mm |
| `_cq_heat_sink` | Finned heat sink | width_mm, height_mm, n_fins, fin_height_mm |
| `_cq_phone_stand` | Phone / tablet stand | width_mm, height_mm, angle_deg |
| `_cq_flange` | Bolt-circle flange | od_mm, bore_mm, thickness_mm, n_bolts |
| `_cq_shaft` | Solid shaft / rod | diameter_mm, length_mm |
| `_cq_pulley` | V-groove pulley | od_mm, bore_mm, width_mm |
| `_cq_cam` | Eccentric cam | od_mm, bore_mm, thickness_mm |
| `_cq_pin` | Dowel pin | diameter_mm, length_mm |
| `_cq_spacer` | Disc / washer / spacer | od_mm, bore_mm, thickness_mm |
| `_cq_tube` | Round tube / pipe | od_mm, bore_mm, length_mm |
| `_cq_gear` | Spur gear | module_mm, n_teeth, thickness_mm, bore_mm |
| `_cq_nozzle` | Convergent-divergent nozzle | entry_r_mm, throat_r_mm, exit_r_mm, length_mm, wall_mm |
| `_cq_escape_wheel` | Escapement wheel | od_mm, n_teeth, thickness_mm |
| `_cq_nema_motor` | NEMA stepper motor model | nema_size (17/23/34) |
| `_cq_mgn_rail` | MGN linear rail | mgn_size (12/15/25), length_mm |
| `_cq_ball_bearing` | Ball bearing model | od_mm, bore_mm, width_mm |
| `_cq_shaft_coupling` | Rigid shaft coupling | bore_1_mm, bore_2_mm, od_mm, length_mm |
| `_cq_profile_extrusion` | Aluminum extrusion (2020/4040) | profile_size, length_mm |
| `_cq_snap_hook` | Snap-fit hook / clip | length_mm, width_mm, thickness_mm |
| `_cq_thread_insert` | Heat-set threaded insert | od_mm, bore_mm, length_mm |
| `_cq_hinge` | Door / butt hinge | width_mm, height_mm, thickness_mm |
| `_cq_clamp` | Pipe / cable clamp | bore_mm, width_mm, thickness_mm |
| `_cq_handle` | Handle / grip / knob | length_mm, diameter_mm |
| `_cq_enclosure_lid` | Snap-fit enclosure lid | width_mm, height_mm, thickness_mm |
| `_cq_gusset` | Corner brace / gusset | width_mm, height_mm, thickness_mm |
| `_cq_spoked_wheel` | Spoked wheel / handwheel | od_mm, bore_mm, n_spokes |
| `_cq_t_slot_plate` | T-slot fixture plate | width_mm, height_mm, thickness_mm |
| `_cq_spring_clip` | Retaining clip / circlip | od_mm, bore_mm, thickness_mm |

### Output Paths

| Path | Contents |
|------|----------|
| `outputs/cad/step/` | STEP files |
| `outputs/cad/stl/` | STL mesh files |
| `outputs/cad/meta/` | Version metadata JSON (git SHA, CEM SF, params) |
| `outputs/cad/generated_code/` | Raw CadQuery scripts |
| `outputs/cad/grasshopper/<part>/` | Grasshopper artifacts |
| `outputs/cad/dxf/` | Civil DXF + JSON sidecar |
| `outputs/cam/<part>/` | CAM scripts + setup sheets + machinability JSON |
| `outputs/drawings/` | GD&T SVG drawings |
| `outputs/ecad/<board>/` | KiCad scripts + BOM + validation |
| `outputs/screenshots/` | PNG renders |
| `outputs/aria_generation_log.json` | GH pipeline run log |
| `cem_design_history.json` | CEM parameter snapshots |
| `contracts/` | JSON Schema files for output validation |
| `sessions/` | Agent session logs |

### Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | No | -- | Primary LLM backend |
| `GOOGLE_API_KEY` | No | -- | Gemini fallback LLM + vision |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model override |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL` | No | `deepseek-coder` | Local model name |
| `ONSHAPE_ACCESS_KEY` | No | -- | Onshape API key |
| `ONSHAPE_SECRET_KEY` | No | -- | Onshape API secret |
| `ARIA_PROFILE` | No | `dev` | Feature flag profile (dev/demo/production) |

### CAM Materials Database

| Material Key | SFM | Typical Use |
|-------------|-----|-------------|
| `aluminium_6061` | 300 | General purpose aluminum |
| `aluminium_7075` | 260 | High-strength aluminum |
| `steel_4140` | 90 | Alloy steel |
| `x1_420i` | 85 | Stainless steel |
| `inconel_718` | 40 | High-temp superalloy |
| `pla` | -- | 3D printing (no CAM) |
| `abs` | -- | 3D printing (no CAM) |

### CEM Safety Factor Thresholds

| Part | Check | Required SF |
|------|-------|-------------|
| aria_ratchet_ring | tooth_shear | 8.0 (safety-critical) |
| aria_spool | radial_load | 2.0 |
| aria_cam_collar | taper_engagement | 2.0 |
| aria_housing | wall_bending | 2.0 |
| aria_brake_drum | hoop_stress | 2.0 |
| All others (general) | primary check | 2.0 (warn at 1.5) |
