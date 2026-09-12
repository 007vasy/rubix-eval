"""Static + JSON API server for the interactive 3D cube."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .cube import Cube
from .metrics import grade_solution
from .task import make_task


def serve(web_root: Path, host: str, port: int) -> None:
    root = web_root.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            sys_stderr_write = super().log_message
            sys_stderr_write(fmt, *args)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/task":
                query = parse_qs(parsed.query)
                size = int(query.get("size", ["3"])[0])
                depth = int(query.get("depth", ["8"])[0])
                seed = int(query.get("seed", ["0"])[0])
                task = make_task(size, depth, seed)
                payload = task.to_dict()
                payload["oracle"] = task.oracle_solution()
                self._json(payload)
                return
            super().do_GET()

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json({"error": "invalid JSON"}, 400)
                return
            if parsed.path == "/api/grade":
                state = body.get("state", body)
                cube = Cube.from_dict(state)
                depth = int(body.get("scramble_depth", 0))
                max_moves = body.get("max_moves")
                result = grade_solution(cube, body.get("solution", ""), depth, max_moves)
                self._json(result.to_dict())
                return
            self._json({"error": "not found"}, 404)

        def _json(self, payload: dict, status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

    httpd = ThreadingHTTPServer((host, port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
