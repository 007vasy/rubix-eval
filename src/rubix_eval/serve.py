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
from .records import list_records, load_record, public_record
from .leaderboard import build_ai_leaderboard, build_leaderboard
from .trusted_view import TrustedView
from .visual_session import bind_submit_body, boot_payload, grade_progress, random_visual_session


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
    view: TrustedView | None = None
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
            if path in ("/solves", "/solves/"):
                self.path = "/solves.html"
                super().do_GET()
                return
            if path in ("/leaderboard", "/leaderboard/"):
                self.path = "/leaderboard.html"
                super().do_GET()
                return
            if path in ("/ai", "/ai/", "/leaderboard/ai"):
                self.path = "/ai.html"
                super().do_GET()
                return
            if path in ("/replay", "/replay/"):
                self.path = "/replay.html"
                super().do_GET()
                return
            if path == "/api/leaderboard/ai":
                self._json(build_ai_leaderboard())
                return
            if path == "/api/leaderboard":
                want_bench = query.get("bench", ["0"])[0] in ("1", "true")
                visual = query.get("visual", ["1"])[0] not in ("0", "false")
                self._json(build_leaderboard(bench=want_bench, visual_only=visual))
                return
            if path == "/api/solves":
                sid = query.get("id", [None])[0]
                if sid:
                    record = load_record(sid)
                    if not record:
                        self._json({"error": "not found"}, 404)
                        return
                    self._json(public_record(record))
                    return
                self._json({"solves": list_records()})
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
                        ai = (query.get("ai") or query.get("agent") or query.get("model") or [None])[0]
                        if ai and str(ai).strip():
                            session["ai"] = str(ai).strip()[:80]
                        sessions[session["id"]] = session
                        current_id = session["id"]
                        if view is not None:
                            try:
                                view.load(session)
                            except Exception as exc:
                                self._json({"error": f"renderer failed: {exc}"}, 500)
                                return
                    elif query.get("ai") or query.get("agent") or query.get("model"):
                        ai = (query.get("ai") or query.get("agent") or query.get("model") or [None])[0]
                        if ai and str(ai).strip():
                            session["ai"] = str(ai).strip()[:80]
                self._json(boot_payload(session))
                return
            if path == "/api/visual/frame":
                sid = query.get("id", [current_id])[0]
                with lock:
                    session = sessions.get(sid) if sid else None
                if not session or view is None:
                    self._json({"error": "no visual session"}, 404)
                    return
                png = view.png(session)
                self._png(png)
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
                ndim = int(kind[0]) if kind and kind[0].isdigit() and kind.endswith("d") and kind != "3d" else 3
                task = (
                    make_hyper_task(depth, seed, size=size, ndim=ndim)
                    if ndim >= 4
                    else make_task(size, depth, seed)
                )
                payload = task.to_dict()
                payload.pop("oracle", None)
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
            if parsed.path == "/api/visual/input":
                with lock:
                    sid = body.get("id") or current_id
                    session = sessions.get(sid) if sid else None
                    if not session or view is None:
                        self._json({"error": "no visual session"}, 404)
                        return
                    kind = body.get("type") or "click"
                    if kind == "orbit":
                        result = view.orbit(
                            session,
                            body.get("x") or 80,
                            body.get("y") or 200,
                            body.get("dx") or 0,
                            body.get("dy") or 0,
                        )
                    else:
                        result = view.click(
                            session,
                            body.get("x") or 0,
                            body.get("y") or 0,
                            body.get("button") or 0,
                            bool(body.get("dbl")),
                        )
                payload = {"ok": True}
                if isinstance(result, dict):
                    payload["ok"] = bool(result.get("ok", True))
                    for key in ("pick", "error"):
                        if result.get(key) is not None:
                            payload[key] = result[key]
                    if result.get("history") is not None:
                        payload["n"] = len(result["history"])
                self._json(payload)
                return
            if parsed.path == "/api/visual/submit":
                with lock:
                    sid = body.get("id") or current_id
                    session = sessions.get(sid) if sid else None
                    if not session:
                        self._json({"error": "no visual session"}, 404)
                        return
                    body = bind_submit_body(session, body)
                    snapshot = {
                        key: session[key]
                        for key in (
                            "id",
                            "kind",
                            "size",
                            "scramble_depth",
                            "seed",
                            "max_moves",
                            "state",
                            "oracle",
                            "challenge_id",
                            "depth_label",
                            "started_at",
                            "ai",
                        )
                        if key in session
                    }
                payload = grade_progress(snapshot, body, compare=True, record=True)
                with lock:
                    live = sessions.get(sid)
                    if live is not None:
                        live["progress"] = payload
                        live["submitted"] = True
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

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _png(self, data: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

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
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    origin_host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    view = TrustedView(f"http://{origin_host}:{port}", root)
    if visual_session is not None:
        view.load(visual_session)
    try:
        worker.join()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.shutdown()
        if view is not None:
            view.close()
        httpd.server_close()
