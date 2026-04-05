[<-- Back to Table of Contents](./README.md) | [<-- Previous: Roadmap](./09-roadmap.md)

---

# Appendix

## A. All 49 CadQuery Templates

Each template is a Python function that takes a `params` dict and returns a CadQuery script string. Templates produce valid geometry on every invocation --- no LLM involved.

### ARIA Structural Parts (7)

| # | Template | Function | Description |
|---|---|---|---|
| 1 | `aria_ratchet_ring` | `_cq_ratchet_ring` | External ratchet ring with asymmetric tooth profile (drive 8 deg, back 60 deg) |
| 2 | `aria_housing` | `_cq_housing` | Cylindrical housing (with OD) or rectangular enclosure (without OD) |
| 3 | `aria_spool` | `_cq_spool` | Rope spool with flanges, hub bore, and rope grooves |
| 4 | `aria_cam_collar` | `_cq_cam_collar` | Tapered cam collar for brake engagement |
| 5 | `aria_brake_drum` | `_cq_brake_drum` | Brake drum with hub bore and wall |
| 6 | `aria_catch_pawl` | `_cq_catch_pawl` | Flat pawl/strip with pivot bore and tapered tip |
| 7 | `aria_rope_guide` | `_cq_rope_guide` | Rope guide with roller channel and mounting bracket |

### Generic Mechanical Parts (16)

| # | Template | Function | Description |
|---|---|---|---|
| 8 | `bracket` | `_cq_bracket` | Rectangular bracket with bolt holes and optional center bore |
| 9 | `l_bracket` | `_cq_l_bracket` | L-shaped angle bracket with mounting holes on both faces |
| 10 | `flange` | `_cq_flange` | Circular flange with bolt circle and center bore |
| 11 | `shaft` | `_cq_shaft` | Solid cylindrical shaft |
| 12 | `pin` | `_cq_pin` | Dowel pin (short cylinder) |
| 13 | `spacer` | `_cq_spacer` | Ring/disc/washer (OD - bore - height) |
| 14 | `tube` | `_cq_tube` | Hollow tube (OD - ID - length) |
| 15 | `pulley` | `_cq_pulley` | V-groove pulley with hub bore |
| 16 | `gear` | `_cq_gear` | Simplified spur gear with trapezoidal teeth |
| 17 | `cam` | `_cq_cam` | Eccentric disc cam |
| 18 | `flat_plate` | `_cq_flat_plate` | Flat rectangular plate with optional holes |
| 19 | `hollow_rect` | `_cq_hollow_rect` | Hollow rectangular tube (structural link, extrusion profile) |
| 20 | `nozzle` | `_cq_nozzle` | Convergent-divergent bell nozzle (revolved in XY around Y axis) |
| 21 | `escape_wheel` | `_cq_escape_wheel` | Clock escapement wheel with pointed teeth |
| 22 | `involute_gear` | `_cq_involute_gear` | High-fidelity involute spur gear with true tooth profile |
| 23 | `cam_profile` | `_cq_cam_profile` | Eccentric cam disc with dwell/rise/fall lobes |

### Standard Components (5)

| # | Template | Function | Description |
|---|---|---|---|
| 24 | `nema_motor` | `_cq_nema_motor` | NEMA stepper motor model (17/23/34 sizes) |
| 25 | `mgn_rail` | `_cq_mgn_rail` | MGN linear rail (12/15/25 sizes) |
| 26 | `ball_bearing` | `_cq_ball_bearing` | Ball bearing (inner/outer race, no balls) |
| 27 | `shaft_coupling` | `_cq_shaft_coupling` | Rigid shaft coupling with clamping screws |
| 28 | `profile_extrusion` | `_cq_profile_extrusion` | V-slot/T-slot aluminum extrusion (2020/4040) |

### Consumer / 3D Print Parts (6)

| # | Template | Function | Description |
|---|---|---|---|
| 29 | `phone_case` | `_cq_phone_case` | Protective phone/device case with cutouts |
| 30 | `phone_stand` | `_cq_phone_stand` | Angled phone/tablet stand |
| 31 | `snap_hook` | `_cq_snap_hook` | Snap-fit hook/clip |
| 32 | `thread_insert` | `_cq_thread_insert` | Threaded/knurled heat-set insert |
| 33 | `heat_sink` | `_cq_heat_sink` | Parallel fin heat sink |
| 34 | `handle` | `_cq_handle` | Pull handle / grip / knob |

### Enclosure & Structural (8)

