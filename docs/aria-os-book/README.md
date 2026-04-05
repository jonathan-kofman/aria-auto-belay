# ARIA-OS Project Book

| Field | Value |
|---|---|
| **Project** | ARIA-OS (Autonomous Rope Intelligence Architecture — Operating System) |
| **Version** | 0.9.0-beta |
| **Status** | Active development, pre-launch |
| **Maintainer** | Jonathan Ko |
| **Repository** | `aria-auto-belay/aria_os/` |
| **License** | Proprietary |
| **Last updated** | 2026-03-31 |

---

## What Is This Book?

This is the complete project book for ARIA-OS, the AI-driven CAD pipeline that generates 3D mechanical parts from natural language descriptions. It covers architecture, decisions, operations, and roadmap.

ARIA-OS is one component of the broader ARIA project (a wall-mounted auto-belay device for climbing gyms). The hardware documentation lives separately at `docs/book/`.

---

## Table of Contents

| # | Chapter | What You Will Learn |
|---|---|---|
| 00 | [Elevator Pitch](./00-elevator-pitch.md) | What ARIA-OS is, who it is for, key metrics |
| 01 | [The Why](./01-the-why.md) | The problem, what exists today, the gap |
| 02 | [The Vision](./02-the-vision.md) | Product vision, user stories, success metrics |
| 03 | [The Map](./03-the-map.md) | Architecture, pipeline flow, data flow, API surface |
| 04 | [The Foundation](./04-the-foundation.md) | Tech stack decisions, dependencies, infrastructure |
| 05 | [The Build](./05-the-build.md) | Development setup, first run, testing, CI |
| 06 | [Integrations](./06-integrations.md) | External services: Onshape, Claude, Gemini, Zoo.dev, Lightning AI |
| 07 | [Gotchas](./07-gotchas.md) | Known issues, failure patterns, workarounds |
| 08 | [Operations](./08-operations.md) | CLI commands, batch mode, dashboard, extending the system |
| 09 | [Roadmap](./09-roadmap.md) | What is done, what is next, Q2-Q4 2026 |
| 10 | [Appendix](./10-appendix.md) | All 49 templates, CLI reference, env vars, output paths |

---

## How to Use This Book

**If you are a YC partner or investor evaluating the system:**
Start with [00 Elevator Pitch](./00-elevator-pitch.md), then [01 The Why](./01-the-why.md) for competitive landscape, then [09 Roadmap](./09-roadmap.md) for where this is going.

**If you are a developer extending ARIA-OS:**
Start with [03 The Map](./03-the-map.md) for architecture, then [05 The Build](./05-the-build.md) for setup, then [07 Gotchas](./07-gotchas.md) to avoid known pitfalls.

**If you are a user generating parts:**
Start with [08 Operations](./08-operations.md) for CLI usage, then [10 Appendix](./10-appendix.md) for template and command reference.

**If you want to understand the design decisions:**
Read [04 The Foundation](./04-the-foundation.md) for tech stack rationale, then [06 Integrations](./06-integrations.md) for external service architecture.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements_aria_os.txt

# Generate a part from natural language
python run_aria_os.py "aluminium bracket 100x60x8mm with 4x M6 holes"

# Full pipeline: generate + FEA + drawing + render + CAM + setup sheet
python run_aria_os.py --full "ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
```

For detailed setup instructions, see [05 The Build](./05-the-build.md).

---

[Next: Elevator Pitch -->](./00-elevator-pitch.md)
