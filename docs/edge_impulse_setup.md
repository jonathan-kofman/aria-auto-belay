# ARIA — Edge Impulse Wake Word Setup
## Complete Training Guide for 6 Climbing Commands

---

## Quick start — Record audio (Windows)

1. **Start recording:** Double-click **`RECORD_EDGE_IMPULSE_AUDIO.bat`** in the project root (or run it from a terminal in the project folder).
2. The script will install `sounddevice`, `soundfile`, and `numpy` if needed, then prompt you to record each class.
3. **Target:** 60 clips per class. For each clip you press ENTER, then say the word (or record noise/unknown as instructed).
4. Clips are saved under **`dataset/`** (e.g. `dataset/take/`, `dataset/slack/`, …).
5. When done, continue with **Step 1** below (create Edge Impulse project) and **Step 3** (upload the `dataset/` folders).

To record only one class:  
`python tools/aria_collect_audio.py take`  
(or `slack`, `lower`, `up`, `watch_me`, `rest`, `noise`, `unknown`).

---

## Overview

This guide takes you from zero to a deployed wake word model on the XIAO ESP32-S3 Sense
that recognizes: **take, slack, lower, up, watch me, rest**

Total time: ~3-4 hours (mostly recording audio)
Cost: Free (Edge Impulse free tier supports this project size)

---

## Step 1 — Create Edge Impulse Project

