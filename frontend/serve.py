#!/usr/bin/env python3
"""Serve the built Svelte trace viewer frontend.

Usage:
    uv run python frontend/serve.py          # default port 8080
    uv run python frontend/serve.py 3000     # custom port

For development with hot reload:
    cd frontend && npm run dev
"""

import http.server
import os
import sys
import webbrowser
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

dist_dir = Path(__file__).parent / "dist"
if not dist_dir.exists():
    print("Built frontend not found. Building...")
    os.system(f"cd {Path(__file__).parent} && npm run build")

os.chdir(dist_dir)
handler = http.server.SimpleHTTPRequestHandler
with http.server.HTTPServer(("localhost", PORT), handler) as server:
    url = f"http://localhost:{PORT}"
    print(f"Trace viewer running at {url}")
    webbrowser.open(url)
    server.serve_forever()
