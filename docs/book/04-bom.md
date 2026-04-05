[&larr; Back to Table of Contents](./README.md) &middot; [Previous: The Architecture](./03-the-architecture.md) &middot; [Next: The Build &rarr;](./05-the-build.md)

# Bill of Materials

## BOM Summary

This is the complete bill of materials for one ARIA unit. Prices are estimates as of 2026 Q1. Source links will be added as parts are ordered and validated.

> **Tip:** Order 10-15% extra fasteners. You will drop M4 screws into the wall cavity.

## Electronics

| # | Part | Spec | Qty | Source | Est. Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | STM32 Dev Board | {e.g. STM32F446RE Nucleo} | 1 | {e.g. DigiKey} | {e.g. $15} | Safety layer MCU |
| 2 | ESP32 Dev Board | ESP32-WROOM-32 | 1 | {e.g. DigiKey} | {e.g. $8} | Intelligence layer MCU |
| 3 | VESC Motor Controller | {e.g. VESC 6.7} | 1 | {e.g. Flipsky} | {e.g. $80} | FOC motor drive |
| 4 | BLDC Motor | {e.g. 5065 or similar, sized for torque study} | 1 | {e.g. Flipsky} | {e.g. $45} | Rope tension drive |
| 5 | Planetary Gearbox | 30:1 ratio, {e.g. Nema 23 frame} | 1 | {e.g. Amazon / AliExpress} | {e.g. $60} | Speed reduction, torque multiplication |
| 6 | HX711 Load Cell Amp | 24-bit ADC, breakout board | 1 | {e.g. SparkFun} | {e.g. $10} | Tension measurement |
| 7 | Load Cell | {e.g. 50 kg S-type} | 1 | {e.g. Amazon} | {e.g. $15} | Inline rope tension sensor |
| 8 | Camera Module | {e.g. OV2640, SPI} | 1 | {e.g. AliExpress} | {e.g. $8} | Clip detection CV |
| 9 | Microphone / MEMS | {e.g. INMP441 I2S} | 1 | {e.g. DigiKey} | {e.g. $5} | Voice command input for Edge Impulse |
| 10 | LED Strip (WS2812B) | {e.g. 30 LED/m, 0.5 m} | 1 | {e.g. Amazon} | {e.g. $8} | Wall-face status indicator |
| 11 | 12V Power Supply | {e.g. 12V 10A, Mean Well} | 1 | {e.g. DigiKey} | {e.g. $25} | Main system power |
| 12 | Barrel Jack Connector | 5.5x2.1 mm, panel mount | 1 | {e.g. DigiKey} | {e.g. $2} | Power input |
| 13 | Brake Solenoid | {e.g. 12V push-pull} | 1 | {e.g. Amazon} | {e.g. $15} | Power-off brake release |
| 14 | MOSFET Driver Board | {e.g. IRF520 module} | 1 | {e.g. Amazon} | {e.g. $3} | Solenoid drive from STM32 GPIO |
| 15 | Voltage Regulator | 12V to 3.3V/5V | 2 | {e.g. DigiKey} | {e.g. $6} | MCU power rails |
| 16 | Flyback Diode | {e.g. 1N4007} | 1 | {e.g. DigiKey} | {e.g. $0.10} | Solenoid protection |
| 17 | JST Connectors | {e.g. JST-XH 4-pin} | 6 | {e.g. DigiKey} | {e.g. $4} | Sensor and motor harness |
| 18 | Wire Harness | {e.g. 22 AWG silicone} | 1 lot | {e.g. Amazon} | {e.g. $10} | Internal wiring |

**Electronics Subtotal:** {e.g. ~$320}

## Mechanical

