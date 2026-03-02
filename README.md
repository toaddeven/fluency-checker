# Fluency Checker

macOS screen quality detection tool - detects stuttering, lag, black screen, and flash issues.

## Features

- **Black Screen Detection**: Detects when screen is black/off/locked
- **Freeze Detection**: Detects screen freezes (no motion)
- **Flash Detection**: Detects sudden brightness changes
- **Stutter Detection**: Detects irregular motion patterns (jank)

## Requirements

```bash
pip3 install numpy opencv-python pillow
```

## Usage

```bash
# Run detection for 30 seconds
python3 detector.py

# Import as module
from detector import ScreenDetector

detector = ScreenDetector()
results = detector.analyze(duration=60, interval=0.5)
print(results)
```

## Parameters

- `threshold_brightness`: Minimum brightness to consider screen active (default: 15)
- `threshold_motion`: Minimum motion to consider screen updating (default: 0.02)
- `freeze_frames`: Number of consecutive frames with no motion to detect freeze (default: 5)

## How It Works

1. Captures screen frames at regular intervals
2. Analyzes brightness and motion between frames
3. Detects anomalies:
   - Black screen: Average brightness < threshold
   - Freeze: No motion between consecutive frames
   - Flash: Sudden brightness change > 100
   - Stutter: Inconsistent motion patterns

## License

MIT
