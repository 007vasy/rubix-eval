"""Known cube-solving algorithms, used to score how optimal an attempt was."""

from __future__ import annotations

import time
from typing import Any

from .cube import Cube
from .hyper_moves import format_hyper_moves, parse_hyper_moves
from .hypercube import HyperCube
from .kociemba import solve_kociemba
from .metrics import step_cost
from .moves import Move, format_moves, parse_moves
from .search import solve_optimal


def history_to_moves(kind: str, history: Any, ndim: int | None = None) -> list:
    if not history:
        return []
    d = ndim if ndim is not None else (4 if kind != "3d" else 3)
    if isinstance(history, str):
        return parse_hyper_moves(history, ndim=d) if d >= 4 else parse_moves(history)
    moves = []
    for item in history:
        if isinstance(item, str):
            ndim = 4 if kind != "3d" else 3
            moves.extend(parse_hyper_moves(item, ndim=ndim) if ndim >= 4 else parse_moves(item))
            continue
        if kind != "3d":
            axis_cells = item.get("axisCells") or item.get("axis_cells") or ()
            axis = item.get("axis") or (axis_cells[0] if axis_cells else "")
            from .hyper_moves import HyperMove

            moves.append(
                HyperMove(
                    item["cell"],
                    axis,
                    int(item.get("turns", 1)),
                    int(item.get("order", 4)),
                    tuple(axis_cells),
                    item.get("layer"),
                )
            )
        else:
            moves.append(
                Move(
                    item["face"],
                    int(item.get("layer", 1)),
                    bool(item.get("wide", False)),
                    int(item.get("turns", 1)),
                )
            )
    return moves


def format_history(kind: str, moves: list) -> str:
    if kind != "3d":
        return format_hyper_moves(moves)
    return format_moves(moves)


def move_as_dict(kind: str, move: Any) -> dict[str, Any]:
    if kind != "3d":
        return {
            "cell": move.cell,
            "axis": move.axis,
            "turns": move.turns,
            "order": move.order,
            "axisCells": list(move.axis_cells),
            "layer": move.layer,
        }
    return {
        "face": move.face,
        "layer": move.layer,
        "wide": move.wide,
        "turns": move.turns,
    }


def history_as_dicts(kind: str, moves: list) -> list[dict[str, Any]]:
    return [move_as_dict(kind, move) for move in moves]