| # | Part | Spec | Qty | Source | Est. Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Housing | 6061 Al, 700x680x344 mm, 10 mm wall | 1 | CNC machined | {e.g. $800-1500} | Primary structure |
| 2 | Spool | 6061 Al, 600 mm dia | 1 | CNC machined | {e.g. $200-400} | Rope storage |
| 3 | Ratchet Ring | {e.g. 4140 steel}, 213 mm OD, 24 teeth | 1 | CNC machined | {e.g. $150-300} | Anti-reverse mechanism |
| 4 | Catch Pawls | {e.g. 4140 steel}, 45 mm arm | 2 | CNC machined | {e.g. $40-80} | Engage ratchet teeth |
| 5 | Brake Drum | Cast iron / steel, 200 mm dia | 1 | CNC machined / cast | {e.g. $100-200} | Clutch engagement surface |
| 6 | Cam Collar | {e.g. 6061 Al} | 1 | CNC machined | {e.g. $50-100} | Tapered clutch engagement |
| 7 | Rope Guide | {e.g. 6061 Al} | 1 | CNC machined | {e.g. $30-60} | Roller guide bracket |
| 8 | Shaft | Steel, 20 mm dia, 344 mm long | 1 | Turned | {e.g. $20-40} | Central shaft |
| 9 | Deep Groove Bearings | 47.2 mm OD | 2 | {e.g. SKF / Amazon} | {e.g. $15} | Shaft support |
| 10 | Pawl Springs | {e.g. compression, sized per CEM} | 2 | {e.g. McMaster} | {e.g. $5} | Pawl return force |
| 11 | Brake Spring | {e.g. compression, sized per brake design} | 1 | {e.g. McMaster} | {e.g. $5} | Power-off brake engagement |

**Mechanical Subtotal:** {e.g. ~$1,500-2,800}

## Fasteners

| # | Part | Spec | Qty | Notes |
|---|---|---|---|---|
| 1 | Wall Mount Bolts | {e.g. M10 x 80 mm, Grade 8.8} | 4 | Into structural beam |
| 2 | Housing Assembly Screws | {e.g. M6 x 16 mm, stainless} | {e.g. 20} | Housing panels |
| 3 | Bearing Retainers | {e.g. M4 x 12 mm, stainless} | 4 | Bearing shoulders |
| 4 | Motor Mount Bolts | {e.g. M5 x 20 mm, stainless} | 4 | Motor to housing |
| 5 | PCB Standoffs | M3 x 10 mm, nylon | {e.g. 8} | STM32 + ESP32 boards |
| 6 | Cable Glands | {e.g. PG11} | 2 | Cable and drain holes (25 mm, 8 mm) |
| 7 | Lock Washers | {e.g. M6, M10} | Assorted | All structural joints |
| 8 | Threadlocker | Loctite 242 (blue, medium) | 1 | All structural fasteners |

**Fasteners Subtotal:** {e.g. ~$30}

## 3D Printed Parts

| # | Part | Material | Notes |
|---|---|---|---|
| 1 | Wire management clips | PETG or ASA | Internal harness routing |
| 2 | Sensor mount brackets | PETG or ASA | Camera + microphone positioning |
| 3 | LED diffuser strip | Clear PETG | Wall-face light pipe |
| 4 | Connector shroud | PETG | JST strain relief |

> **Tip:** Use PETG or ASA, not PLA. The inside of the housing may reach 40+ C in summer months near the motor.

**3D Printed Parts Subtotal:** ~$5 in filament

## PCBs

| # | Board | Size | Notes |
|---|---|---|---|
| 1 | ARIA Sensor Board | 80 x 60 mm | ESP32 + HX711 + UART + BLE; generated via `--ecad` pipeline |
| 2 | Breakout / Wiring Board | {e.g. 50 x 40 mm} | Power distribution, JST headers, MOSFET driver |

> **Tip:** The ARIA-OS pipeline can generate KiCad pcbnew scripts for these boards. Run `python run_aria_os.py --ecad "ARIA ESP32 board, 80x60mm, 12V, UART, BLE, HX711"` to produce the script and BOM.

**PCB Subtotal:** {e.g. ~$20 for prototypes via JLCPCB}

## Tools Required

- [ ] Allen key set (metric: M3, M4, M5, M6)
- [ ] Torque wrench (for M10 wall mount bolts)
- [ ] Soldering station
- [ ] Multimeter
- [ ] Wire strippers / crimpers
- [ ] USB-C cables (STM32 + ESP32 flashing)
- [ ] Serial terminal software (PuTTY, screen, or Arduino IDE Serial Monitor)
- [ ] Loctite 242 (blue threadlocker)
- [ ] Drill with masonry/wood bits (wall mounting, depending on structure)
- [ ] Level (for housing alignment)
- [ ] Caliper (for verifying machined part dimensions)

---

**Estimated Total BOM Cost:** {e.g. $1,900-3,200} per unit (dominated by CNC machined parts)

> **Warning:** These are rough estimates. Actual CNC costs depend on shop rates, batch size, and material sourcing. Get quotes from your shop before committing to a design.

[Next: The Build &rarr;](./05-the-build.md)
