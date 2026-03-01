# ARIA — Complete Setup Guide
## Autonomous Rope Intelligence Architecture
### Jonathan Kofman — Lead Auto Belay Project

---

## HARDWARE SHOPPING LIST

| Item | Link | Qty | ~Cost |
|------|------|-----|-------|
| STM32F411 Black Pill + ST-Link V2 | amazon.com/dp/B0D2M3HL1Q | 2+1 | $26 |
| Seeed XIAO ESP32-S3 Sense (camera+mic) | seeedstudio.com/XIAO-ESP32S3-Sense | 1 | $20 |
| HX711 + 50kg load cell combo | amazon.com/dp/B079LVMC9D | 1 | $10 |
| AS5048A magnetic rotary encoder | amazon.com/dp/B07MMWMGKR | 1 | $12 |
| BLDC motor (T-Motor GB54-2 or similar) | tmotor.com or aliexpress | 1 | $80-120 |
| 30:1 planetary gearbox (matched to motor) | aliexpress search "30:1 planetary gearbox BLDC" | 1 | $40-60 |
| **TOTAL** | | | **~$190-$260** |

---

## SOFTWARE SETUP

### Step 1 — Install Arduino IDE
Download from: https://www.arduino.cc/en/software
Install version 2.x (not legacy 1.x)

### Step 2 — Add ESP32 and STM32 board support
In Arduino IDE → Preferences → Additional Board Manager URLs, add both:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json
```
Then: Tools → Board → Boards Manager → search "esp32" → install Espressif Systems ESP32
And: search "STM32" → install STMicroelectronics STM32

### Step 3 — Install SimpleFOC
Tools → Manage Libraries → search "Simple FOC" → install "Simple Field Oriented Control"

### Step 4 — Install Python dependencies (for simulator and data collection)
```bash
pip install sounddevice soundfile numpy
```

---

## FLASHING ORDER

### STM32 (safety layer) — Flash first
1. Connect ST-Link V2 to Black Pill:
   - SWDIO → PA13
   - SWCLK → PA14
   - GND   → GND
   - 3.3V  → 3.3V
2. Open `aria_stm32_complete.cpp` in Arduino IDE
3. Tools → Board → STM32 → Generic STM32F4 Series
4. Tools → Board part number → STM32F411CEUx (Black Pill)
5. Tools → Upload method → STLink
6. **Before first flash:** uncomment `#define CALIBRATION_MODE`, flash, run calibration, copy values, recomment, reflash

### ESP32-S3 (intelligence layer) — Flash second
1. Connect XIAO ESP32-S3 via USB-C
2. Open `aria_esp32_firmware.ino`
3. Tools → Board → ESP32 Arduino → XIAO_ESP32S3
4. Tools → Upload Speed → 921600
5. Flash

---

## WIRING DIAGRAM

```
STM32 Black Pill          AS5048A Encoder
─────────────            ───────────────
PA4 (CS)    ────────────  CS
PA5 (SCK)   ────────────  CLK
PA6 (MISO)  ────────────  MISO
PA7 (MOSI)  ────────────  MOSI
3.3V        ────────────  VCC
GND         ────────────  GND

STM32 Black Pill          HX711 + Load Cell
─────────────            ─────────────────
PB0         ────────────  DOUT
PB1         ────────────  SCK
3.3V        ────────────  VCC
GND         ────────────  GND
(Load cell 4 wires go to HX711 E+/E-/A+/A-)

STM32 Black Pill          Motor Driver (e.g. DRV8313)
─────────────            ───────────────────────────
PA8         ────────────  IN1 (Phase A PWM)
PA9         ────────────  IN2 (Phase B PWM)
PA10        ────────────  IN3 (Phase C PWM)
PB10        ────────────  EN (enable)
GND         ────────────  GND
(Motor phases: driver OUT1/2/3 → motor U/V/W)
(24V power supply → driver PVDD and GND)

STM32 Black Pill          ESP32-S3 XIAO Sense
─────────────            ───────────────────
PA2 (UART TX) ──────────  GPIO44 (RX)
PA3 (UART RX) ──────────  GPIO43 (TX)
GND         ────────────  GND
(Do NOT connect 3.3V — each board self-powers)

STM32 Black Pill          E-Stop Button
─────────────            ─────────────
PB12        ────────────  One leg
GND         ────────────  Other leg
(Internal pull-up enabled in firmware)
```

