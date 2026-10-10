"""
ATLAS Fuzzer — Universal Vercel Handler
Serves the Red-Teaming Workbench Portal (HTML/CSS/JS) and API Endpoints.
Guarantees the frontend displays properly whether Vercel deploys in Python or Static mode.
"""
from http.server import BaseHTTPRequestHandler
import os
import json
import mimetypes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_path = self.path.split('?')[0]

        # 1. API Endpoints
        if url_path.startswith('/api/health') or url_path == '/api':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = {
                "name": "ATLAS Fuzzer Engine",
                "version": "1.0.0",
                "status": "online",
                "framework": "MITRE ATLAS v2024",
                "compliance": [
                    "MITRE ATLAS (AML.T0051 - AML.T0056)",
                    "NIST AI RMF 1.0 (MAP, MEASURE, MANAGE)",
                    "OWASP Top 10 for Large Language Models"
                ]
            }
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
            return

        # 2. Static File Resolution
        if url_path in ('', '/', '/index', '/index.html'):
            rel_file = 'index.html'
        else:
            rel_file = url_path.lstrip('/')

        candidate_paths = [
            os.path.join(BASE_DIR, rel_file),
            os.path.join(BASE_DIR, 'portal', rel_file)
        ]

        target_file = None
        for p in candidate_paths:
            if os.path.isfile(p):
                target_file = p
                break

        # Fallback to index.html if file doesn't exist
        if not target_file:
            target_file = os.path.join(BASE_DIR, 'index.html')
            if not os.path.isfile(target_file):
                target_file = os.path.join(BASE_DIR, 'portal', 'index.html')

        if os.path.isfile(target_file):
            content_type, _ = mimetypes.guess_type(target_file)
            if not content_type:
                if target_file.endswith('.css'):
                    content_type = 'text/css'
                elif target_file.endswith('.js'):
                    content_type = 'application/javascript'
                elif target_file.endswith('.html'):
                    content_type = 'text/html; charset=utf-8'
                else:
                    content_type = 'text/plain'

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()

            with open(target_file, 'rb') as f:
                self.wfile.write(f.read())
            return

        # 3. 404 Fallback
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"404 Not Found")