1. Go to [studio.edgeimpulse.com](https://studio.edgeimpulse.com)
2. Sign up / log in
3. Create new project → name it **"ARIA-Wake-Word"**
4. Project type: **Audio (Keyword Spotting)**

---

## Step 2 — Record Dataset

Run the collection script first:

```bash
pip install sounddevice soundfile numpy
python3 tools/aria_collect_audio.py
```

**Target: 60 clips per class, recorded in a real gym environment**

### Classes to record:

| Class | What to say | Notes |
|-------|------------|-------|
| `take` | "Take" | Vary volume, urgency, distance from mic |
| `slack` | "Slack" | Say it naturally, how you'd say it climbing |
| `lower` | "Lower" | Try both casual and urgent versions |
| `up` | "Up" | Short word — be clear, vary emphasis |
| `watch_me` | "Watch me" | Two-word command — say as one phrase |
| `rest` | "Rest" | Try whispering and yelling versions |
| `noise` | (silence) | Record gym ambient noise — music, chalk, conversation |
| `unknown` | Random words | hello, stop, yes, go, climb, belay, rope, send |

### Tips for gym recording:
- Record near the wall where device will be mounted
- Include background music (most gyms have it)
- Have friends say the words too — speaker diversity helps
- Record at different distances: 1m, 2m, 4m from mic
- Record while breathing hard (post-climb)
- The `noise` class should be pure background — no speech

---

## Step 3 — Upload to Edge Impulse

### Option A — Web upload (simple):
1. Edge Impulse → Data acquisition → Upload data
2. For each class folder: select all WAVs, set label = folder name
3. Split: 80% training / 20% test (Edge Impulse does this automatically)

### Option B — CLI upload (faster for large datasets):
```bash
npm install -g edge-impulse-cli
edge-impulse-uploader --api-key YOUR_KEY dataset/take/*.wav --label take
edge-impulse-uploader --api-key YOUR_KEY dataset/slack/*.wav --label slack
edge-impulse-uploader --api-key YOUR_KEY dataset/lower/*.wav --label lower
edge-impulse-uploader --api-key YOUR_KEY dataset/up/*.wav --label up
edge-impulse-uploader --api-key YOUR_KEY dataset/watch_me/*.wav --label watch_me
edge-impulse-uploader --api-key YOUR_KEY dataset/rest/*.wav --label rest
edge-impulse-uploader --api-key YOUR_KEY dataset/noise/*.wav --label noise
edge-impulse-uploader --api-key YOUR_KEY dataset/unknown/*.wav --label unknown
```

Find your API key: Edge Impulse → project → Dashboard → Keys

---

## Step 4 — Design Impulse

Go to: **Create impulse**

### Input block:
- Window size: **1000ms**
- Window increase: **500ms**
- Frequency: **16000 Hz**
- Zero-pad data: **ON**

### Processing block:
- Click **Add a processing block**
- Select **MFE (Mel Filterbank Energy)**
- Parameters to use:
  - Frame length: 0.02 (20ms)
  - Frame stride: 0.01 (10ms)
  - Filter number: 40
  - FFT length: 256
  - Low frequency: 0
  - High frequency: 0 (= Nyquist)
  - Noise floor: -52 dB
  - Noise scale: 0 (no scaling)

### Learning block:
- Click **Add a learning block**
- Select **Classification**
- Leave at defaults for now

Click **Save impulse**

---

## Step 5 — Configure MFE Features

1. Go to: **MFE** (under Impulse design)
2. Click **Save parameters**
3. Click **Generate features**
4. Wait for processing (2-5 minutes)
5. Check the **Feature explorer** — you should see clear clusters for each word

**What to look for:**
- "take" cluster should be distinct from "slack"
- "watch_me" (2 syllables) should be separate from single-syllable words
- "noise" and "unknown" should overlap somewhat (that's fine)

If clusters are mixed: add more training data or adjust MFE parameters

---

## Step 6 — Train the Model

Go to: **Classifier**

### Recommended architecture for ESP32-S3:

```
Input layer (MFE features)
    ↓
Reshape (1D → 2D for conv)
    ↓
Conv1D (8 filters, kernel 3, ReLU)
    ↓
MaxPooling1D (pool size 2)
    ↓
Conv1D (16 filters, kernel 3, ReLU)
    ↓
MaxPooling1D (pool size 2)
    ↓
Flatten
    ↓
Dense (64, ReLU)
    ↓
Dropout (0.25)
    ↓
Dense (8, Softmax) ← 8 classes
```

### Training settings:
- Number of training cycles: **100**
- Learning rate: **0.005**
- Validation set size: **20%**
- Data augmentation: **ON**
  - Add noise: **0.05**
  - Time stretch factor range: **0.9 - 1.1**

Click **Start training**

### Target metrics:
- Overall accuracy: **>95%**
- Per-class accuracy: **>90%** for all command words
- Confusion between noise/unknown is acceptable
- Zero confusion between "take" and any other command word (safety critical)

If accuracy is below target: collect more data for underperforming classes

---

## Step 7 — Evaluate on Device

Go to: **Model testing** → **Classify all**

Check the confusion matrix. Pay special attention to:
- False positive rate for "take" (should be <2%)
- False negative rate for "take" (should be <5%)
- "watch_me" accuracy (two-word commands are harder)

Go to: **Live classification**
- Connect your XIAO ESP32-S3 via USB
- Click **Connect to development board**
- Say each command and verify classification

---

## Step 8 — Deploy to ESP32-S3

Go to: **Deployment**

1. Select: **Arduino library**
2. Select optimization: **Quantized (int8)** — smaller and faster on ESP32-S3
3. Click **Build**
4. Download the ZIP file

### Add to Arduino IDE:
1. Arduino IDE → Sketch → Include Library → Add .ZIP Library
2. Select the downloaded ZIP
3. Library name will be something like: `aria-wake-word_inferencing`

---

## Step 9 — Integrate with ARIA ESP32 Firmware

In `firmware/esp32/aria_esp32_firmware.ino`, uncomment and update:

```cpp
// Replace this line:
// #include "aria-wake-word_inferencing.h"
// With your actual library name:
#include "aria-wake-word_inferencing.h"  // ← your exact library name
```

Then in the `voice_task()` function, replace the placeholder with:

```cpp
void voice_task(void* param) {
  // Edge Impulse continuous audio classification
  // This runs the microphone capture + inference loop
  
  if (microphone_inference_start(EI_CLASSIFIER_SLICE_SIZE) != EI_IMPULSE_OK) {
    Serial.println("Voice: mic init failed");
    vTaskDelete(NULL);
    return;
  }
  
  while (true) {
    // Record one window of audio
    bool m = microphone_inference_record();
    if (!m) {
      vTaskDelay(pdMS_TO_TICKS(10));
      continue;
    }
    
    // Run classifier
    signal_t signal;
    microphone_inference_signal_get_data(0, 0, &signal);
    
    ei_impulse_result_t result;
    EI_IMPULSE_ERROR r = run_classifier_continuous(&signal, &result, false);
    
    if (r != EI_IMPULSE_OK) {
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    
    // Find highest confidence prediction
    float best_conf = 0.0f;
    int   best_idx  = -1;
    for (int i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
      if (result.classification[i].value > best_conf) {
        best_conf = result.classification[i].value;
        best_idx  = i;
      }
    }
    
    // Send to STM32 if above threshold
    if (best_conf >= VOICE_CONFIDENCE_MIN && best_idx >= 0) {
      const char* label = ei_classifier_inferencing_categories[best_idx];
      
      // Map label to command ID
      for (int j = 0; j < LABEL_MAP_LEN; j++) {
        if (strcmp(label, LABEL_MAP[j].label) == 0) {
          uart_send_voice(LABEL_MAP[j].cmd, best_conf);
          Serial.printf("[VOICE] %s (%.2f)\n", label, best_conf);
          break;
        }
      }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}
```

Also add these microphone functions (provided by Edge Impulse library):

```cpp
// Add before void setup():
static bool microphone_inference_start(uint32_t n_samples);
static bool microphone_inference_record(void);
static int  microphone_inference_signal_get_data(size_t, size_t, signal_t*);
static void microphone_inference_end(void);
// Implementation is in the Edge Impulse library — it handles PDM mic on XIAO ESP32-S3
```

---

## Confidence Threshold Reference

The ARIA firmware uses **0.85** as the minimum confidence to act on a voice command.
This is a safety choice — at 85% confidence, false trigger rate is very low.

You can tune this in `aria_esp32_firmware.ino`:
```cpp
#define VOICE_CONFIDENCE_MIN    0.85f   // raise to reduce false triggers
                                        // lower to improve responsiveness
```

For "take" specifically, you want high confidence because it locks the rope.
For "slack" the cost of a false trigger is lower (just feeds extra rope).

---

## Troubleshooting

**Low accuracy on "watch_me":**
Two-word commands are harder. Record more samples, try saying it faster/slower.
Alternative: train "watch" as the trigger word and ignore "me".

**High false trigger rate for "take":**
Raise `VOICE_CONFIDENCE_MIN` to 0.90. Add more "unknown" samples that sound like "take"
(rake, cake, lake, fake, bake).

**Model too large for ESP32-S3:**
Use quantized (int8) deployment — it's already selected above.
If still too large, reduce the Conv1D filter counts (8 → 4, 16 → 8).

**Gym background noise causing false triggers:**
Add more gym-specific noise samples. Record during peak hours.
Consider training a two-stage model: first detect silence vs. speech, then classify.

**"up" being confused with background sounds:**
Short words are harder. Record "up" with very clear pronunciation.
Add more unknown samples that are single syllables.

---

## Dataset Checklist

Before training, verify you have:

- [ ] 60+ clips of each command word
- [ ] 60+ clips of gym ambient noise (no speech)
- [ ] 60+ clips of unknown words
- [ ] Clips from at least 3 different speakers
- [ ] Clips at multiple distances from mic (1m, 2m, 4m)
- [ ] Clips with background music playing
- [ ] Clips while breathing hard
- [ ] 80/20 train/test split confirmed in Edge Impulse

---

## Expected Model Size on ESP32-S3

- Model size: ~15-25 KB (int8 quantized)
- RAM usage during inference: ~8-12 KB
- Inference time on ESP32-S3: ~15-30ms per window
- ESP32-S3 PSRAM: 8MB — plenty of headroom

The ESP32-S3's AI accelerator (vector extensions) handles this model comfortably
at 10+ inferences per second, well within the 500ms voice confirmation window.
