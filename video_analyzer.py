#!/usr/bin/env python3
"""
Video Fluency Analyzer
Input: Screen recording video file
Output: List of issues (frame drops, black screen, freeze, flash, etc.)
"""
import cv2
import numpy as np
import sys
import argparse
from pathlib import Path

class VideoAnalyzer:
    def __init__(self, 
                 brightness_threshold=20,
                 motion_threshold=0.01,
                 freeze_threshold=3,
                 flash_threshold=80):
        self.brightness_threshold = brightness_threshold
        self.motion_threshold = motion_threshold
        self.freeze_threshold = freeze_threshold
        self.flash_threshold = flash_threshold
        
    def analyze_frame(self, frame):
        """Analyze a single frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        return gray, brightness
    
    def calculate_psnr(self, frame1, frame2):
        """Calculate PSNR between two frames for quality assessment"""
        mse = np.mean((frame1.astype(float) - frame2.astype(float)) ** 2)
        if mse == 0:
            return 100
        return 20 * np.log10(255 / np.sqrt(mse))
    
    def detect_frame_drops(self, prev_gray, curr_gray, fps, timestamp):
        """Detect frame drops by analyzing motion discontinuity"""
        if prev_gray is None:
            return None
        
        # Calculate difference
        diff = np.abs(curr_gray.astype(float) - prev_gray.astype(float))
        motion = np.mean(diff) / 255.0
        
        # Expected motion per frame at given FPS
        expected_motion = fps / 60.0  # Normalized to 60fps
        
        # If motion is much lower than expected, might be a frame drop
        if motion < self.motion_threshold * 0.1:
            return {
                'type': 'frame_drop',
                'timestamp': timestamp,
                'frame': int(timestamp * fps),
                'confidence': min(1.0, (self.motion_threshold * 0.1 - motion) / (self.motion_threshold * 0.1))
            }
        return None
    
    def detect_black_screen(self, brightness, timestamp, frame_num):
        """Detect black/dark frames"""
        if brightness < self.brightness_threshold:
            return {
                'type': 'black_screen',
                'timestamp': timestamp,
                'frame': frame_num,
                'brightness': float(brightness)
            }
        return None
    
    def detect_freeze(self, prev_gray, curr_gray, timestamp, frame_num, consecutive_freeze):
        """Detect frozen frames (identical or nearly identical)"""
        if prev_gray is None:
            return None
            
        # Calculate similarity
        diff = np.mean(np.abs(curr_gray.astype(float) - prev_gray.astype(float)))
        similarity = 1 - (diff / 255.0)
        
        if similarity > 0.99:  # Nearly identical
            consecutive_freeze[0] += 1
            if consecutive_freeze[0] >= self.freeze_threshold:
                return {
                    'type': 'freeze',
                    'timestamp': timestamp,
                    'frame': frame_num,
                    'duration_frames': consecutive_freeze[0],
                    'similarity': float(similarity)
                }
        else:
            consecutive_freeze[0] = 0
        return None
    
    def detect_flash(self, prev_brightness, curr_brightness, timestamp, frame_num):
        """Detect sudden brightness changes (flash)"""
        delta = abs(curr_brightness - prev_brightness)
        if delta > self.flash_threshold:
            return {
                'type': 'flash',
                'timestamp': timestamp,
                'frame': frame_num,
                'delta_brightness': float(delta),
                'prev_brightness': float(prev_brightness),
                'curr_brightness': float(curr_brightness)
            }
        return None
    
    def detect_stutter(self, frame_times, fps, timestamp, frame_num):
        """Detect stuttering by frame timing analysis"""
        if len(frame_times) < 3:
            return None
            
        # Calculate expected frame interval
        expected_interval = 1.0 / fps
        
        # Get actual intervals
        intervals = []
        for i in range(1, len(frame_times)):
            intervals.append(frame_times[-1] - frame_times[-2])
        
        if len(intervals) < 2:
            return None
            
        # Detect irregular timing
        avg_interval = np.mean(intervals[-5:])  # Last 5 intervals
        variance = np.std(intervals[-5:])
        
        # High variance indicates stutter
        if variance > expected_interval * 0.5:
            return {
                'type': 'stutter',
                'timestamp': timestamp,
                'frame': frame_num,
                'expected_interval': float(expected_interval),
                'actual_interval': float(avg_interval),
                'jitter': float(variance)
            }
        return None
    
    def analyze(self, video_path, output_report=None):
        """Analyze video file and return issues"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {'error': f'Cannot open video: {video_path}'}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Video: {video_path}")
        print(f"Resolution: {width}x{height}, FPS: {fps}, Total frames: {total_frames}")
        print("-" * 60)
        
        issues = []
        prev_gray = None
        prev_brightness = 0
        frame_times = []
        consecutive_freeze = [0]
        frame_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_num / fps
            frame_times.append(timestamp)
            
            # Analyze current frame
            gray, brightness = self.analyze_frame(frame)
            
            # Check for black screen
            issue = self.detect_black_screen(brightness, timestamp, frame_num)
            if issue:
                issues.append(issue)
            
            # Check for flash
            if prev_gray is not None:
                issue = self.detect_flash(prev_brightness, brightness, timestamp, frame_num)
                if issue:
                    issues.append(issue)
                    
                # Check for frame drops
                issue = self.detect_frame_drops(prev_gray, gray, fps, timestamp)
                if issue:
                    issues.append(issue)
                    
                # Check for freeze
                issue = self.detect_freeze(prev_gray, gray, timestamp, frame_num, consecutive_freeze)
                if issue:
                    issues.append(issue)
            
            # Check for stutter (every 10 frames)
            if frame_num % 10 == 0 and frame_num > 0:
                issue = self.detect_stutter(frame_times, fps, timestamp, frame_num)
                if issue:
                    issues.append(issue)
            
            prev_gray = gray
            prev_brightness = brightness
            frame_num += 1
        
        cap.close()
        
        # Summary
        result = {
            'video': str(video_path),
            'resolution': f'{width}x{height}',
            'fps': fps,
            'total_frames': total_frames,
            'issues': issues,
            'summary': self._summarize(issues)
        }
        
        return result
    
    def _summarize(self, issues):
        """Create summary of issues"""
        summary = {
            'total_issues': len(issues),
            'frame_drops': 0,
            'black_screens': 0,
            'freezes': 0,
            'flashes': 0,
            'stutters': 0
        }
        
        for issue in issues:
            issue_type = issue['type']
            if issue_type == 'frame_drop':
                summary['frame_drops'] += 1
            elif issue_type == 'black_screen':
                summary['black_screens'] += 1
            elif issue_type == 'freeze':
                summary['freezes'] += 1
            elif issue_type == 'flash':
                summary['flashes'] += 1
            elif issue_type == 'stutter':
                summary['stutters'] += 1
        
        return summary
    
    def print_report(self, result):
        """Print analysis report"""
        if 'error' in result:
            print(f"Error: {result['error']}")
            return
        
        print("\n" + "=" * 60)
        print("VIDEO FLUENCY ANALYSIS REPORT")
        print("=" * 60)
        
        summary = result['summary']
        print(f"\n📊 Summary:")
        print(f"   Total issues found: {summary['total_issues']}")
        print(f"   🟥 Frame drops: {summary['frame_drops']}")
        print(f"   ⬛ Black screens: {summary['black_screens']}")
        print(f"   ❄️  Freezes: {summary['freezes']}")
        print(f"   ⚡ Flashes: {summary['flashes']}")
        print(f"   🔀 Stutters: {summary['stutters']}")
        
        if result['issues']:
            print(f"\n📝 Detailed Issues:")
            for i, issue in enumerate(result['issues'], 1):
                print(f"\n   [{i}] {issue['type'].upper()}")
                print(f"       Time: {issue['timestamp']:.2f}s (Frame {issue['frame']})")
                
                if issue['type'] == 'black_screen':
                    print(f"       Brightness: {issue['brightness']:.1f}")
                elif issue['type'] == 'flash':
                    print(f"       Brightness change: {issue['delta_brightness']:.1f}")
                elif issue['type'] == 'freeze':
                    print(f"       Duration: {issue['duration_frames']} frames")
                elif issue['type'] == 'stutter':
                    print(f"       Jitter: {issue['jitter']*1000:.1f}ms")
        
        print("\n" + "=" * 60)

def main():
    parser = argparse.ArgumentParser(description='Analyze video for fluency issues')
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--output', '-o', help='Output report to file')
    parser.add_argument('--brightness', '-b', type=int, default=20, help='Black screen threshold')
    parser.add_argument('--flash', '-f', type=int, default=80, help='Flash detection threshold')
    args = parser.parse_args()
    
    analyzer = VideoAnalyzer(
        brightness_threshold=args.brightness,
        flash_threshold=args.flash
    )
    
    result = analyzer.analyze(args.video)
    analyzer.print_report(result)
    
    if args.output:
        import json
        with open(args.output, 'w') as fp:
            json.dump(result, fp, indent=2)
        print(f"\nReport saved to: {args.output}")
    
    return 0 if result['summary']['total_issues'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
