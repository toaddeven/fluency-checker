#!/usr/bin/env python3
"""
Video Fluency Visualizer
"""
import cv2
import numpy as np
import json
import sys
import argparse
import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8080

class VideoAnalyzer:
    def __init__(self, brightness_threshold=20, freeze_threshold=3, flash_threshold=80):
        self.brightness_threshold = brightness_threshold
        self.freeze_threshold = freeze_threshold
        self.flash_threshold = flash_threshold
        
    def analyze_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        return gray, brightness
    
    def analyze(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {'error': 'Cannot open video: ' + video_path}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        issues = []
        prev_gray = None
        frame_num = 0
        consecutive_freeze = [0]
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_num / fps
            gray, brightness = self.analyze_frame(frame)
            
            if brightness < self.brightness_threshold:
                issues.append({
                    'type': 'black_screen',
                    'timestamp': round(timestamp, 2),
                    'frame': frame_num,
                    'brightness': float(brightness)
                })
            
            if prev_gray is not None:
                delta = abs(brightness - np.mean(prev_gray))
                if delta > self.flash_threshold:
                    issues.append({
                        'type': 'flash',
                        'timestamp': round(timestamp, 2),
                        'frame': frame_num,
                        'delta': float(delta)
                    })
                
                diff = np.mean(np.abs(gray.astype(float) - prev_gray.astype(float)))
                similarity = 1 - (diff / 255.0)
                if similarity > 0.99:
                    consecutive_freeze[0] += 1
                    if consecutive_freeze[0] >= self.freeze_threshold:
                        issues.append({
                            'type': 'freeze',
                            'timestamp': round(timestamp, 2),
                            'frame': frame_num,
                            'duration': consecutive_freeze[0]
                        })
                else:
                    consecutive_freeze[0] = 0
                    
                if diff / 255.0 < 0.001 and brightness > self.brightness_threshold:
                    issues.append({
                        'type': 'frame_drop',
                        'timestamp': round(timestamp, 2),
                        'frame': frame_num
                    })
            
            prev_gray = gray
            frame_num += 1
        
        cap.release()
        
        return {
            'video': str(video_path),
            'fps': fps,
            'total_frames': total_frames,
            'duration': total_frames / fps,
            'issues': issues
        }
    
    def generate_html(self, analysis_result, video_path):
        video_name = Path(video_path).name
        issues_json = json.dumps(analysis_result['issues'])
        
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fluency Checker - ''' + video_name + '''</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #16213e; padding: 15px 20px; border-bottom: 1px solid #0f3460; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 18px; color: #00d9ff; }
        .stats { display: flex; gap: 20px; }
        .stat { padding: 5px 12px; border-radius: 15px; font-size: 13px; }
        .stat.drop { background: #e74c3c; }
        .stat.black { background: #2c3e50; }
        .stat.freeze { background: #3498db; }
        .stat.flash { background: #f39c12; }
        .main { flex: 1; display: flex; overflow: hidden; }
        .timeline { background: #16213e; padding: 20px; width: 300px; overflow-y: auto; }
        .timeline h3 { margin-bottom: 15px; font-size: 14px; color: #888; text-transform: uppercase; }
        .issue-item { background: #0f3460; padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer; border-left: 3px solid #00d9ff; }
        .issue-item:hover { background: #1a4a7a; }
        .issue-item.black { border-left-color: #2c3e50; }
        .issue-item.freeze { border-left-color: #3498db; }
        .issue-item.flash { border-left-color: #f39c12; }
        .issue-item.frame_drop { border-left-color: #e74c3c; }
        .issue-time { font-size: 12px; color: #888; }
        .issue-type { font-weight: 600; margin: 5px 0; }
        .issue-detail { font-size: 11px; color: #aaa; }
        .viewer { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
        video { max-width: 100%; max-height: 70vh; border-radius: 8px; }
        .controls { display: flex; align-items: center; gap: 15px; margin-top: 20px; }
        .progress { width: 400px; height: 6px; }
        .time-display { font-size: 13px; color: #888; min-width: 100px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Fluency Checker</h1>
        <div class="stats">
            <span class="stat drop">Drop ''' + str(len([i for i in analysis_result['issues'] if i['type'] == 'frame_drop'])) + '''</span>
            <span class="stat black">Black ''' + str(len([i for i in analysis_result['issues'] if i['type'] == 'black_screen'])) + '''</span>
            <span class="stat freeze">Freeze ''' + str(len([i for i in analysis_result['issues'] if i['type'] == 'freeze'])) + '''</span>
            <span class="stat flash">Flash ''' + str(len([i for i in analysis_result['issues'] if i['type'] == 'flash'])) + '''</span>
        </div>
    </div>
    <div class="main">
        <div class="timeline">
            <h3>Issues</h3>
''' + self._generate_issue_items(analysis_result['issues']) + '''
        </div>
        <div class="viewer">
            <video id="video" controls>
                <source src="/video" type="video/mp4">
            </video>
            <div class="controls">
                <span class="time-display" id="timeDisplay">0:00</span>
                <input type="range" class="progress" id="progress" min="0" max="''' + str(analysis_result['total_frames']) + '''" value="0">
            </div>
        </div>
    </div>
    <script>
        const video = document.getElementById('video');
        const progress = document.getElementById('progress');
        const timeDisplay = document.getElementById('timeDisplay');
        const issues = ''' + issues_json + ''';
        const duration = ''' + str(analysis_result['duration']) + ''';
        
        progress.addEventListener('input', function() {
            video.currentTime = (progress.value / ''' + str(analysis_result['total_frames']) + ''') * duration;
        });
        
        video.addEventListener('timeupdate', function() {
            progress.value = (video.currentTime / duration) * ''' + str(analysis_result['total_frames']) + ''';
            timeDisplay.textContent = Math.floor(video.currentTime) + 's / ' + Math.floor(duration) + 's';
        });
    </script>
</body>
</html>'''
        return html
    
    def _generate_issue_items(self, issues):
        items = []
        type_names = {'frame_drop': ('Drop', 'drop'), 'black_screen': ('Black', 'black'), 'freeze': ('Freeze', 'freeze'), 'flash': ('Flash', 'flash')}
        
        for issue in issues:
            type_name, css_class = type_names.get(issue['type'], (issue['type'], ''))
            detail = ''
            if 'brightness' in issue:
                detail = 'Brightness: ' + str(round(issue['brightness'], 1))
            elif 'delta' in issue:
                detail = 'Delta: ' + str(round(issue['delta'], 1))
            elif 'duration' in issue:
                detail = 'Frames: ' + str(issue['duration'])
            
            items.append('<div class="issue-item ' + css_class + '" onclick="video.currentTime=' + str(issue['timestamp']) + '">' +
                '<div class="issue-time">' + str(issue['timestamp']) + 's (frame ' + str(issue['frame']) + ')</div>' +
                '<div class="issue-type">' + type_name + '</div>' +
                '<div class="issue-detail">' + detail + '</div></div>')
        
        return ''.join(items)

class VideoHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video':
            if hasattr(self.server, 'video_path'):
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', str(Path(self.server.video_path).stat().st_size))
                self.end_headers()
                with open(self.server.video_path, 'rb') as f:
                    self.wfile.write(f.read())
        else:
            super().do_GET()

def serve_video(video_path, port=PORT):
    analyzer = VideoAnalyzer()
    result = analyzer.analyze(video_path)
    
    if 'error' in result:
        print('Error:', result['error'])
        return
    
    html = analyzer.generate_html(result, video_path)
    html_path = Path(video_path).parent / 'fluency_report.html'
    with open(html_path, 'w') as f:
        f.write(html)
    
    print('Analysis complete! Total issues:', len(result['issues']))
    print('Opening: http://localhost:' + str(port))
    
    handler = VideoHandler
    handler.video_path = str(video_path)
    
    with socketserver.TCPServer(('', port), handler) as httpd:
        webbrowser.open('http://localhost:' + str(port) + '/fluency_report.html')
        httpd.serve_forever()

def main():
    if len(sys.argv) < 2:
        print('Usage: visualizer.py <video_file>')
        sys.exit(1)
    
    video_path = sys.argv[1]
    serve_video(video_path)

if __name__ == '__main__':
    main()
