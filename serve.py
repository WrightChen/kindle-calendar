#!/usr/bin/env python3
"""Tiny LAN server for the Kindle: GET /calendar.png re-renders when the date changed (or hourly).

    python serve.py --port 8765
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
OUT = HERE / "site" / "calendar.png"
TZ = ZoneInfo("Asia/Shanghai")
_lock = threading.Lock()
_last_render: dt.datetime | None = None


def ensure_fresh() -> None:
    global _last_render
    now = dt.datetime.now(TZ)
    with _lock:
        stale = (
            _last_render is None
            or not OUT.exists()
            or _last_render.date() != now.date()
            or (now - _last_render) > dt.timedelta(hours=1)
        )
        if stale:
            script = "render_qa.py" if os.environ.get("STYLE", "qa") == "qa" else "render.py"
            subprocess.run([sys.executable, str(HERE / script), "--out", str(OUT)], check=True,
                           env={"PYTHONIOENCODING": "utf-8", **os.environ})
            _last_render = now


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ("/", "/calendar.png"):
            self.send_error(404)
            return
        try:
            ensure_fresh()
        except Exception as e:  # keep serving the last good image
            sys.stderr.write(f"render failed: {e}\n")
        data = OUT.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:  # noqa: D401
        sys.stderr.write(f"{dt.datetime.now(TZ):%m-%d %H:%M:%S} {self.client_address[0]} {fmt % args}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--bind", default="0.0.0.0")
    args = ap.parse_args()
    ensure_fresh()
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"serving {OUT} on http://{args.bind}:{args.port}/calendar.png", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
