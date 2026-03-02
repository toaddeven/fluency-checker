# Fluency Checker

macOS screen quality detection tool - detects stuttering, lag, black screen, flash, and frame drops in screen recordings.

## Features

- **Frame Drop Detection**: Detects missing frames by analyzing motion discontinuity
- **Black Screen Detection**: Detects dark/black frames
- **Freeze Detection**: Detects frozen frames (identical consecutive frames)
- **Flash Detection**: Detects sudden brightness changes
- **Stutter Detection**: Detects irregular frame timing (jank)

## Requirements

```bash
pip3 install numpy opencv-python pillow
brew install ffmpeg
```

## Usage

### Analyze a video file

```bash
# Basic usage
python3 video_analyzer.py /path/to/recording.mp4

# With custom thresholds
python3 video_analyzer.py video.mp4 --brightness 15 --flash 60
```

### Real-time screen detection

```bash
python3 detector.py
```

## Output Example

```
Video: test.mp4
Resolution: 1920x1080, FPS: 60.0, Total frames: 1800
------------------------------------------------------------

============================================================
VIDEO FLUENCY ANALYSIS REPORT
============================================================

📊 Summary:
   Total issues found: 5
   🟥 Frame drops: 2
   ⬛ Black screens: 1
   ❄️  Freezes: 0
   ⚡ Flashes: 2
   🔀 Stutters: 0

📝 Detailed Issues:

   [1] BLACK_SCREEN
       Time: 5.23s (Frame 314)
       Brightness: 12.5

   [2] FLASH
       Time: 8.45s (Frame 507)
       Brightness change: 125.3

   [3] FRAME_DROP
       Time: 12.10s (Frame 726)
       Confidence: 0.85

   [4] FLASH
       Time: 15.67s (Frame 940)
       Brightness change: 98.2

   [5] FRAME_DROP
       Time: 20.33s (Frame 1220)
       Confidence: 0.78
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--brightness` | 20 | Black screen brightness threshold |
| `--flash` | 80 | Flash detection threshold (brightness delta) |
| `--output` | - | Save JSON report to file |

## How It Works

1. **Frame Drop**: Analyzes motion between consecutive frames. If motion is suspiciously low compared to expected motion at given FPS, marks as potential frame drop.

2. **Black Screen**: Calculates average frame brightness. If below threshold, marks as black screen.

3. **Freeze**: Compares frame similarity. If consecutive frames are >99% similar for 3+ frames, marks as freeze.

4. **Flash**: Monitors brightness changes between frames. Sudden changes > threshold indicate flash.

5. **Stutter**: Analyzes frame timing variance. High jitter indicates stuttering.

## License

MIT
