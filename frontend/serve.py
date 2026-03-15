#!/usr/bin/env python3
"""Minimal dev server for the trace viewer frontend."""

import http.server
import os
import sys
import webbrowser

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

os.chdir(os.path.dirname(os.path.abspath(__file__)))
handler = http.server.SimpleHTTPRequestHandler
with http.server.HTTPServer(("localhost", PORT), handler) as server:
    url = f"http://localhost:{PORT}"
    print(f"Trace viewer running at {url}")
    webbrowser.open(url)
    server.serve_forever()
