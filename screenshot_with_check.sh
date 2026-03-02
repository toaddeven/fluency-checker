#!/bin/bash
# Check if screen has content before taking screenshot

BRIGHTNESS=$(python3 -c "
import subprocess
import os
import sys
import tempfile
from PIL import Image

with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    tmp_path = f.name

result = subprocess.run(
    ['/usr/sbin/screencapture', '-x', '-D1', tmp_path],
    capture_output=True
)
if result.returncode != 0:
    print('100')
    sys.exit(0)

img = Image.open(tmp_path)
img_gray = img.convert('L')
pixels = list(img_gray.getdata())
avg_brightness = sum(pixels) / len(pixels)
print(f'{avg_brightness}')
os.unlink(tmp_path)
" 2>/dev/null)

echo "Screen brightness: $BRIGHTNESS"

# Use awk for float comparison
SKIP=$(echo "$BRIGHTNESS < 15" | bc -l 2>/dev/null || echo "0")

if [ "$SKIP" = "1" ]; then
    echo "Screen is black, skipping screenshot"
    exit 1
fi

# Take actual screenshot
python3 /Users/daisy/.agents/skills/screenshot/scripts/take_screenshot.py
