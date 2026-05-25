"""Local dev server for the 2026 Rookie Board.

Serves the board at http://localhost:5050 and exposes a POST /refresh endpoint
that runs refresh_draft_state.py on demand — so the browser button works
without any terminal commands.

Usage:
    .venv/bin/python scripts/serve_rookie_board.py
    (browser opens automatically)
"""

from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "src" / "dynasty_genius" / "dashboard"
RESOURCES_DIR = ROOT / "resources"
PORT = 5050


class BoardHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # suppress default Apache-style logs
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        mime, _ = mimetypes.guess_type(str(path))
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._send_file(DASHBOARD_DIR / "rookie_board.html")

        elif path.startswith("/resources/"):
            filename = path[len("/resources/"):]
            self._send_file(RESOURCES_DIR / filename)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/refresh":
            self.send_response(404)
            self.end_headers()
            return

        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "refresh_draft_state.py")],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
            )
            if result.returncode == 0:
                print(f"[refresh] {result.stdout.strip()}")
                self._send_json(200, {"ok": True, "output": result.stdout.strip()})
            else:
                print(f"[refresh] ERROR: {result.stderr.strip()}")
                self._send_json(500, {"ok": False, "error": result.stderr.strip()[:200]})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})


def main() -> None:
    server = HTTPServer(("localhost", PORT), BoardHandler)
    url = f"http://localhost:{PORT}"

    print(f"Rookie Board → {url}")
    print("Ctrl+C to stop\n")

    threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
