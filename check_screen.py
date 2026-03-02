#!/usr/bin/env python3
"""Check if screen has content before taking screenshot."""
import subprocess
import os
import sys
import tempfile
from PIL import Image

def check_screen_brightness():
    """Take a small sample and check if screen is not black."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        tmp_path = f.name
    
    try:
        # Take screenshot of a small region (or first display)
        result = subprocess.run(
            ['/usr/sbin/screencapture', '-x', '-D1', tmp_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return True  # Assume screen has content if capture fails
        
        # Check brightness
        img = Image.open(tmp_path)
        img = img.convert('L')
        pixels = list(img.getdata())
        avg_brightness = sum(pixels) / len(pixels)
        
        print(f"Screen brightness: {avg_brightness}", file=sys.stderr)
        
        # If brightness is very low, screen is likely black/lock screen
        return avg_brightness >= 15
        
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

if __name__ == '__main__':
    has_content = check_screen_brightness()
    if has_content:
        print('TAKE_SCREENSHOT')
        sys.exit(0)
    else:
        print('SKIP_SCREENSHOT')
        sys.exit(1)
