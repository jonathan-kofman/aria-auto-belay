# Repository Structure

Three active projects share this repository. Physical directories are organized
below; Python modules at the root cannot be moved without refactoring imports,
so they are documented by project here.

---

## 1. ARIA Auto-Belay Device

The actual climbing auto-belay hardware product.

### Physical directories (in `device/`)
| Path | Contents |
|---|---|
| `device/firmware/` | STM32 safety layer + ESP32 intelligence layer (C/C++/Arduino) |
| `device/aria-climb/` | React Native / Expo companion app (iOS + Android) |
| `device/aria-ui/` | Web dashboard UI (React + Vite + Tailwind) |
| `device/dataset/` | Drop-test audio data (Edge Impulse labels) |
| `device/docs/` | Setup guides, testing checklist, safety docs |

### Dashboard modules (`dashboard/`)
All Streamlit tabs and dashboard support files live in `dashboard/`. Backward-compat shims remain at root so existing imports still work.

| File | Role |
|---|---|
| `dashboard/aria_server.py` | FastAPI backend for the UI |
| `dashboard/aria_api_tab.py` | Dashboard tab: API |
| `dashboard/aria_cad_tab.py` | Dashboard tab: CAD viewer |
| `dashboard/aria_cem_tab.py` | Dashboard tab: CEM physics |
| `dashboard/aria_cem.py` | CEM entry shim for dashboard |
| `dashboard/aria_materials_tab.py` | Dashboard tab: materials |
| `dashboard/aria_outputs_tab.py` | Dashboard tab: outputs |
| `dashboard/aria_report_tab.py` | Dashboard tab: reports |
| `dashboard/aria_statemachine_tab.py` | Dashboard tab: state machine |
| `dashboard/aria_testdata_tab.py` | Dashboard tab: test data |
| `dashboard/aria_cert_package.py` | Certification package generator |
| `dashboard/aria_clutch_sweep.py` | Clutch parameter sweep |
| `dashboard/aria_design_history.py` | Design history viewer |
| `dashboard/aria_drop_parser.py` | Drop-test CSV parser |
| `dashboard/aria_fault_behavior.py` | Fault scenario analysis |
| `dashboard/aria_flyweight_verify.py` | Flyweight mass verification |
| `dashboard/aria_offline_mode.py` | Offline data mode |
| `dashboard/aria_phase1_drop_protocol.py` | Phase 1 drop test protocol |

### Python modules at root (device project)
| File | Role |
|---|---|
| `aria_dashboard.py` | Streamlit operator dashboard (entry point — stays at root) |
| `state_machine.py` | Python mirror of STM32 state machine |
| `aria_models/` | Physics models, static tests |
| `context/` | Mechanical specs, failure patterns, patent notes |
| `tools/` | Simulator, PID tuner, HIL tests, constants sync |
| `tests/` | Pytest suite |

### Entry scripts
```
scripts/START_DASHBOARD.bat / run_dashboard.bat / run_dashboard.ps1  — operator dashboard
scripts/START_ARIA_UI.bat / start_aria_ui.sh                          — web UI + API server
scripts/START_TEST_DAY.bat                                            — test day harness
scripts/setup_local_python.ps1                                        — local Python env setup
```

---

## 2. ARIA-OS CAD Pipeline

AI-driven multi-backend CAD generation tool (CadQuery / Fusion / Grasshopper / Blender).
This is a general-purpose engineering tool; ARIA parts are just one use case.

### Physical directories
| Path | Contents |
|---|---|
| `aria_os/` | Main pipeline module (orchestrator, generators, validators) |
| `aria_cem/` | CEM module inputs and definitions |
| `outputs/` | Generated CAD, CAM, ECAD, drawings, screenshots |
| `cad-pipeline/assembly_configs/` | ARIA assembly configs (clutch, etc.) |
| `cad-pipeline/parts/` | ARIA parts lists for batch generation |
| `cad-pipeline/cad/` | Fusion 360 scripts (root-level cad folder) |

### CEM physics modules (`cem/`)
Physics computation modules live in `cem/`. Backward-compat shims remain at root.

| File | Role |
|---|---|
| `cem/cem_core.py` | Base `Material` + `Fluid` classes; import from here, never redefine |
| `cem/cem_aria.py` | ARIA CEM thin shim → `compute_for_goal()` |
| `cem/cem_lre.py` | Liquid rocket engine CEM → `compute_lre_nozzle()` |
| `cem/cem_clock.py` | Mechanical clock CEM |
| `cem/cem_registry.py` | Maps goal keywords → CEM module names |
| `cem/cem_to_geometry.py` | CEM scalars → deterministic CadQuery scripts |

### Python modules at root (CAD pipeline)
| File | Role |
|---|---|
| `run_aria_os.py` | Main CLI entry point |
| `run_aria_os_cli.py` | Alternative CLI interface |
| `batch.py` | Batch part generation |
| `assemble.py` | Assembly from JSON config |
| `assemble_constrain.py` | Fusion 360 constrained assembly |
| `catalog.py` | Component catalog management |
| `fetch_component.py` | Component cache fetcher |
| `mesh_check.py` | Mesh integrity checker |
| `preview.py` | Quick STL preview helper |
| `screenshot.py` | STL PNG render |
| `generate_clock.py` | Clock assembly generator |
| `generate_map.py` | Layout map generator |
| `watch.py` | File watcher for hot reload |

---

## 3. Other Example Projects

Non-ARIA assemblies generated through the CAD pipeline.

| Path | Contents |
|---|---|
| `cad-pipeline/other-projects/assembly_configs/` | Clock, F1 car, welding robot, CNC router configs |
| `cad-pipeline/other-projects/parts/` | Parts lists for the above |

---

## Shared Infrastructure

| Path | Used by |
|---|---|
| `sessions/` | Session logs for all projects |
| `requirements.txt` | Dashboard + device Python deps |
| `requirements_aria_os.txt` | CAD pipeline Python deps |
| `CLAUDE.md` | Claude Code instructions |