| # | Template | Function | Description |
|---|---|---|---|
| 35 | `hinge` | `_cq_hinge` | Door/butt hinge with knuckle joints |
| 36 | `clamp` | `_cq_clamp` | C-clamp / pipe clamp / cable clamp |
| 37 | `enclosure_lid` | `_cq_enclosure_lid` | Snap-fit lid for enclosures |
| 38 | `gusset` | `_cq_gusset` | Triangular gusset plate / corner brace |
| 39 | `spoked_wheel` | `_cq_spoked_wheel` | Spoked handwheel / steering wheel |
| 40 | `t_slot_plate` | `_cq_t_slot_plate` | T-slot fixture/tooling plate |
| 41 | `pcb_enclosure` | `_cq_pcb_enclosure` | Electronics enclosure with PCB standoffs |
| 42 | `bearing_pillow_block` | `_cq_bearing_pillow_block` | Bearing pillow/plummer block |

### Specialized Mechanical (7)

| # | Template | Function | Description |
|---|---|---|---|
| 43 | `spring_clip` | `_cq_spring_clip` | Retaining clip / circlip / U-clip |
| 44 | `bellows` | `_cq_bellows` | Corrugated bellows / flex joint |
| 45 | `compression_spring` | `_cq_compression_spring` | Helical compression spring (coil approximation) |
| 46 | `keyway_shaft` | `_cq_keyway_shaft` | Shaft with keyway slot |
| 47 | `dovetail_joint` | `_cq_dovetail_joint` | Dovetail rail / slide joint |
| 48 | `slot_plate` | `_cq_slot_plate` | Plate with multiple parallel slots |
| 49 | `cable_gland` | `_cq_cable_gland` | Cable gland / strain relief fitting |

---

## B. CadQuery Operations Reference (25 Unique Operations)

These tested operations are injected into LLM prompts. Each has working code.

| # | Operation | Description |
|---|---|---|
| 1 | `box` | Rectangular solid |
| 2 | `cylinder` | Circular disc or cylinder (`.circle(r).extrude(h)`) |
| 3 | `tube` | Hollow cylinder (OD - bore) |
| 4 | `through_hole` | Simple through-hole on top face |
| 5 | `counterbore` | Counterbore hole (bolt recess) |
| 6 | `countersink` | Countersink hole (screw flush) |
| 7 | `pocket` | Rectangular pocket cut |
| 8 | `slot` | Through-slot |
| 9 | `circular_bolt_pattern` | N holes evenly spaced on a circle |
| 10 | `rectangular_bolt_pattern` | 4 holes at rectangle corners |
| 11 | `shell` | Hollow out a solid (wall thickness) |
| 12 | `shell_open_top` | Shell with open face |
| 13 | `revolve_profile` | Revolve 2D profile around axis (nozzles, cups) |
| 14 | `revolve_hollow` | Revolve hollow profile (tubes, vases) |
| 15 | `sweep_circle` | Sweep circle along path (pipes) |
| 16 | `sweep_rect` | Sweep rectangle along path (rails) |
| 17 | `loft_rect_to_circle` | Transition from rectangle to circle |
| 18 | `loft_two_rects` | Taper from large to small rectangle |
| 19 | `fillet_vertical` | Fillet vertical edges |
| 20 | `fillet_top` | Fillet top face edges |
| 21 | `chamfer_edges` | Chamfer selected edges |
| 22 | `boss` | Raised cylindrical boss |
| 23 | `rib` | Reinforcing rib/stiffener |
| 24 | `engrave_text` | Text engraving on face |
| 25 | `mirror` | Mirror body across a plane |

Additional composite operations (union, cut, intersect, linear_pattern) and domain-specific snippets (GoPro mount, heat sink fins, L-bracket) are also included.

---

## C. All CLI Commands

### Core Generation

| Command | Description |
|---|---|
| `python run_aria_os.py "<goal>"` | Generate part from natural language |
| `python run_aria_os.py --full "<goal>"` | Full pipeline (all outputs) |
| `python run_aria_os.py --full "<goal>" --machine "HAAS VF2"` | Full pipeline with machine override |
| `python run_aria_os.py --coordinator "<goal>"` | Run 5-phase agent pipeline |
| `python run_aria_os.py --image <path> ["hint"]` | Generate from photo |
| `python run_aria_os.py --preview "<goal>"` | 3D browser preview before export |
| `python run_aria_os.py --modify <script> "<changes>"` | Modify existing part |

### Inspection and Validation

| Command | Description |
|---|---|
| `python run_aria_os.py --list` | List all generated parts with status |
| `python run_aria_os.py --validate` | Re-validate all STEP files |
| `python run_aria_os.py --cem-full` | CEM physics check on all parts |
| `python run_aria_os.py --material-study <part>` | Material comparison study |
| `python run_aria_os.py --material-study-all` | Material study for all parts |
| `python run_aria_os.py --analyze-part <step> [--fea\|--cfd\|--auto]` | FEA or CFD analysis |

