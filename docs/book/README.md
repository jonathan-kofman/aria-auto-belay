# ARIA Auto-Belay Project Book


| Field            | Value                                                  |
| ---------------- | ------------------------------------------------------ |
| **Project**      | ARIA (Autonomous Rope Intelligence Architecture)       |
| **Description**  | Wall-mounted AI-driven lead climbing auto-belay device |
| **Last Updated** | 2026-03-31                                             |
| **Revision**     | 1.0                                                    |
| **Maintainer**   | Jonathan Kofman                                        |
| **License**      | Proprietary                                            |


---

## Table of Contents


| #   | Chapter                                      | What You Will Find                                                 |
| --- | -------------------------------------------- | ------------------------------------------------------------------ |
| 0   | [Elevator Pitch](./00-elevator-pitch.md)     | What ARIA is, who it serves, key specs                             |
| 1   | [The Why](./01-the-why.md)                   | The problem, what exists, the gap, why now                         |
| 2   | [The Design](./02-the-design.md)             | Design principles, constraints, tradeoffs                          |
| 3   | [The Architecture](./03-the-architecture.md) | System diagram, mechanical/electrical/software breakdown           |
| 4   | [Bill of Materials](./04-bom.md)             | Full BOM: electronics, mechanical, fasteners, PCBs, tools          |
| 5   | [The Build](./05-the-build.md)               | Step-by-step assembly instructions                                 |
| 6   | [The Firmware](./06-the-firmware.md)         | Flashing, configuration, architecture, protocols                   |
| 7   | [Calibration](./07-calibration.md)           | First power-on, sensor/actuator verification, tuning               |
| 8   | [The Gotchas](./08-the-gotchas.md)           | Known pitfalls, common mistakes, misleading symptoms               |
| 9   | [Safety](./09-safety.md)                     | Hazard summary, electrical/mechanical safety, emergency procedures |
| 10  | [Operations](./10-operations.md)             | Normal operation, troubleshooting, maintenance schedule            |
| 11  | [Appendix](./11-appendix.md)                 | Pinouts, schematics, datasheets, error codes, glossary             |


---

## How to Use This Book

**Building ARIA for the first time?**
Start at [Chapter 0](./00-elevator-pitch.md) and read straight through. The chapters are ordered in the sequence you will need them: understand the device, gather parts, build it, flash firmware, calibrate, and operate.

**Evaluating whether ARIA fits your gym?**
Read [Chapter 0 (Elevator Pitch)](./00-elevator-pitch.md) and [Chapter 9 (Safety)](./09-safety.md). That covers what it does and how it keeps climbers safe.

**Debugging a problem?**
Go to [Chapter 8 (The Gotchas)](./08-the-gotchas.md) first. If your issue is not listed, check [Chapter 10 (Operations)](./10-operations.md) for the troubleshooting table.

**Extending the firmware or CAD pipeline?**
Read [Chapter 3 (Architecture)](./03-the-architecture.md) and [Chapter 6 (Firmware)](./06-the-firmware.md) for the full software and hardware breakdown.

**Looking up a pinout, error code, or constant?**
Go directly to [Chapter 11 (Appendix)](./11-appendix.md).

---

## Keeping This Book Alive

This book is only useful if it matches the hardware on the wall. Follow these rules:

1. **Every hardware change gets a book update in the same commit.** If you change a pin assignment, update the appendix pinout table.
2. **Every firmware constant change must be reflected here.** Run `python tools/aria_constants_sync.py` to verify alignment between firmware and documentation.
3. **BOM changes require updating Chapter 4.** Include source links and current pricing.
4. **Safety-critical changes require a revision bump.** Update the revision field in this README and add an entry to the Revision History in the Appendix.
5. **If you find something wrong, fix it now.** Do not leave a "TODO" in a hardware book. Someone will build from these instructions.

