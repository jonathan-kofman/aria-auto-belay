[&larr; Back to Table of Contents](./README.md) &middot; [Previous: Bill of Materials](./04-bom.md) &middot; [Next: The Firmware &rarr;](./06-the-firmware.md)

# The Build

## Before You Start

- [ ] All BOM items received and inspected (see [Chapter 4](./04-bom.md))
- [ ] CNC machined parts measured with caliper -- confirm critical dimensions match STEP files
- [ ] Ratchet ring teeth inspected for burrs or machining artifacts -- deburr if needed
- [ ] Bearings spin freely by hand
- [ ] STM32 and ESP32 boards power on via USB (test before soldering anything)
- [ ] 12V power supply tested with multimeter (confirm voltage and polarity)
- [ ] Structural beam behind climbing wall identified and marked for mounting holes
- [ ] All tools from the BOM tools list available at the bench
- [ ] Read [Chapter 9 (Safety)](./09-safety.md) completely before beginning

> **Warning:** ARIA is a safety-critical device. Do not skip inspection steps. A misaligned ratchet ring or loose bearing can cause a catastrophic failure under fall loads.

## Assembly Order

The build proceeds from the inside out: shaft and bearings first, then spool and braking mechanisms, then motor and drivetrain, then electronics, then housing closure, and finally wall mounting.

1. Shaft and bearing installation
2. Spool mounting
3. Ratchet ring and pawl installation
4. Brake drum and clutch assembly
5. Motor and gearbox mounting
6. Power-off brake installation
7. Electronics installation (STM32, ESP32, HX711, VESC)
8. Wiring harness
9. Housing closure
10. Wall mounting
11. External connections (rope port, LED strip, power)

---

## Step 1: Shaft and Bearing Installation

**Parts Needed:**
- [ ] Shaft (20 mm dia, 344 mm long)
- [ ] Deep groove bearings x2 (47.2 mm OD)
- [ ] Housing (one half or open side)
- [ ] Bearing retainer screws x4

**Instructions:**

1. Press bearings onto shaft ends. Bearing inner race should be a light press fit on the shaft. If loose, use retaining compound (Loctite 638).
2. Seat shaft + bearing assembly into housing bearing pockets. Bearing OD should sit in the pocket with bearing shoulder (55 mm OD, 3 mm height) registering against the housing face.
3. Secure bearing retainers. Torque to {e.g. spec per fastener size}.

**Verify:**
- [ ] Shaft spins freely with no perceptible play
- [ ] Bearings are fully seated (shoulder flush against housing)
- [ ] No binding or rough spots through full rotation

---

## Step 2: Spool Mounting

**Parts Needed:**
- [ ] Spool (600 mm dia)
- [ ] Spool retaining hardware (keyway or set screws, per design)

**Instructions:**

1. Slide spool onto shaft. Spool center should align to X=350 mm, Y=330 mm from housing origin.
2. Secure spool to shaft using keyway or set screws. Apply Loctite 242 to set screws.
3. Route rope through rope slot (30 x 80 mm) and anchor to spool core.

**Verify:**
- [ ] Spool is centered on shaft (no wobble)
- [ ] Spool rotates freely with shaft
- [ ] Rope pays out and retracts smoothly through rope slot
- [ ] No rope rubbing on housing walls

---

## Step 3: Ratchet Ring and Pawl Installation

**Parts Needed:**
- [ ] Ratchet ring (213 mm OD, 24 teeth, 21 mm thick)
- [ ] Catch pawls x2
- [ ] Pawl pivot pins x2
- [ ] Pawl return springs x2

**Instructions:**

1. Mount ratchet ring onto spool shaft. The ring should be keyed or pinned to the spool so it rotates with the spool.
2. Install pawl pivot pins in the housing at the correct engagement position. Pawl tip width is 6 mm, engagement depth is 3 mm.
3. Mount pawls on pivot pins. Confirm pawls swing freely.
4. Install return springs. Springs should bias pawls toward engagement (into the teeth), not away.

**Verify:**
- [ ] Ratchet ring seats in ratchet pocket (213 mm dia, 21 mm depth)
- [ ] Pawls engage teeth when spool is rotated in the payout (backdriving) direction
- [ ] Pawls lift clear of teeth when spool rotates in the take-up direction
- [ ] Both pawls engage independently (test each alone)
- [ ] No binding or interference between pawls and ring

> **Warning:** The ratchet ring is the primary fall arrest mechanism. Test engagement thoroughly. Every tooth must be reachable by at least one pawl. Rotate the spool a full revolution and verify engagement at every tooth.

---

## Step 4: Brake Drum and Clutch Assembly

**Parts Needed:**
- [ ] Brake drum (200 mm dia)
- [ ] Centrifugal clutch components
- [ ] Cam collar

**Instructions:**

1. Mount brake drum on shaft (opposite end from ratchet ring, or concentric per design).
2. Install centrifugal clutch weights and springs inside the drum.
3. Install cam collar if applicable.

**Verify:**
- [ ] Drum is concentric and true (no runout)
- [ ] Clutch engages when shaft is spun rapidly by hand
- [ ] Clutch releases cleanly at low speed

---

## Step 5: Motor and Gearbox Mounting

**Parts Needed:**
- [ ] BLDC motor
- [ ] Planetary gearbox (30:1)
- [ ] Motor mount bolts x4
- [ ] Coupling (motor shaft to spool shaft or gearbox output)

**Instructions:**

1. Attach planetary gearbox to motor. Confirm gear ratio marking (30:1).
2. Mount motor + gearbox assembly to housing. Use all four mounting bolts with Loctite 242.
3. Connect gearbox output shaft to spool drive shaft via coupling.