### Manufacturing

| Command | Description |
|---|---|
| `python run_aria_os.py --draw <step>` | Generate GD&T drawing SVG |
| `python run_aria_os.py --cam <step> --material <mat>` | Generate Fusion 360 CAM script |
| `python run_aria_os.py --cam-validate <step>` | Machinability check |
| `python run_aria_os.py --setup <step> <cam_script>` | Generate CNC setup sheet |

### Optimization

| Command | Description |
|---|---|
| `python run_aria_os.py --optimize <part> --goal <goal> --constraint "<expr>"` | Parametric optimizer |
| `python run_aria_os.py --optimize-and-regenerate <part> --goal <goal>` | Optimize + regenerate |
| `python run_aria_os.py --print-scale <part> --scale <factor>` | Print-fit scaling check |

### Assembly

| Command | Description |
|---|---|
| `python run_aria_os.py --assemble <config.json>` | Assemble from JSON config |
| `python run_aria_os.py --constrain <config.json>` | Generate Fusion 360 constraints |
| `python run_aria_os.py --generate-and-assemble "<goal>" --into <config> --as <id>` | Generate + add to assembly |
| `python assemble.py <config.json> [--no-clearance]` | Assembly CLI |
| `python assemble_constrain.py <config.json> [--proximity N]` | Constrain CLI |

### Batch

| Command | Description |
|---|---|
| `python batch.py <parts.json>` | Batch generate from JSON part list |
| `python batch.py <parts.json> --skip-existing` | Skip already-generated |
| `python batch.py <parts.json> --only "<filter>" --workers N` | Filter + parallel |
| `python batch.py <parts.json> --render` | PNG preview per part |
| `python batch.py <parts.json> --verify-mesh` | Mesh compatibility check |

### Specialized Domains

| Command | Description |
|---|---|
| `python run_aria_os.py --ecad "<description>"` | KiCad PCB generation |
| `python run_aria_os.py --ecad-variants "<desc>" --variants <file>` | ECAD variant study |
| `python run_aria_os.py --autocad "<description>" --state TX --discipline drainage` | Civil DXF |
| `python run_aria_os.py --lattice --pattern honeycomb --width 100 --height 100 --depth 10` | Blender lattice |
| `python run_aria_os.py --scenario "<situation>"` | Scenario decomposition |
| `python run_aria_os.py --system "<description>"` | Full system design |

---

## D. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | (none) | Anthropic Claude API |
| `GOOGLE_API_KEY` | (none) | Google Gemini API |
| `ZOO_API_TOKEN` | (none) | Zoo.dev text-to-STEP |
| `ONSHAPE_ACCESS_KEY` | (none) | Onshape REST API |
| `ONSHAPE_SECRET_KEY` | (none) | Onshape REST API |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Override Gemini model |
| `GEMMA_MODEL` | `gemma4:31b` | Override Gemma model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Default Ollama model |

---

## E. LLM Priority Chain (Detailed)

### Code Generation (`call_llm`)

```
1. Anthropic Claude
   Models: claude-sonnet-4-6 -> claude-3-5-sonnet-20241022
   Retry: 3x on overload (5s, 10s, 20s backoff)
   
2. Google Gemini
   Models: gemini-2.0-flash -> gemini-2.0-flash-lite -> gemini-2.5-flash
   SDK: google-genai (new) -> google-generativeai (legacy)
   
3. Gemma 4 31B (Ollama)
   Model: gemma4:31b (configurable via GEMMA_MODEL)
   Auto-reconnects Lightning AI tunnel if down
   Retry: 1x on HTTP 500 (OOM)
   
4. Ollama Default
   Model: qwen2.5-coder:7b (configurable via OLLAMA_MODEL)
   NOTE: Skipped for CAD code generation (too unreliable at 7B)
   
5. None -> caller falls back to templates/heuristics
```

### Non-Code Tasks (`call_llm_local_first`)

```
1. Gemma 4 31B (Ollama) -> free, fast reasoning
2. Google Gemini         -> conserves Anthropic quota
3. Anthropic Claude      -> last resort
4. Ollama Default        -> fallback
5. None
```

### Visual Verification

```
1. Gemini 2.5 Flash -> fast, cheap, adequate vision
2. Anthropic Claude  -> fallback (more expensive)
3. None -> visual verification skipped
```

### Image Analysis (`analyze_image_for_cad`)

