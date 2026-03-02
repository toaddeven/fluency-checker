#!/usr/bin/env python3
"""
Screen Quality Detector
Detects: stuttering, lag, black screen, flash, screen freeze
"""
import subprocess
import os
import sys
import time
import tempfile
from PIL import Image
import numpy as np

class ScreenDetector:
    def __init__(self, threshold_brightness=15, threshold_motion=0.02, freeze_frames=5):
        self.threshold_brightness = threshold_brightness
        self.threshold_motion = threshold_motion
        self.freeze_frames = freeze_frames
        self.frame_history = []
        
    def capture_screen(self):
        """Capture a screen frame"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            tmp_path = f.name
        
        result = subprocess.run(
            ['/usr/sbin/screencapture', '-x', '-D1', tmp_path],
            capture_output=True
        )
        
        if result.returncode != 0:
            return None
            
        try:
            img = Image.open(tmp_path)
            img = img.convert('L')  # Grayscale
            os.unlink(tmp_path)
            return np.array(img)
        except:
            return None
    
    def calculate_brightness(self, frame):
        """Calculate average brightness"""
        if frame is None:
            return 0
        return np.mean(frame)
    
    def calculate_motion(self, frame1, frame2):
        """Calculate motion between two frames"""
        if frame1 is None or frame2 is None:
            return 0
        
        # Calculate difference
        diff = np.abs(frame1.astype(float) - frame2.astype(float))
        motion = np.mean(diff) / 255.0
        return motion
    
    def detect_black_screen(self, frame):
        """Detect if screen is black (off or locked)"""
        brightness = self.calculate_brightness(frame)
        return brightness < self.threshold_brightness
    
    def detect_flash(self, frame1, frame2):
        """Detect screen flash (sudden brightness change)"""
        b1 = self.calculate_brightness(frame1)
        b2 = self.calculate_brightness(frame2)
        
        # Significant brightness change
        if abs(b1 - b2) > 100:
            return True
        return False
    
    def detect_freeze(self, frame1, frame2):
        """Detect screen freeze (no motion)"""
        motion = self.calculate_motion(frame1, frame2)
        return motion < self.threshold_motion
    
    def detect_stutter(self, frame1, frame2, frame3):
        """Detect stuttering (irregular frame timing)"""
        # This is a simplified detection
        # Real stutter detection requires frame timing analysis
        motion1 = self.calculate_motion(frame1, frame2)
        motion2 = self.calculate_motion(frame2, frame3)
        
        # Inconsistent motion patterns indicate stutter
        if motion1 > 0 and motion2 > 0:
            ratio = min(motion1, motion2) / max(motion1, motion2)
            if ratio < 0.3:  # Very inconsistent
                return True
        return False
    
    def analyze(self, duration=10, interval=0.5):
        """
        Analyze screen quality for specified duration
        Returns: dict with detection results
        """
        results = {
            'black_screen_count': 0,
            'flash_count': 0,
            'freeze_count': 0,
            'stutter_count': 0,
            'total_frames': 0,
            'issues': []
        }
        
        frames = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            frame = self.capture_screen()
            if frame is not None:
                frames.append(frame)
                results['total_frames'] += 1
                
                # Check black screen
                if self.detect_black_screen(frame):
                    results['black_screen_count'] += 1
                    results['issues'].append('Black screen detected')
                
                # Check against previous frames
                if len(frames) >= 2:
                    # Freeze detection
                    if self.detect_freeze(frames[-2], frame):
                        results['freeze_count'] += 1
                        results['issues'].append('Screen freeze detected')
                    
                    # Flash detection
                    if self.detect_flash(frames[-2], frame):
                        results['flash_count'] += 1
                        results['issues'].append('Screen flash detected')
                
                # Stutter detection (need 3 frames)
                if len(frames) >= 3:
                    if self.detect_stutter(frames[-3], frames[-2], frames[-1]):
                        results['stutter_count'] += 1
                        results['issues'].append('Stutter detected')
            
            time.sleep(interval)
        
        return results

def main():
    detector = ScreenDetector()
    
    print("Starting screen quality detection...")
    print("Monitoring for 30 seconds...\n")
    
    results = detector.analyze(duration=30, interval=0.5)
    
    print("=" * 50)
    print("DETECTION RESULTS")
    print("=" * 50)
    print(f"Total frames analyzed: {results['total_frames']}")
    print(f"Black screen events: {results['black_screen_count']}")
    print(f"Flash events: {results['flash_count']}")
    print(f"Freeze events: {results['freeze_count']}")
    print(f"Stutter events: {results['stutter_count']}")
    
    if results['issues']:
        print("\nIssues detected:")
        for issue in results['issues'][:10]:  # Show first 10
            print(f"  - {issue}")
    else:
        print("\nNo issues detected!")
    
    return 0 if results['stutter_count'] == 0 and results['freeze_count'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
