"""Visual-only eval sessions. The page never receives the scramble or oracle."""

from __future__ import annotations

import secrets
from typing import Any

from .challenges import Challenge, request_challenge
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
        make_hyper_task(depth, seed, max_moves)
        if kind == "4d"
        else make_task(size, depth, seed, max_moves)
    )
    return session_from_task(task)


def session_from_task(
    task: EvalTask,
    *,
    challenge_id: str | None = None,
    depth_label: str | None = None,
) -> dict[str, Any]:
    return {
        "id": secrets.token_urlsafe(12),
        "kind": task.kind,
        "size": task.size,
        "scramble_depth": task.scramble_depth,
        "seed": task.seed,
        "max_moves": task.max_moves,
        "state": task.state,
        "oracle": task.oracle_solution(),
        "challenge_id": challenge_id,
        "depth_label": depth_label,
        "progress": None,
        "submitted": False,
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
        visual=size is None,
    )
    return session_from_challenge(challenge)


def boot_payload(session: dict[str, Any]) -> dict[str, Any]:
    """What the visual page is allowed to know: enough to draw, nothing else."""
    return {
        "id": session["id"],
        "kind": session["kind"],
        "size": session["size"],
        "state": session["state"],
    }


def grade_progress(session: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    htm = int(progress.get("htm") or 0)
    qtm = int(progress.get("qtm") or 0)
    depth = int(session["scramble_depth"])
    solved = bool(progress.get("solved"))
    misplaced = int(progress.get("misplaced") or 0)
    max_moves = session["max_moves"]
    over = max_moves is not None and htm > max_moves
    return {
        "id": session["id"],
        "kind": session["kind"],
        "size": session["size"],
        "scramble_depth": depth,
        "solved": solved and not over,
        "htm": htm,
        "qtm": qtm,
        "excess_htm": htm - depth,
        "efficiency": round((depth / htm) if htm else (1.0 if depth == 0 else 0.0), 4),
        "misplaced_stickers": misplaced,
        "max_moves": max_moves,
        "challenge_id": session.get("challenge_id"),
        "depth_label": session.get("depth_label"),
        "submitted": True,
        "error": f"over max_moves ({htm} > {max_moves})" if over else None,
    }