```
1. Google Gemini (vision) -> primary
2. Anthropic Claude (vision) -> fallback
3. Ollama (llava / llava-llama3) -> local fallback
4. None
```

---

## F. Output Paths

| Path | Contents | Git Tracked |
|---|---|---|
| `outputs/cad/step/` | STEP files | No |
| `outputs/cad/stl/` | STL files | No |
| `outputs/cad/generated_code/` | CadQuery scripts | No |
| `outputs/cad/meta/` | Version metadata JSON per part | Yes |
| `outputs/cad/grasshopper/<part>/` | Grasshopper params + scripts | Yes |
| `outputs/cad/dxf/` | Civil engineering DXF + JSON sidecar | No |
| `outputs/cad/fusion_scripts/` | Fusion 360 parametric API scripts | No |
| `outputs/cad/learning_log.json` | Attempt outcomes (success/fail + error) | Yes |
| `outputs/cam/<part>/` | CAM scripts, setup sheets, machinability | No |
| `outputs/drawings/` | GD&T engineering drawing SVGs | No |
| `outputs/ecad/<board>/` | KiCad scripts, BOM, validation, variants | No |
| `outputs/screenshots/` | PNG renders of STL files | No |
| `outputs/aria_generation_log.json` | GH pipeline run log | No |
| `outputs/api_run_log.json` | API server run log | No |
| `cem_design_history.json` | CEM parameter snapshots | No |
| `contracts/cam_setup_schema_v1.json` | Setup sheet JSON Schema | Yes |
| `contracts/ecad_bom_schema_v1.json` | BOM JSON Schema | Yes |
| `sessions/` | Agent session logs | Yes |
| `workspace/scratchpad/<job_id>/` | Coordinator job artifacts | No |

---

## G. Spec Extraction Patterns

The `spec_extractor.py` module recognizes these dimension patterns:

| Pattern | Example | Extracted |
|---|---|---|
| `NNmm OD` | `213mm OD` | `od_mm: 213` |
| `OD NNmm` | `OD 50mm` | `od_mm: 50` |
| `NN mm outer` | `50mm outer` | `od_mm: 50` |
| `NNmm bore` | `30mm bore` | `bore_mm: 30` |
| `NNmm ID` | `120mm ID` | `bore_mm: 120` |
| `WxHxDmm` | `100x60x8mm` | `width_mm: 100, height_mm: 60, depth_mm: 8` |
| `WxHmm` | `100x60mm` | `width_mm: 100, height_mm: 60` |
| `NNmm thick` | `8mm thick` | `thickness_mm: 8` |
| `NNmm tall` / `NNmm height` | `50mm tall` | `height_mm: 50` |
| `NNmm long` / `NNmm length` | `300mm long` | `length_mm: 300` |
| `NN teeth` | `24 teeth` | `n_teeth: 24` |
| `NxMN bolt` | `4xM6 bolts` | `n_bolts: 4, bolt_dia_mm: 6` |
| `NN holes` | `4 holes` | `n_bolts: 4` |
| `NNmm bolt circle` | `80mm bolt circle` | `bolt_circle_r_mm: 40` |
| `NNmm wall` | `5mm wall` | `wall_mm: 5` |
| `NNmm radius` | `50mm radius` | `diameter_mm: 100` (radius->diameter conversion) |
| Material keywords | `aluminium`, `6061`, `titanium`, `steel`, `PLA` | `material: "aluminium_6061"` |

---

## H. Materials Supported

### CEM / FEA

| Material Key | Yield (MPa) | Density (kg/m3) | Use Case |
|---|---|---|---|
| `aluminium_6061` | 276 | 2700 | General structural |
| `aluminium_7075` | 503 | 2810 | High-strength structural |
| `steel_4140` | 655 | 7850 | Shafts, gears |
| `x1_420i` | 530 | 7800 | ARIA structural parts (maraging steel) |
| `inconel_718` | 1034 | 8190 | LRE nozzles, high-temp |
| `titanium_6al4v` | 880 | 4430 | Aerospace, medical |

### CAM (feeds/speeds)

| Material Key | SFM | Application |
|---|---|---|
| `aluminium_6061` | 300 | General purpose aluminium |
| `aluminium_7075` | 260 | High-strength aluminium |
| `x1_420i` | 85 | Maraging steel |
| `inconel_718` | 40 | Nickel superalloy |
| `steel_4140` | 90 | Alloy steel |
| `pla` | N/A | 3D print (no CAM) |
| `abs` | N/A | 3D print (no CAM) |

---

[<-- Back to Table of Contents](./README.md) | [<-- Previous: Roadmap](./09-roadmap.md)
