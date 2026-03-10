# ARIA System Overview
## Autonomous Rope Intelligence Architecture

## What It Is
ARIA is an open-source, wall-mounted lead climbing auto-belay device.
It targets a genuine gap in the US market: no commercial auto-belay system
currently handles lead climbing (as opposed to top-rope). ARIA automates
rope management for solo lead climbing practice.

## Core Mechanical Design
Based on the Lead Solo centrifugal clutch design:
- 200mm brake drum
- 600mm rope spool
- 6061 aluminum housing
- Mounted BEHIND the wall panel — only the rope port, LED strip, and iPad HMI
  are visible on the wall face

## What Makes It Different From Existing Auto-Belays
- Existing devices (Trublue, etc.) are top-rope only
- ARIA handles the dynamic slack demands of lead climbing
- Adds powered rope management (BLDC + gearbox) on top of passive clutch
- Voice control + wearable BLE unit for hands-free operation
- CV-based zone intrusion detection
- Open source — designed for gym pilot deployment and community iteration

## Target Users
- Climbing gyms (B2B primary market)
- Solo lead climbers at facilities without partners
- 5–10 POC units before major testing phase

## Compliance
- Target standard: ANSI/ASSA Z359.14 (self-retracting lifelines)
- Intertek pre-certification call pending re: Z359.14 classification
- Cert package tooling: aria_cert_package.py

## IP Status
- Provisional patent filed (4 claims)
- Patent doc: [TODO: add path once converted to .md]
- NDA drafted for gym pilot outreach

## Repository
- GitHub: https://github.com/jonathan-kofman/aria-auto-belay (public)
- Pushed: 2/28/2026

## Key Documents
| Document                      | Location                           |
|-------------------------------|------------------------------------|
| Full setup guide              | docs/ARIA_SETUP.md                 |
| App specification             | docs/ARIA_APP_SPEC.md              |
| Safety monitoring spec        | docs/ARIA_SAFETY_MONITORING.md     |
| Cursor development brief      | docs/ARIA_CURSOR_BRIEF.md          |
| Edge Impulse setup            | docs/edge_impulse_setup.md         |
| Testing checklist             | docs/REAL_TESTING_CHECKLIST.md     |
| Psychology / UX research      | ARIA___Psychology.pdf              |
| Renders                       | Renders.pdf                        |

## Dashboard
- Run: `START_DASHBOARD.bat` or `python aria_dashboard.py`
- Tabs: CEM, materials, state machine, test data, reports
- Companion app: aria-climb/ (React Native / Expo)

## Agent Notes
- sessions/ is empty — write session logs here after every agent run
- tests/ is empty — write unit tests here as firmware stabilizes
- context/ is the knowledge base — always read before acting
