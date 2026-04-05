[&larr; Back to Table of Contents](./README.md) &middot; [Next: The Why &rarr;](./01-the-why.md)

# Elevator Pitch

## What Is It?

ARIA (Autonomous Rope Intelligence Architecture) is a wall-mounted auto-belay device for lead climbing. It replaces a human belayer with an AI-driven electromechanical system that manages rope tension, detects voice commands, tracks the climber with computer vision, and arrests falls through redundant mechanical braking.

The device mounts behind the climbing wall panel. Only a flush rope port, LED status strip, and optional iPad HMI are visible from the climbing side. Behind the wall, ARIA handles everything: paying out rope as the climber ascends, taking in slack on command, catching falls, and lowering the climber to the ground.

## Who Is It For?

- **Climbing gyms with lead walls** that want to offer lead climbing without requiring a human belayer for every climber
- **Route setters and gym operators** who need a reliable, low-maintenance auto-belay that works on lead routes (not just top-rope)
- **Solo climbers** who want to train on lead without a partner

## What Does It Replace?

A human belayer. Today, lead climbing requires a trained partner holding the rope. Top-rope auto-belays exist, but no certified auto-belay handles the dynamic rope management, slack payout, and fall arrest required for lead climbing. ARIA is the first device designed to do this.

## Key Specs

| Spec | Value |
|---|---|
| Housing dimensions | 700 x 680 x 344 mm |
| Housing material | 6061 aluminum, CNC machined |
| Rope spool diameter | 600 mm |
| Brake drum diameter | 200 mm |
| Motor type | BLDC with 30:1 planetary gearbox |
| Safety controller | STM32 (independent safety layer) |
| Intelligence controller | ESP32 (voice, CV, BLE) |
| Tension sensor | HX711 load cell |
| Fall arrest | Ratchet ring + centrifugal clutch + power-off brake |
| Mounting | Behind-wall to structural beam |
| Target tension (climbing) | 40 N |
| Fall detection threshold | 400 N + 2.0 m/s rope speed |
| Voice recognition | Edge Impulse on-device |
| Companion app | React Native / Expo (Android + iOS) |
| CAD pipeline | ARIA-OS (AI-driven, CadQuery + LLM + CEM physics) |

## One-Liner

ARIA is a wall-mounted AI auto-belay that lets climbers lead climb without a human belayer, using voice commands, computer vision, and triple-redundant mechanical fail-safes.

[Next: The Why &rarr;](./01-the-why.md)
