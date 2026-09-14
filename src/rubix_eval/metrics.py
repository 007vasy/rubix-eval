"""Step-cost metrics for a solution attempt."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cube import Cube
from .hyper_moves import HyperMove, parse_hyper_moves
from .moves import Move, parse_moves


@dataclass
class StepCost:
    """How expensive a solution is in standard cube metrics."""

    htm: int
    qtm: int
    scramble_depth: int
    excess_htm: int
    efficiency: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "htm": self.htm,
            "qtm": self.qtm,
            "scramble_depth": self.scramble_depth,
            "excess_htm": self.excess_htm,
            "efficiency": self.efficiency,
        }


@dataclass
class GradeResult:
    solved: bool
    move_count: int
    applied: list[str]
    cost: StepCost
    misplaced_stickers: int
    size: int
    error: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "solved": self.solved,
            "move_count": self.move_count,
            "applied": self.applied,
            "cost": self.cost.to_dict(),
            "misplaced_stickers": self.misplaced_stickers,
            "size": self.size,
            "error": self.error,
            **self.extras,
        }


def step_cost(moves: list[Move] | list[HyperMove], scramble_depth: int) -> StepCost:
    htm = sum(move.htm_cost() for move in moves)
    qtm = sum(move.qtm_cost() for move in moves)
    excess = htm - scramble_depth
    efficiency = (scramble_depth / htm) if htm else (1.0 if scramble_depth == 0 else 0.0)
    return StepCost(
        htm=htm,
        qtm=qtm,
        scramble_depth=scramble_depth,
        excess_htm=excess,
        efficiency=round(efficiency, 4),
    )


def grade_solution(
    cube: Cube,
    solution: str | list[Move] | list[HyperMove],
    scramble_depth: int,
    max_moves: int | None = None,
) -> GradeResult:
    """Apply `solution` to a scrambled cube and measure cost.

    The cube is copied; the caller's cube is not mutated.
    """
    work = cube.copy()
    if getattr(cube, "ndim", 3) >= 4:
        parse = lambda text: parse_hyper_moves(text, ndim=int(cube.ndim))
    else:
        parse = parse_moves
    try:
        moves = parse(solution) if isinstance(solution, str) else list(solution)
    except ValueError as exc:
        return GradeResult(
            solved=False,
            move_count=0,
            applied=[],
            cost=step_cost([], scramble_depth),
            misplaced_stickers=work.misplaced_stickers(),
            size=work.size,
            error=str(exc),
        )
    if max_moves is not None and len(moves) > max_moves:
        return GradeResult(
            solved=False,
            move_count=len(moves),
            applied=[m.notation() for m in moves],
            cost=step_cost(moves, scramble_depth),
            misplaced_stickers=work.misplaced_stickers(),
            size=work.size,
            error=f"solution has {len(moves)} moves; max_moves is {max_moves}",
        )
    work.apply(moves)
    return GradeResult(
        solved=work.is_solved(),
        move_count=len(moves),
        applied=[m.notation() for m in moves],
        cost=step_cost(moves, scramble_depth),
        misplaced_stickers=work.misplaced_stickers(),
        size=work.size,
    )
