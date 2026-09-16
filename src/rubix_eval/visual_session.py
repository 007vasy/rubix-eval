"""Visual-only eval sessions. The page never receives the scramble or oracle."""

from __future__ import annotations

import os
import secrets
import time
from typing import Any

from .challenges import Challenge, request_challenge
from .records import make_record, write_record
from .solvers import compare_algorithms, score_optimality, verify_attempt
from .task import EvalTask, make_hyper_task, make_task


def new_session(
    *,
    size: int = 3,
    depth: int = 8,
    seed: int = 0,
    kind: str = "3d",
    max_moves: int | None = None,
) -> dict[str, Any]:
    task = (
        make_hyper_task(depth, seed, max_moves, size=size, ndim=int(kind[0]) if kind[0].isdigit() else 4)
        if kind != "3d"
        else make_task(size, depth, seed, max_moves)
    )
    return session_from_task(task)


def resolve_ai_name(*candidates: Any) -> str | None:
    """Pick the first non-empty AI / agent / model name."""
    for raw in candidates:
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text[:80]
    for key in ("RUBIX_AI", "RUBIX_AGENT"):
        env = os.environ.get(key)
        if env and env.strip():
            return env.strip()[:80]
    return None


def ai_label(name: str | None) -> str:
    return name or "unspecified AI"


def _as_number(value: Any) -> float | None:
    if value is None or value is False:
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number != number:  # noqa: PLR0124 — NaN
        return None
    return number


def _as_int(value: Any) -> int | None:
    number = _as_number(value)
    if number is None:
        return None
    return int(number)


def sanitize_clicks(raw: Any, *, limit: int = 4000) -> list[dict[str, Any]] | None:
    if not isinstance(raw, list):
        return None
    out: list[dict[str, Any]] = []
    for item in raw[:limit]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "pointer")[:24]
        out.append(
            {
                "t": _as_int(item.get("t")),
                "x": _as_int(item.get("x")),
                "y": _as_int(item.get("y")),
                "button": _as_int(item.get("button")),
                "dbl": bool(item.get("dbl")),
                "kind": kind,
            }
        )
    return out


def collect_usage(progress: dict[str, Any], verified: dict[str, Any]) -> dict[str, Any]:
    """Clicks, steps, time, and optional token usage from the client payload."""
    clicks = sanitize_clicks(progress.get("clicks"))
    click_count = _as_int(progress.get("click_count"))
    if click_count is None and clicks is not None:
        click_count = len(clicks)
    raw_tokens = progress.get("tokens")
    tokens = raw_tokens if isinstance(raw_tokens, dict) else {}
    tokens_used = _as_int(progress.get("tokens_used"))
    if tokens_used is None:
        tokens_used = _as_int(tokens.get("used") or tokens.get("total") or tokens.get("tokens_used"))
    if tokens_used is None and not isinstance(raw_tokens, dict):
        tokens_used = _as_int(raw_tokens)
    token_cost = _as_number(
        progress.get("token_cost_usd")
        or progress.get("token_cost")
        or progress.get("cost_usd")
        or tokens.get("cost_usd")
        or tokens.get("cost")
    )
    step_count = verified.get("move_count")
    if step_count is None:
        step_count = len(verified.get("history") or [])
    usage = {
        "click_count": click_count,
        "step_count": step_count,
        "elapsed_sec": verified.get("elapsed_sec"),
        "tokens_used": tokens_used,
        "token_cost_usd": None if token_cost is None else round(token_cost, 6),
    }
    if clicks is not None:
        usage["clicks"] = clicks
    if verified.get("history") is not None:
        usage["history"] = verified["history"]
    return usage


