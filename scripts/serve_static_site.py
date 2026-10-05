#!/usr/bin/env python3
"""Serve a published site folder locally the way Vercel will: static files,
and index.html for any path that is not a file (SPA routes). For checking
`atlas publish` output before deploying. Usage: serve_static_site.py DIR [PORT]"""
import http.server
import os
import sys
from functools import partial

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "site")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 3400


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path.split("?", 1)[0])
        if not os.path.exists(path) and not self.path.startswith(("/api/", "/edition/", "/assets/")):
            self.path = "/index.html"
        return super().send_head()

    def log_message(self, fmt, *args):  # one line per request, no timestamps noise
        sys.stderr.write("%s %s\n" % (self.command, self.path))


http.server.ThreadingHTTPServer.allow_reuse_address = True
with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), partial(SPAHandler, directory=ROOT)) as httpd:
    print(f"serving {ROOT} on http://127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()
