# Screen Brightness Checker

Detect if screen is black/locked before taking screenshots on macOS.

## Usage

```bash
# Check if screen has content
python3 check_screen.py

# Or use the shell script
bash screenshot_with_check.sh
``"

## How it works

1. Takes a small screenshot using ` screencapture`
2. Converts to grayscale and calculates average brightness
3. If brightness < 15, screen is considered black/locked
4. Returns exit code 0 (has content) or 1 (black)