def verify_attempt(session: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    """Replay submitted clicks on the scramble. Do not trust the client counts."""
    kind = session["kind"]
    cube = HyperCube.from_dict(session["state"]) if kind != "3d" else Cube.from_dict(session["state"])
    error = None
    moves: list = []
    if progress.get("history") is not None or progress.get("moves") is not None:
        try:
            raw = progress.get("history")
            if raw is None:
                raw = progress.get("moves")
            moves = history_to_moves(kind, raw)
            cube.apply(moves)
        except (ValueError, KeyError, TypeError) as exc:
            error = str(exc)
            moves = []
            cube = HyperCube.from_dict(session["state"]) if kind != "3d" else Cube.from_dict(session["state"])
    if error is None and (progress.get("history") is not None or progress.get("moves") is not None):
        cost = step_cost(moves, int(session["scramble_depth"]))
        misplaced = cube.misplaced_stickers()
        htm, qtm = cost.htm, cost.qtm
        solved = cube.is_solved()
    else:
        htm = int(progress.get("htm") or 0)
        qtm = int(progress.get("qtm") or 0)
        misplaced = int(progress.get("misplaced") or cube.misplaced_stickers())
        solved = bool(progress.get("solved"))
        cost = None
    max_moves = session["max_moves"]
    over = max_moves is not None and htm > max_moves
    if over:
        solved = False
        error = error or f"over max_moves ({htm} > {max_moves})"
    depth = int(session["scramble_depth"])
    return {
        "solved": solved,
        "htm": htm,
        "qtm": qtm,
        "moves": format_history(kind, moves) if moves else (progress.get("moves") or ""),
        "move_count": len(moves) if moves else htm,
        "misplaced_stickers": misplaced,
        "excess_htm": htm - depth,
        "efficiency": round((depth / htm) if htm else (1.0 if depth == 0 else 0.0), 4),
        "error": error,
        "verified_from_history": bool(moves) or progress.get("history") == [],
        "history": history_as_dicts(kind, moves),
    }


def _algorithm_payload(name: str, label: str, moves: list, kind: str, scramble_depth: int, **extra: Any) -> dict[str, Any]:
    cost = step_cost(moves, scramble_depth)
    return {
        "algorithm": name,
        "label": label,
        "solved": True,
        "htm": cost.htm,
        "qtm": cost.qtm,
        "moves": format_history(kind, moves),
        "optimal": extra.pop("optimal", False),
        "error": extra.pop("error", None),
        **extra,
    }


def compare_algorithms(
    session: dict[str, Any],
    *,
    time_limit: float = 1.5,
) -> list[dict[str, Any]]:
    """Run known solvers on the scramble the agent saw."""
    kind = session["kind"]
    depth = int(session["scramble_depth"])
    cube = HyperCube.from_dict(session["state"]) if kind != "3d" else Cube.from_dict(session["state"])
    results: list[dict[str, Any]] = []

    oracle_text = session.get("oracle") or ""
    t0 = time.perf_counter()
    try:
        ndim = int(session.get("ndim") or (4 if kind != "3d" else 3))
        oracle_moves = (
            parse_hyper_moves(oracle_text, ndim=ndim) if kind != "3d" else parse_moves(oracle_text)
        )
        work = cube.copy()
        work.apply(oracle_moves)
    except ValueError:
        oracle_moves = []
        work = cube
    inverse_elapsed = round(time.perf_counter() - t0, 6)
    if oracle_moves or depth == 0:
        inverse_label = (
            "Inverse scramble (MC4D cheat-solve)"
            if kind != "3d"
            else "Inverse scramble"
        )
        results.append(
            _algorithm_payload(
                "inverse_scramble",
                inverse_label,
                oracle_moves,
                kind,
                depth,
                optimal=False,
                elapsed_sec=inverse_elapsed,
                verified=bool(oracle_moves) and work.is_solved(),
            )
        )

    try:
        god = solve_optimal(cube, time_limit=time_limit)
    except Exception as exc:  # noqa: BLE001 — eval must record solver failures
        god = {
            "algorithm": "god_htm",
            "label": "God's algorithm (HTM search)",
            "solved": False,
            "moves": [],
            "text": "",
            "htm": None,
            "optimal": False,
            "error": str(exc),
        }
    god_moves = god.get("moves") or []
    results.append(
        {
            "algorithm": "god_htm",
            "label": god.get("label") or "God's algorithm (HTM search)",
            "solved": bool(god.get("solved")),
            "htm": god.get("htm"),
            "qtm": step_cost(god_moves, depth).qtm if god_moves else None,
            "moves": god.get("text") or format_history(kind, god_moves),
            "optimal": bool(god.get("optimal") and god.get("solved")),
            "error": god.get("error"),
            "nodes": god.get("nodes"),
            "elapsed_sec": god.get("elapsed_sec"),
        }
    )

    if kind == "3d" and session["size"] == 3:
        try:
            koc = solve_kociemba(cube, time_limit=time_limit)
        except Exception as exc:  # noqa: BLE001
            koc = {
                "algorithm": "kociemba",
                "label": "Kociemba two-phase",
                "solved": False,
                "moves": [],
                "text": "",
                "htm": None,
                "optimal": False,
                "error": str(exc),
            }
        koc_moves = koc.get("moves") or []
        results.append(
            {
                "algorithm": "kociemba",
                "label": "Kociemba two-phase",
                "solved": bool(koc.get("solved")),
                "htm": koc.get("htm"),
                "qtm": step_cost(koc_moves, depth).qtm if koc_moves else None,
                "moves": koc.get("text") or format_history(kind, koc_moves),
                "optimal": False,
                "error": koc.get("error"),
                "elapsed_sec": koc.get("elapsed_sec"),
                "phase1_len": koc.get("phase1_len"),
                "phase2_len": koc.get("phase2_len"),
            }
        )
    return results


def score_optimality(verified: dict[str, Any], algorithms: list[dict[str, Any]]) -> dict[str, Any]:
    solved_algs = [row for row in algorithms if row.get("solved") and isinstance(row.get("htm"), int)]
    best = min(solved_algs, key=lambda row: row["htm"]) if solved_algs else None
    proven = next((row for row in solved_algs if row.get("optimal")), None)
    reference = proven or best
    ai_solved = bool(verified.get("solved"))
    ai_htm = int(verified.get("htm") or 0)
    out: dict[str, Any] = {
        "best_algorithm": reference["algorithm"] if reference else None,
        "best_label": reference["label"] if reference else None,
        "best_htm": reference["htm"] if reference else None,
        "proven_optimal_htm": proven["htm"] if proven else None,
        "ai_htm": ai_htm,
        "ai_solved": ai_solved,
        "excess_vs_best": None,
        "optimality_ratio": None,
        "optimal": False,
    }
    if ai_solved and reference is not None and ai_htm >= 0:
        out["excess_vs_best"] = ai_htm - reference["htm"]
        out["optimality_ratio"] = round((reference["htm"] / ai_htm) if ai_htm else 1.0, 4)
        out["optimal"] = proven is not None and ai_htm == proven["htm"]
    return out
