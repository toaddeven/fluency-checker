#!/usr/bin/env python3
"""
Video Fluency Visualizer
Web-based tool to visualize and navigate through video issues
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
from urllib.parse import quote

PORT = 8080

class VideoAnalyzer:
    def __init__(self, brightness_threshold=20, motion_threshold=0.01, freeze_threshold=3, flash_threshold=80):
        self.brightness_threshold = brightness_threshold
        self.motion_threshold = motion_threshold
        self.freeze_threshold = freeze_threshold
        self.flash_threshold = flash_threshold
        
    def analyze_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        return gray, brightness
    
    def analyze(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {'error': f'Cannot open video: {video_path}'}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        issues = []
        prev_gray = None
        prev_brightness = 0
        frame_num = 0
        consecutive_freeze = [0]
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_num / fps
            gray, brightness = self.analyze_frame(frame)
            
            # Black screen
            if brightness < self.brightness_threshold:
                issues.append({
                    'type': 'black_screen',
                    'timestamp': round(timestamp, 2),
                    'frame': frame_num,
                    'brightness': float(brightness)
                })
            
            # Flash
            if prev_gray is not None:
                delta = abs(brightness - prev_brightness)
                if delta > self.flash_threshold:
                    issues.append({
                        'type': 'flash',
                        'timestamp': round(timestamp, 2),
                        'frame': frame_num,
                        'delta': float(delta)
                    })
                
                # Freeze
                diff = np.mean(np.abs(curr_gray.astype(float) - prev_gray.astype(float)))
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
                    
                # Frame drop (simplified)
                if diff / 255.0 < 0.001 and brightness > self.brightness_threshold:
                    issues.append({
                        'type': 'frame_drop',
                        'timestamp': round(timestamp, 2),
                        'frame': frame_num
                    })
            
            prev_gray = gray
            prev_brightness = brightness
            frame_num += 1
        
        cap.release()
        
        return {
            'video': str(video_path),
            'fps': fps,
            'total_frames': total_frames,
            'duration': total_frames / fps,
            'issues': issues
    def generate_html(self, analysis_result, video_path):
        video_name = Path(video_path).name
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fluency Checker - {video_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: #16213e;
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 18px; color: #00d9ff; }}
        .stats {{
            display: flex;
            gap: 20px;
        }}
        .stat {{
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 13px;
            font-weight: 500;
        }}
        .stat.drop {{ background: #e74c3c; }}
        .stat.black {{ background: #2c3e50; }}
        .stat.freeze {{ background: #3498db; }}
        .stat.flash {{ background: #f39c12; }}
        
        .main {{
            flex: 1;
            display: flex;
            overflow: hidden;
        }}
        .timeline {{
            background: #16213e;
            padding: 20px;
            width: 300px;
            overflow-y: auto;
            border-right: 1px solid #0f3460;
        }}
        .timeline h3 {{
            margin-bottom: 15px;
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
        }}
        .issue-item {{
            background: #0f3460;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid #00d9ff;
        }}
        .issue-item:hover {{
            background: #1a4a7a;
            transform: translateX(5px);
        }}
        .issue-item.black {{ border-left-color: #2c3e50; }}
        .issue-item.freeze {{ border-left-color: #3498db; }}
        .issue-item.flash {{ border-left-color: #f39c12; }}
        .issue-item.frame_drop {{ border-left-color: #e74c3c; }}
        
        .issue-time {{ font-size: 12px; color: #888; }}
        .issue-type {{ font-weight: 600; margin: 5px 0; }}
        .issue-detail {{ font-size: 11px; color: #aaa; }}
        
        .viewer {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
        }}
        video {{
            max-width: 100%;
            max-height: 70vh;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }}
        .controls {{
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 15px;
            background: rgba(0,0,0,0.8);
            padding: 10px 20px;
            border-radius: 30px;
        }}
        .progress {{
            width: 400px;
            height: 6px;
            -webkit-appearance: none;
            background: #333;
            border-radius: 3px;
            cursor: pointer;
        }}
        .progress::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            background: #00d9ff;
            border-radius: 50%;
            cursor: pointer;
        }}
        .time-display {{
            font-size: 13px;
            color: #888;
            min-width: 100px;
        }}
        .issue-markers {{
            position: absolute;
            top: 20px;
            left: 20px;
            right: 20px;
            height: 4px;
            display: flex;
            pointer-events: none;
        }}
        .marker {{
            position: absolute;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            top: -2px;
        }}
        .marker.drop {{ background: #e74c3c; }}
        .marker.black {{ background: #2c3e50; }}
        .marker.freeze {{ background: #3498db; }}
        .marker.flash {{ background: #f39c12; }}
        
        .current-issue {{
            background: #0f3460;
            padding: 15px 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            display: none;
        }}
        .current-issue.show {{ display: block; }}
        .current-issue h2 {{ color: #00d9ff; margin-bottom: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 Fluency Checker</h1>
        <div class="stats">
            <span class="stat drop">🟥 丢帧 {len([i for i in analysis_result['issues'] if i['type'] == 'frame_drop'])}</span>
            <span class="stat black">⬛ 黑屏 {len([i for i in analysis_result['issues'] if i['type'] == 'black_screen'])}</span>
            <span class="stat freeze">❄️ 冻结 {len([i for i in analysis_result['issues'] if i['type'] == 'freeze'])}</span>
            <span class="stat flash">⚡ 闪烁 {len([i for i in analysis_result['issues'] if i['type'] == 'flash'])}</span>
        </div>
    </div>
    
    <div class="main">
        <div class="timeline">
            <h3>异常时间轴</h3>
            {self._generate_issue_items(analysis_result['issues'])}
        </div>
        
        <div class="viewer">
            <div class="current-issue" id="currentIssue">
                <h2 id="issueType">--</h2>
                <p id="issueDetail">--</p>
            </div>
            
            <div class="issue-markers" id="markers"></div>
            
            <video id="video" controls>
                <source src="/video" type="video/mp4">
            </video>
            
            <div class="controls">
                <span class="time-display" id="timeDisplay">0:00 / 0:00</span>
                <input type="range" class="progress" id="progress" min="0" max="{analysis_result['total_frames']}" value="0">
            </div>
        </div>
    </div>
    
    <script>
        const video = document.getElementById('video');
        const progress = document.getElementById('progress');
        const timeDisplay = document.getElementById('timeDisplay');
        const currentIssue = document.getElementById('currentIssue');
        const issueType = document.getElementById('issueType');
        const issueDetail = document.getElementById('issueDetail');
        
        const issues = {json.dumps(analysis_result['issues'])};
        const duration = {analysis_result['duration']};
        
        // Generate markers
        const markers = document.getElementById('markers');
        issues.forEach(issue => {{
            const marker = document.createElement('div');
            marker.className = 'marker ' + issue.type.replace('_', ' ');
            marker.style.left = (issue.timestamp / duration * 100) + '%';
            marker.title = issue.type + ' @ ' + issue.timestamp + 's';
            markers.appendChild(marker);
        }});
        
        function formatTime(s) {{
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return m + ':' + sec.toString().padStart(2, '0');
        }}
        
        progress.addEventListener('input', () => {{
            video.currentTime = (progress.value / {analysis_result['total_frames']}) * duration;
        }});
        
        video.addEventListener('timeupdate', () => {{
            progress.value = (video.currentTime / duration) * {analysis_result['total_frames']};
            timeDisplay.textContent = formatTime(video.currentTime) + ' / ' + formatTime(duration);
            
            // Check for nearby issues
            const currentTime = video.currentTime;
            const nearbyIssue = issues.find(i => Math.abs(i.timestamp - currentTime) < 0.5);
            
            if (nearbyIssue) {{
                currentIssue.classList.add('show');
                const typeNames = {{
                    'frame_drop': '🟥 丢帧',
                    'black_screen': '⬛ 黑屏',
                    'freeze': '❄️ 冻结',
                    'flash': '⚡ 闪烁'
                }};
                issueType.textContent = typeNames[nearbyIssue.type] || nearbyIssue.type;
                
                let detail = '时间: ' + nearbyIssue.timestamp + 's';
                if (nearbyIssue.brightness) detail += ' | 亮度: ' + nearbyIssue.brightness.toFixed(1);
                if (nearbyIssue.delta) detail += ' | 变化: ' + nearbyIssue.delta.toFixed(1);
                if (nearbyIssue.duration) detail += ' | 持续: ' + nearbyIssue.duration + '帧';
                issueDetail.textContent = detail;
            }} else {{
                currentIssue.classList.remove('show');
            }}
        }});
    </script>
</body>
</html>'''
        return html
    
    def _generate_issue_items(self, issues):
        items = []
        type_names = {
            'frame_drop': ('🟥 丢帧', 'drop'),
            'black_screen': ('⬛ 黑屏', 'black'),
            'freeze': ('❄️ 冻结', 'freeze'),
            'flash': ('⚡ 闪烁', 'flash')
        }
        
        for i, issue in enumerate(issues):
            type_name, css_class = type_names.get(issue['type'], (issue['type'], ''))
            detail = ''
            if 'brightness' in issue:
                detail = f"亮度: {issue['brightness']:.1f}"
            elif 'delta' in issue:
                detail = f"变化: {issue['delta']:.1f}"
            elif 'duration' in issue:
                detail = f"持续 {issue['duration']} 帧"
            
            items.append(f'''
            <div class="issue-item {css_class}" onclick="seekTo({issue['timestamp']})">
                <div class="issue-time">{issue['timestamp']}s (帧 {issue['frame']})</div>
                <div class="issue-type">{type_name}</div>
                <div class="issue-detail">{detail}</div>
            </div>
            ''')
        
        return ''.join(items)

class VideoHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video':
            # Serve video file
            if hasattr(self.server, 'video_path'):
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', Path(self.server.video_path).stat().st_size)
                self.end_headers()
                with open(self.server.video_path, 'rb') as f:
                    self.wfile.write(f.read())
        else:
            super().do_GET()

def serve_video(video_path, port=PORT):
    analyzer = VideoAnalyzer()
    result = analyzer.analyze(video_path)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        return
    
    # Generate HTML
    html = analyzer.generate_html(result, video_path)
    html_path = Path(video_path).parent / 'fluency_report.html'
    with open(html_path, 'w') as f:
        f.write(html)
    
    print(f"\nAnalysis complete!")
    print(f"Total issues: {len(result['issues'])}")
    print(f"\nOpening visualizer at http://localhost:{port}")
    
    # Start server
    handler = VideoHandler
    handler.video_path = str(video_path)
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        webbrowser.open(f"http://localhost:{port}/fluency_report.html")
        httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description='Video Fluency Visualizer')
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--port', '-p', type=int, default=PORT, help='Server port')
    args = parser.parse_args()
    
    serve_video(args.video, args.port)

if __name__ == '__main__':
    main()
