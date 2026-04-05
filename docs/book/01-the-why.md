[&larr; Back to Table of Contents](./README.md) &middot; [Previous: Elevator Pitch](./00-elevator-pitch.md) &middot; [Next: The Design &rarr;](./02-the-design.md)

# The Why

## The Problem

Lead climbing requires a human belayer. The belayer must be trained, attentive, and physically present for the entire climb. This creates three problems:

1. **Access**: Solo climbers cannot lead climb. Gym members without a regular partner are locked out of lead walls.
2. **Staffing**: Gyms cannot offer lead climbing without either requiring buddy systems or employing dedicated belayers. Both cost money and limit capacity.
3. **Safety**: Human belayers make mistakes. Distraction, fatigue, and inexperience cause short-roping, slack falls, and dropped climbers every year.

Top-rope auto-belays (TruBlue, Perfect Descent) solve none of these problems. They only work when the rope runs straight up from the climber. Lead climbing requires dynamic slack management: paying out rope as the climber clips, taking in slack between clips, and catching falls with a controlled deceleration.

## What Exists Already

| Alternative | Cost | Gets Right | Falls Short |
|---|---|---|---|
| Human belayer | $0 (partner) or $25-40/hr (hired) | Dynamic rope management, judgment | Requires a second person; human error |
| TruBlue auto-belay | ~$4,000 | Reliable top-rope retraction | Top-rope only; no lead climbing capability |
| Perfect Descent | ~$3,500 | Compact, magnetic braking | Top-rope only; fixed retraction speed |
| TRUBLUE iQ+ | ~$5,500 | Speed monitoring, usage logging | Still top-rope only; no slack payout |
| Edelrid OHM | ~$150 | Adds friction for weight mismatch | Requires a human belayer; passive device |

## The Gap

No product on the market handles lead climbing without a human belayer. The fundamental challenge is that lead climbing requires the rope system to do four things that top-rope auto-belays cannot do:

1. **Pay out slack** as the climber moves above their last clip
2. **Take in slack** when the climber clips or requests it by voice
3. **Detect falls** and arrest them with controlled deceleration (not a hard stop)
4. **Lower the climber** smoothly to the ground after the climb

These four operations require active motor control, real-time tension sensing, and situational awareness (voice + vision). No passive mechanical device can do all four.

## Why Build It Now?

Three technologies matured in 2025-2026 that make ARIA possible:

1. **On-device ML inference**: Edge Impulse and TensorFlow Lite run voice classification and object detection on an ESP32 with sub-100ms latency. ARIA uses voice recognition ("take", "slack", "lower") and CV-based clip detection without cloud dependency.
2. **BLDC motor control libraries**: SimpleFOC provides field-oriented control for brushless motors on STM32 at the hobbyist price point. Combined with a planetary gearbox, this gives ARIA the torque and precision to manage rope tension in real time.
3. **AI-driven CAD pipelines**: ARIA-OS (the software side of this project) generates validated, machinable STEP files from natural language descriptions. Every mechanical part in ARIA is designed and iterated through this pipeline, collapsing the traditional CAD bottleneck from days to seconds.

The climbing gym market is also growing (800+ gyms in the US, ~15% annual growth). Lead climbing is the premium offering at most gyms, but capacity is limited by belayer availability. ARIA turns every lead wall into a self-service station.

[Next: The Design &rarr;](./02-the-design.md)