**Verify:**
- [ ] Motor spins freely when powered (test with bench supply before wiring VESC)
- [ ] No misalignment between gearbox output and spool shaft
- [ ] All motor mount bolts torqued and threadlocked

---

## Step 6: Power-Off Brake Installation

**Parts Needed:**
- [ ] Brake spring
- [ ] Brake pads / shoes
- [ ] Brake solenoid (12V)
- [ ] Solenoid mounting hardware

**Instructions:**

1. Install brake shoes against brake drum.
2. Install brake spring. Spring should press shoes against drum when solenoid is de-energized (power off = brake engaged).
3. Mount solenoid. When energized (12V), solenoid pulls brake shoes away from drum.
4. Wire solenoid leads (leave loose for now -- will connect in wiring step).

**Verify:**
- [ ] With solenoid unpowered: brake is engaged, shaft cannot rotate by hand
- [ ] With 12V applied to solenoid: brake releases, shaft rotates freely
- [ ] Brake engages instantly when power is removed (no sticking)

---

## Step 7: Electronics Installation

**Parts Needed:**
- [ ] STM32 dev board
- [ ] ESP32 dev board
- [ ] VESC motor controller
- [ ] HX711 breakout + load cell
- [ ] PCB standoffs x8
- [ ] Camera module
- [ ] Microphone module

**Instructions:**

1. Mount STM32 and ESP32 boards on standoffs inside housing. Keep boards away from motor and brake (heat + vibration).
2. Mount VESC near motor. Ensure adequate ventilation.
3. Mount HX711 breakout. Connect to load cell (inline with rope or on tension arm).
4. Mount camera module with line of sight to climbing wall through rope port or dedicated window.
5. Mount microphone. Position for best voice pickup from climbing side of wall.

**Verify:**
- [ ] All boards power on via USB
- [ ] No boards or wires touching metal housing (insulate or use standoffs)
- [ ] Camera has clear field of view
- [ ] Microphone is not blocked or covered

---

## Step 8: Wiring Harness

**Parts Needed:**
- [ ] Wire harness (22 AWG silicone)
- [ ] JST connectors
- [ ] Voltage regulators (12V to 3.3V, 12V to 5V)
- [ ] MOSFET driver board
- [ ] Flyback diode
- [ ] Wire management clips (3D printed)

**Instructions:**

1. Wire 12V barrel jack to main power bus.
2. Wire voltage regulators: 12V to 5V (ESP32, LED strip), 12V to 3.3V (STM32, HX711).
3. Wire VESC: 12V power in, 3-phase out to motor, UART TX/RX to STM32.
4. Wire HX711: data + clock to STM32 GPIO.
5. Wire UART bridge: STM32 TX to ESP32 RX, STM32 RX to ESP32 TX. 115200 baud.
6. Wire brake solenoid: STM32 GPIO to MOSFET driver, MOSFET to solenoid, flyback diode across solenoid coil.
7. Wire LED strip: data to ESP32 GPIO, 5V power.
8. Wire camera and microphone to ESP32.
9. Route all wires through 3D-printed cable clips. Keep high-current wires (motor, solenoid) away from signal wires (UART, I2C).

**Verify:**
- [ ] Continuity check on all connections with multimeter
- [ ] No shorts between power and ground
- [ ] UART TX/RX wires are crossed (TX to RX, not TX to TX)
- [ ] Flyback diode polarity is correct (cathode to 12V, anode to ground side of solenoid)
- [ ] All JST connectors click and seat fully

---

## Step 9: Housing Closure

**Instructions:**

1. Do a final inspection of all internal components before closing.
2. Attach housing panels / cover. Apply Loctite to structural screws.
3. Route cables through cable glands (PG11 for power cable, smaller for signal cables).

**Verify:**
- [ ] No wires pinched between housing panels
- [ ] Rope slot is clear and unobstructed
- [ ] Cable glands are snug (water ingress protection for drain hole area)
- [ ] Housing is rigid with no rattle

---

## Step 10: Wall Mounting

**Parts Needed:**
- [ ] Wall mount bolts (M10 x 80 mm)
- [ ] Mounting boss alignment tools (level)

**Instructions:**

1. Mark mounting holes on structural beam. Use housing mounting bosses (30 mm dia, 60 mm inset from edge) as a template.
2. Drill pilot holes into beam.
3. Lift housing into position. This is a two-person job -- the housing is heavy (aluminum, 700 x 680 x 344 mm).
4. Bolt through mounting bosses (10.5 mm bore) into structural beam. Torque to specification.
5. Level check. The spool axis must be perpendicular to the wall.

**Verify:**
- [ ] All four mounting bolts are torqued
- [ ] Housing does not rock or shift when pushed
- [ ] Level reads true on top and side of housing
- [ ] Rope port aligns with climbing wall opening

---

## Step 11: External Connections

**Instructions:**

1. Route rope through wall panel and into rope port (30 x 80 mm slot).
2. Mount LED strip on wall face above or beside rope port.
3. Connect 12V power supply to barrel jack.
4. If using iPad HMI: mount iPad bracket on wall face.

**Verify:**
- [ ] Rope pulls smoothly through rope port with no snagging
- [ ] LED strip illuminates on power-on
- [ ] System powers up (both MCU boards alive via serial)

> **Tip:** After wall mounting, proceed immediately to [Chapter 6 (Firmware)](./06-the-firmware.md) for first flash, then [Chapter 7 (Calibration)](./07-calibration.md) for sensor verification before any rope-loaded testing.

[Next: The Firmware &rarr;](./06-the-firmware.md)