---

## PHASE BUILD ORDER

### Phase 1 — Mechanical only (do this first, no electronics)
Build Lead Solo design from renders:
- 200mm brake drum
- 600mm rope spool
- Centrifugal clutch
- 6061 aluminium housing
- Wall mount bracket
**Test:** Drop sandbag, verify catch works. Don't proceed until this is solid.

### Phase 2 — Add motor (no software yet)
Wire BLDC + gearbox to spool shaft via one-way bearing.
Flash STM32 in TENSION_HOLD mode only.
Run calibration routine.
**Test:** Motor maintains ~40N rope tension. Manual mode switching via serial.

### Phase 3 — Add voice (no camera yet)
Flash ESP32.
Run `aria_collect_audio.py` — record 60 clips per command in actual gym.
Train Edge Impulse model (see Edge Impulse section below).
Add generated library to ESP32 firmware.
**Test:** Yell commands, verify STM32 state transitions via serial monitor.

### Phase 4 — Add camera
Enable CV task in ESP32 firmware.
Calibrate `WALL_HEIGHT_M` and pixel threshold for your gym lighting.
**Test:** Verify climber detection and clip gesture prediction.

### Phase 5 — Full integration
Run all scenarios from Python simulator against real hardware.
Compare state transitions to simulator predictions.
Tune PID gains for smooth tension control.

---

## EDGE IMPULSE SETUP (for voice)

1. Create account: studio.edgeimpulse.com
2. New project → "ARIA-Wake-Word"
3. Collect data using `aria_collect_audio.py` → upload dataset/ folders
4. Create Impulse:
   - Input: Audio (16000Hz, 1000ms window, 500ms stride)
   - Processing: MFE (40 coefficients)
   - Learning: Classification (8 classes)
5. Train → target >95% accuracy
6. Deployment → Arduino Library → Download ZIP
7. Arduino IDE → Sketch → Include Library → Add .ZIP Library
8. In `aria_esp32_firmware.ino`: uncomment the Edge Impulse #include and inference code

---

## STM32 CONTACTS (from Grok research)

These engineers have direct SimpleFOC + STM32 experience. DM them on X:

**@__su888** — Built STM32G431 + SimpleFOC + tension control system (closest to your application)
**@kokensha_tech** — Custom STM32 BLDC driver PCBs with SimpleFOC
**@nimomono** — STM32G4 + SimpleFOC on humanoid robot actuators

Suggested DM:
> "Building a safety-critical rope tension controller: STM32F411 + SimpleFOC torque mode + HX711 load cell for a lead auto belay device. Saw your [project]. Would value 15 min of feedback on PID tuning for stable torque under sudden dynamic load (fall arrest scenario). Happy to share test data."

---

## PID TUNING GUIDE (when hardware arrives)

Start with these and tune in order:
1. Set Ki=0, Kd=0. Increase Kp until tension tracks setpoint but oscillates.
2. Back Kp off 30%. Add Ki slowly until steady-state error disappears.
3. Add small Kd if you see overshoot on sudden load changes.

Current starting values in firmware:
```
Kp = 0.08  (conservative)
Ki = 1.5
Kd = 0.0005
```
If tension oscillates: reduce Kp or increase LPF time constant.
If tension responds slowly: increase Kp or Ki.
If noisy: increase tensionLPF time constant (default 0.02s).

---

## FILES IN THIS PROJECT

| File | Purpose | Run on |
|------|---------|--------|
| `aria_simulator.py` | Full state machine simulator | Your laptop now |
| `aria_stm32_complete.cpp` | STM32 safety + motor layer | STM32 Black Pill |
| `aria_esp32_firmware.ino` | ESP32 voice + CV layer | XIAO ESP32-S3 |
| `aria_collect_audio.py` | Wake word dataset recorder | Your laptop |
| `ARIA_SETUP.md` | This file | Reference |
