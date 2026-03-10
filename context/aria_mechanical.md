# ARIA Mechanical Constants & Geometry
# Source of truth for all CAD scripts. Never hardcode these values elsewhere.

## Housing
| Parameter         | Value     | Notes                          |
|-------------------|-----------|--------------------------------|
| Width             | 700.0 mm  |                                |
| Height            | 680.0 mm  |                                |
| Depth             | 344.0 mm  |                                |
| Wall thickness    | 10.0 mm   | Minimum — do not reduce        |

## Spool & Bearing Center
| Parameter         | Value     | Notes                          |
|-------------------|-----------|--------------------------------|
| Spool center X    | 350.0 mm  | From housing origin            |
| Spool center Y    | 330.0 mm  | From housing origin            |
| Rope spool dia    | 600.0 mm  |                                |
| Spool material    | 6061 Al   |                                |

## Bearings
| Parameter             | Value    | Notes                        |
|-----------------------|----------|------------------------------|
| Bearing OD            | 47.2 mm  |                              |
| Bearing shoulder OD   | 55.0 mm  |                              |
| Bearing shoulder H    | 3.0 mm   |                              |

## Clutch System
| Parameter             | Value    | Notes                        |
|-----------------------|----------|------------------------------|
| Brake drum diameter   | 200.0 mm | Centrifugal clutch           |
| Ratchet pocket dia    | 213.0 mm |                              |
| Ratchet pocket depth  | 21.0 mm  |                              |

## Rope Interface
| Parameter         | Value    | Notes                          |
|-------------------|----------|--------------------------------|
| Rope slot width   | 30.0 mm  |                                |
| Rope slot length  | 80.0 mm  |                                |

## Mounting Bosses
| Parameter         | Value    | Notes                          |
|-------------------|----------|--------------------------------|
| Boss diameter     | 30.0 mm  |                                |
| Boss height       | 20.0 mm  |                                |
| Boss hole dia     | 10.5 mm  |                                |
| Boss inset        | 60.0 mm  | From housing edge              |

## Cable & Drain
| Parameter         | Value    |
|-------------------|----------|
| Cable hole dia    | 25.0 mm  |
| Drain hole dia    | 8.0 mm   |

## Drivetrain
| Parameter             | Value      | Notes                      |
|-----------------------|------------|----------------------------|
| Motor type            | BLDC       | Slack management           |
| Gearbox ratio         | 30:1       | Planetary                  |

## Wall Mount
- Mounts behind wall panel to structural beam
- Only flush rope port, LED strip, and iPad HMI visible on wall face
- Behind-wall architecture for aesthetics and tamper resistance

## Material Specs
| Component     | Material      | Process              |
|---------------|---------------|----------------------|
| Housing       | 6061 Al       | CNC machined         |
| Spool         | 6061 Al       | CNC machined         |
| Brake drum    | Cast iron / steel | —               |
| Fasteners     | Stainless     | —                    |

## Fusion 360 API Notes
- All mm values → divide by 10.0 for Fusion's internal cm units
- Lambda: `cm = lambda mm: mm/10.0`
- Always use Direct Design mode, not Parametric
- Build sequence: solid box → interior cut → features on existing faces
- See context/aria_failures.md for known failure modes

## Pawl Geometry (from static_tests.py)
| Constant              | Value    | Variable name in code      |
|-----------------------|----------|----------------------------|
| Pawl tip width        | 6.0 mm   | PAWL_TIP_WIDTH_MM          |
| Pawl thickness        | 9.0 mm   | PAWL_THICKNESS_MM          |
| Pawl arm length       | 45.0 mm  | PAWL_ARM_MM                |
| Pawl body height      | 22.0 mm  | PAWL_BODY_H_MM             |
| Pawl engagement depth | 3.0 mm   | PAWL_ENGAGEMENT_MM         |
| Number of pawls       | 2        | N_PAWLS                    |

## Ratchet Geometry (from static_tests.py / aria_cem.py)
| Constant              | Value    | Variable name in code      |
|-----------------------|----------|----------------------------|
| Pitch radius          | 100.0 mm | RATCHET_PITCH_R_MM         |
| Face width            | 20.0 mm  | RATCHET_FACE_W_MM          |
| Number of teeth       | 24       | N_TEETH                    |
| Pressure angle        | 26.0 deg | pressure_angle_deg         |
| Module                | 3.0 mm   | module_mm                  |

## Shaft Geometry
| Constant              | Value    | Variable name in code      |
|-----------------------|----------|----------------------------|
| Shaft diameter        | 20.0 mm  | SHAFT_D_MM                 |
| Shaft span            | 344.0 mm | SHAFT_SPAN_MM              |

