"""Server-owned cube renderer. Agents never receive cubie JSON."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

class TrustedView:
    def __init__(self, origin: str, web_root: Path) -> None:
        self.origin = origin.rstrip("/")
        host_js = Path(web_root) / "js" / "trusted-host.mjs"
        env = os.environ.copy()
        node_path = env.get("NODE_PATH", "")
        extra = "/home/ben/.npm/_npx/7d92d9a2d2ccc630/node_modules"
        if extra not in node_path and Path(extra).is_dir():
            env["NODE_PATH"] = extra if not node_path else extra + ":" + node_path
        self.proc = subprocess.Popen(
            ["node", str(host_js), self.origin],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )
        self._lock = threading.Lock()
        hello = self.call({"op": "ping"})
        if not hello.get("ok"):
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"trusted renderer failed: {hello} {err[:500]}")

    def call(self, msg: dict[str, Any]) -> dict[str, Any]:
        if self.proc.poll() is not None:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"trusted renderer exited: {err[:800]}")
        assert self.proc.stdin and self.proc.stdout
        with self._lock:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"trusted renderer closed: {err[:800]}")
        return json.loads(line)

    def load(self, session: dict[str, Any]) -> None:
        result = self.call(
            {
                "op": "load",
                "id": session["id"],
                "kind": session.get("kind") or "3d",
                "state": session["state"],
            }
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "load failed")
        session["server_history"] = []
        session["server_clicks"] = []

    def click(self, session: dict[str, Any], x: float, y: float, button: int, dbl: bool) -> dict[str, Any]:
        result = self.call(
            {
                "op": "click",
                "id": session["id"],
                "x": int(x),
                "y": int(y),
                "button": int(button or 0),
                "dbl": bool(dbl),
            }
        )
        session["server_clicks"] = list(session.get("server_clicks") or []) + [
            {"t": None, "x": int(x), "y": int(y), "button": int(button or 0), "dbl": bool(dbl), "kind": "pointer"}
        ]
        if result.get("history") is not None:
            session["server_history"] = result["history"]
        return result

    def orbit(self, session: dict[str, Any], x: float, y: float, dx: float, dy: float) -> dict[str, Any]:
        result = self.call(
            {
                "op": "orbit",
                "id": session["id"],
                "x": int(x),
                "y": int(y),
                "dx": int(dx),
                "dy": int(dy),
            }
        )
        session["server_clicks"] = list(session.get("server_clicks") or []) + [
            {"t": None, "x": int(x), "y": int(y), "button": 0, "dbl": False, "kind": "orbit"}
        ]
        return result

    def png(self, session: dict[str, Any]) -> bytes:
        import base64

        result = self.call({"op": "shot", "id": session["id"]})
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "shot failed")
        return base64.b64decode(result["png"])

    def close(self) -> None:
        try:
            self.call({"op": "close"})
        except Exception:
            pass
        if self.proc.poll() is None:
            self.proc.terminate()
