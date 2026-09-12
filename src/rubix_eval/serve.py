"""Static + JSON API server for the interactive cube and visual eval."""

from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .cube import Cube
from .hypercube import HyperCube
from .metrics import grade_solution
from .task import make_hyper_task, make_task
from .challenges import catalog, request_challenge
from .visual_session import boot_payload, grade_progress, random_visual_session


def serve(
    web_root: Path,
    host: str,
    port: int,
    *,
    visual_session: dict | None = None,
) -> None:
    root = web_root.resolve()
    lock = threading.Lock()
    sessions: dict[str, dict] = {}
    current_id: str | None = None
    if visual_session is not None:
        sessions[visual_session["id"]] = visual_session
        current_id = visual_session["id"]

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self) -> None:
            nonlocal current_id
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path in ("/eval", "/eval/"):
                self.path = "/eval.html"
                super().do_GET()
                return
            if path == "/api/visual/boot":
                kind = query.get("kind", ["3d"])[0]
                size = int(query["size"][0]) if query.get("size") else None
                depth = query["depth"][0] if query.get("depth") else None
                want_new = query.get("random", ["1"])[0] not in ("0", "false")
                with lock:
                    session = None
                    if not want_new:
                        sid = query.get("id", [current_id])[0]
                        session = sessions.get(sid) if sid else None
                    if session is None:
                        session = random_visual_session(size=size, depth=depth, kind=kind)
                        sessions[session["id"]] = session
                        current_id = session["id"]
                self._json(boot_payload(session))
                return
            if path == "/api/challenges":
                kind = query.get("kind", ["3d"])[0]
                visual = query.get("visual", ["0"])[0] in ("1", "true")
                self._json({"challenges": catalog(kind=kind, visual=visual)})
                return
            if path == "/api/challenge":
                kind = query.get("kind", ["3d"])[0]
                size = int(query["size"][0]) if query.get("size") else None
                depth = query["depth"][0] if query.get("depth") else None
                visual = query.get("visual", ["0"])[0] in ("1", "true")
                try:
                    challenge = request_challenge(
                        size=size, depth=depth, kind=kind, visual=visual
                    )
                except ValueError as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                self._json(challenge.public_dict())
                return
            if path == "/api/visual/grade":
                with lock:
                    sid = query.get("id", [current_id])[0]
                    session = sessions.get(sid) if sid else None
                if not session:
                    self._json({"error": "no visual session"}, 404)
                    return
                if not session.get("progress"):
                    self._json({"error": "not submitted", "id": session["id"]}, 409)
                    return
                self._json(session["progress"])
                return
            if path == "/api/task":
                size = int(query.get("size", ["3"])[0])
                depth = int(query.get("depth", ["8"])[0])
                seed = int(query.get("seed", ["0"])[0])
                kind = query.get("kind", ["3d"])[0]
                task = make_hyper_task(depth, seed) if kind == "4d" else make_task(size, depth, seed)
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
            if parsed.path == "/api/visual/submit":
                with lock:
                    sid = body.get("id") or current_id
                    session = sessions.get(sid) if sid else None
                    if not session:
                        self._json({"error": "no visual session"}, 404)
                        return
                    session["progress"] = grade_progress(session, body)
                    session["submitted"] = True
                    payload = session["progress"]
                self._json(payload)
                return
            if parsed.path == "/api/grade":
                state = body.get("state", body)
                if state.get("kind") == "4d" or "cells" in state:
                    cube = HyperCube.from_dict(state)
                else:
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
            self.send_header("Cache-Control", "no-store")
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
