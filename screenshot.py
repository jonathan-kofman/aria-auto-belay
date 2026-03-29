"""
screenshot.py — Save clipboard image and print the path for Claude.

Workflow:
  1. Win+Shift+S  (snip any region)
  2. python screenshot.py
  3. Paste the printed path into Claude
"""
import sys
import datetime
from pathlib import Path
from PIL import ImageGrab

OUT_DIR = Path(__file__).resolve().parent / "outputs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

img = ImageGrab.grabclipboard()

if img is None:
    print("No image in clipboard.")
    print("  1. Press Win+Shift+S and snip the region you want to share")
    print("  2. Run this script again")
    sys.exit(1)

ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = OUT_DIR / f"screenshot_{ts}.png"
img.save(out_path, "PNG")

print(f"\nSaved: {out_path}")
print(f"\nPaste into Claude:\n  {out_path}")
