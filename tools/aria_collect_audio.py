#!/usr/bin/env python3
"""
ARIA Wake Word Dataset Collector
Collects labeled audio samples for Edge Impulse training.

Usage:
  pip install sounddevice soundfile numpy
  python3 aria_collect_audio.py

Records 1-second clips of each command word and saves them
in the correct folder structure for Edge Impulse upload.

Folder structure created:
  dataset/
    take/
    slack/
    lower/
    up/
    watch_me/
    rest/
    noise/      ← background gym noise (no speech)
    unknown/    ← other words, false triggers

EDGE IMPULSE UPLOAD:
  1. Go to studio.edgeimpulse.com → your project → Data acquisition
  2. Upload → Select folder → choose dataset/take/, etc.
  3. Set label = folder name
  4. Repeat for each class
  OR use Edge Impulse CLI:
    npm install -g edge-impulse-cli
    edge-impulse-uploader --api-key <key> dataset/take/*.wav
"""

import sounddevice as sd
import soundfile  as sf
import numpy      as np
import os
import time
import sys

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

SAMPLE_RATE   = 16000   # Hz — required by Edge Impulse KWS models
DURATION_S    = 1.0     # seconds per clip
CHANNELS      = 1       # mono
SAMPLES_GOAL  = 60      # target clips per class (50 minimum, 60+ better)
OUTPUT_DIR    = "dataset"

COMMANDS = [
    "take",
    "slack",
    "lower",
    "up",
    "watch_me",
    "rest",
    "noise",    # background only — don't speak
    "unknown",  # random words: hello, go, stop, yes, no
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def ensure_dirs():
    for cmd in COMMANDS:
        os.makedirs(os.path.join(OUTPUT_DIR, cmd), exist_ok=True)

def count_existing(label):
    path = os.path.join(OUTPUT_DIR, label)
    if not os.path.exists(path):
        return 0
    return len([f for f in os.listdir(path) if f.endswith(".wav")])

def record_clip():
    audio = sd.rec(
        int(DURATION_S * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32"
    )
    sd.wait()
    return audio.flatten()

def save_clip(audio, label, idx):
    filename = os.path.join(OUTPUT_DIR, label, f"{label}_{idx:04d}.wav")
    sf.write(filename, audio, SAMPLE_RATE)
    return filename

def normalize_audio(audio):
    """Normalize to -1..1 range"""
    peak = np.max(np.abs(audio))
    if peak > 0:
        return audio / peak
    return audio

def check_audio_level(audio, min_rms=0.01):
    """Returns True if clip has enough signal (not silence)"""
    rms = np.sqrt(np.mean(audio**2))
    return rms > min_rms

def list_devices():
    print("\nAvailable audio devices:")
    print(sd.query_devices())
    print(f"\nDefault input device: {sd.default.device[0]}")

# ─────────────────────────────────────────────
# COLLECTION LOOP
# ─────────────────────────────────────────────

def collect_class(label, goal=SAMPLES_GOAL):
    existing = count_existing(label)
    print(f"\n{'='*50}")
    print(f"  Class: '{label}'")
    print(f"  Existing: {existing} / {goal}")
    print(f"{'='*50}")

    if label == "noise":
        print("  -> Record BACKGROUND GYM NOISE only. Do NOT speak.")
        print("  -> Hold mic in gym, let ambient sound record.")
    elif label == "unknown":
        print("  -> Say RANDOM words (not your commands).")
        print("  -> Examples: hello, stop, yes, no, go, climb, belay, rope")
    else:
        print(f"  -> Say the word: '{label.upper().replace('_',' ')}'")
        print(f"  -> Vary your volume, distance, and tone each clip.")
        print(f"  -> Try saying it with different urgency (calm, urgent, yelling)")

    print(f"\n  Press ENTER to start recording each clip.")
    print(f"  Press Q + ENTER to skip to next class.")
    print(f"  Press X + ENTER to quit.\n")

    idx = existing
    while idx < goal:
        remaining = goal - idx
        inp = input(f"  [{idx}/{goal}] Press ENTER to record (Q=skip, X=quit): ").strip().lower()

        if inp == 'x':
            print("Exiting.")
            sys.exit(0)
        if inp == 'q':
            print(f"  Skipping '{label}'")
            break

        print(f"  >> Recording {DURATION_S}s... SAY IT NOW")
        audio = record_clip()
        audio = normalize_audio(audio)

        # Quality check (skip for noise class)
        if label != "noise" and not check_audio_level(audio):
            print(f"  [!] Too quiet - clip rejected. Speak closer to mic.\n")
            continue

        path = save_clip(audio, label, idx)
        idx += 1
        print(f"  [OK] Saved: {os.path.basename(path)} ({remaining-1} remaining)\n")

    print(f"  [OK] '{label}' complete: {idx} clips")

# ─────────────────────────────────────────────
# PROGRESS REPORT
# ─────────────────────────────────────────────

def print_progress():
    print(f"\n{'='*50}")
    print(f"  DATASET PROGRESS")
    print(f"{'='*50}")
    total = 0
    for cmd in COMMANDS:
        n = count_existing(cmd)
        total += n
        bar = "#" * (n // 3) + "-" * ((SAMPLES_GOAL - n) // 3)
        status = "OK" if n >= SAMPLES_GOAL else f"{n}/{SAMPLES_GOAL}"
        print(f"  {cmd:<12} {bar} {status}")
    print(f"{'-'*50}")
    print(f"  Total clips: {total}")
    print(f"{'='*50}\n")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n+==================================================+")
    print("|  ARIA Wake Word Dataset Collector             |")
    print("|  Target: Edge Impulse KWS training            |")
    print("+==================================================+\n")

    list_devices()
    print(f"\nRecording at {SAMPLE_RATE}Hz, {DURATION_S}s clips.")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}/\n")

    ensure_dirs()

    # Option: collect specific class
    if len(sys.argv) > 1:
        label = sys.argv[1].lower()
        if label in COMMANDS:
            print_progress()
            collect_class(label)
            print_progress()
            return
        else:
            print(f"Unknown class '{label}'. Valid: {COMMANDS}")
            sys.exit(1)

    # Full collection run
    print_progress()

    for cmd in COMMANDS:
        existing = count_existing(cmd)
        if existing >= SAMPLES_GOAL:
            print(f"  [OK] '{cmd}' already complete ({existing} clips) - skipping")
            continue
        collect_class(cmd)

    print_progress()
    print("\n[OK] Dataset collection complete!")
    print("\nNEXT STEPS:")
    print("  1. Upload dataset/ folders to studio.edgeimpulse.com")
    print("  2. Create impulse: Audio → MFE (40 coefficients, 1s window)")
    print("  3. Train CNN classifier")
    print("  4. Deploy → Arduino Library → Download ZIP")
    print("  5. Add ZIP to Arduino IDE → integrate into aria_esp32_firmware.ino")

if __name__ == "__main__":
    main()