def session_from_task(
    task: EvalTask,
    *,
    challenge_id: str | None = None,
    depth_label: str | None = None,
    ai: str | None = None,
) -> dict[str, Any]:
    return {
        "id": secrets.token_urlsafe(12),
        "kind": task.kind,
        "size": task.size,
        "ndim": getattr(task, "ndim", 3),
        "scramble_depth": task.scramble_depth,
        "seed": task.seed,
        "max_moves": task.max_moves,
        "state": task.state,
        "oracle": task.oracle_solution(),
        "challenge_id": challenge_id,
        "depth_label": depth_label,
        "ai": resolve_ai_name(ai),
        "lane": os.environ.get("RUBIX_LANE") or "open",
        "web_access": os.environ.get("RUBIX_WEB_ACCESS", "1") not in ("0", "false", "no"),
        "harness": os.environ.get("RUBIX_HARNESS") or "browser",
        "progress": None,
        "submitted": False,
        "started_at": time.time(),
    }


def session_from_challenge(challenge: Challenge) -> dict[str, Any]:
    return session_from_task(
        challenge.task,
        challenge_id=challenge.challenge_id,
        depth_label=challenge.depth_label,
    )


def random_visual_session(
    *,
    size: int | None = None,
    depth: int | str | None = None,
    kind: str = "3d",
) -> dict[str, Any]:
    challenge = request_challenge(
        size=size,
        depth=depth,
        kind=kind,
        visual=size is None and not (kind and kind[0].isdigit() and int(kind[0]) >= 5),
    )
    return session_from_challenge(challenge)


def bind_submit_body(session: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Ignore client-supplied move lists once the server owns the cube."""
    if session.get("server_history") is None:
        return body
    clicks = session.get("server_clicks") or body.get("clicks")
    return {
        **body,
        "history": session.get("server_history") or [],
        "clicks": clicks,
        "click_count": len(session.get("server_clicks") or []),
    }


def boot_payload(session: dict[str, Any]) -> dict[str, Any]:
    """Public boot for the in-browser cube. Oracle and seed stay on the server."""
    return {
        "id": session["id"],
        "kind": session["kind"],
        "size": session["size"],
        "ndim": session.get("ndim") or (3 if session.get("kind") == "3d" else 4),
        "state": session["state"],
        "github": "https://github.com/007vasy/rubix-eval",
        "issues": "https://github.com/007vasy/rubix-eval/issues",
    }


def grade_progress(
    session: dict[str, Any],
    progress: dict[str, Any],
    *,
    compare: bool = True,
    record: bool = False,
    time_limit: float = 1.5,
) -> dict[str, Any]:
    verified = verify_attempt(session, progress)
    started = session.get("started_at")
    if started is not None:
        verified["elapsed_sec"] = round(time.time() - float(started), 4)
    ai = resolve_ai_name(
        (progress or {}).get("ai"),
        (progress or {}).get("agent"),
        (progress or {}).get("model"),
        session.get("ai"),
    )
    verified["ai"] = ai
    verified.update(collect_usage(progress or {}, verified))
    depth = int(session["scramble_depth"])
    algorithms = compare_algorithms(session, time_limit=time_limit) if compare else []
    optimality = score_optimality(verified, algorithms) if compare else None
    payload = {
        "id": session["id"],
        "kind": session["kind"],
        "size": session["size"],
        "scramble_depth": depth,
        "solved": verified["solved"],
        "htm": verified["htm"],
        "qtm": verified["qtm"],
        "excess_htm": verified["excess_htm"],
        "efficiency": verified["efficiency"],
        "misplaced_stickers": verified["misplaced_stickers"],
        "max_moves": session["max_moves"],
        "challenge_id": session.get("challenge_id"),
        "depth_label": session.get("depth_label"),
        "submitted": True,
        "error": verified["error"],
        "moves": verified["moves"],
        "verified_from_history": verified["verified_from_history"],
        "algorithms": algorithms,
        "optimality": optimality,
        "elapsed_sec": verified.get("elapsed_sec"),
        "ai": ai_label(ai),
        "click_count": verified.get("click_count"),
        "step_count": verified.get("step_count"),
        "tokens_used": verified.get("tokens_used"),
        "token_cost_usd": verified.get("token_cost_usd"),
        "history": verified.get("history") or [],
    }
    if record:
        stored = make_record(session, verified, algorithms, optimality or {}, progress=progress)
        path = write_record(stored)
        payload["record_id"] = stored["record_id"]
        payload["record_path"] = str(path)
    return payload
