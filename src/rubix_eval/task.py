"""Eval task: an NxNxN cube scrambled a fixed number of steps from solved."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cube import Cube
from .hyper_moves import format_hyper_moves, invert_hyper_moves, parse_hyper_moves
from .hypercube import HyperCube
from .metrics import GradeResult, grade_solution
from .moves import format_moves, invert_moves, parse_moves
from .render import ascii_hyper_net, ascii_net, hyper_legend, legend
from .scramble import generate_hyper_scramble, generate_scramble

DEFAULT_MAX_MOVES = {
    2: 40,
    3: 80,
    4: 160,
    5: 240,
}


def default_max_moves(size: int) -> int:
    if size in DEFAULT_MAX_MOVES:
        return DEFAULT_MAX_MOVES[size]
    return max(40, size * size * 12)


@dataclass
class EvalTask:
    """Public puzzle given to the agent. The scramble sequence is withheld."""

    id: str
    size: int
    scramble_depth: int
    seed: int
    state: dict[str, Any]
    max_moves: int
    metric: str = "HTM"
    kind: str = "3d"

    ndim: int = 3

    def cube(self) -> Cube | HyperCube:
        if self.kind != "3d":
            return HyperCube.from_dict(self.state)
        return Cube.from_dict(self.state)

    def prompt(self) -> str:
        cube = self.cube()
        if self.kind != "3d":
            shape = "×".join([str(self.size)] * int(self.state.get("ndim", 4)))
            return "\n".join(
                [
                    f"Solve this {shape} ({self.kind}) Rubik's cube.",
                    f"It is {self.scramble_depth} random cell-twists away from solved.",
                    "Return Zhao notation: RU twists the R cell 90° around U; RU' and RU2 as usual.",
                    "Cells: R L U D F B I (inside) O (outside).",
                    f"Metric: {self.metric}. Stay under {self.max_moves} moves.",
                    hyper_legend(),
                    "",
                    ascii_hyper_net(cube),
                    "",
                    "JSON state:",
                    json.dumps(self.state, separators=(",", ":")),
                ]
            )
        return "\n".join(
            [
                f"Solve this {self.size}x{self.size}x{self.size} Rubik's cube.",
                f"It is {self.scramble_depth} random face/slice turns away from solved.",
                f"Return a move sequence in WCA notation (R, U', 2R, Rw, ...).",
                f"Metric: {self.metric}. Stay under {self.max_moves} moves.",
                legend(),
                "",
                ascii_net(cube),
                "",
                "JSON state:",
                json.dumps(self.state, separators=(",", ":")),
            ]
        )

    def grade(self, solution: str) -> GradeResult:
        return grade_solution(self.cube(), solution, self.scramble_depth, self.max_moves)

    def oracle_solution(self) -> str:
        """Invert the withheld scramble. Used to test the engine, not the agent."""
        if self.kind != "3d":
            ndim = int(self.state.get("ndim") or self.ndim or 4)
            moves = generate_hyper_scramble(
                self.scramble_depth, self.seed, size=self.size, ndim=ndim
            )
            return format_hyper_moves(invert_hyper_moves(moves))
        moves = generate_scramble(self.size, self.scramble_depth, self.seed)
        return format_moves(invert_moves(moves))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "size": self.size,
            "scramble_depth": self.scramble_depth,
            "seed": self.seed,
            "state": self.state,
            "max_moves": self.max_moves,
            "metric": self.metric,
            "ndim": self.ndim,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(self.dumps() + "\n", encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalTask:
        kind = data.get("kind") or data.get("state", {}).get("kind") or "3d"
        size = int(data.get("size") or 3)
        ndim = int(data.get("ndim") or data.get("state", {}).get("ndim") or (3 if kind == "3d" else 4))
        return cls(
            id=data["id"],
            size=size,
            scramble_depth=int(data["scramble_depth"]),
            seed=int(data["seed"]),
            state=data["state"],
            max_moves=int(data.get("max_moves") or (120 if kind != "3d" else default_max_moves(size))),
            metric=data.get("metric", "HTM"),
            kind=kind,
            ndim=ndim,
        )

    @classmethod
    def load(cls, path: str | Path) -> EvalTask:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def make_task(
    size: int,
    depth: int,
    seed: int = 0,
    max_moves: int | None = None,
) -> EvalTask:
    cube = Cube(size)
    scramble = generate_scramble(size, depth, seed)
    cube.apply(scramble)
    task_id = f"{size}x{size}x{size}-d{depth}-s{seed}"
    return EvalTask(
        id=task_id,
        size=size,
        scramble_depth=depth,
        seed=seed,
        state=cube.to_dict(),
        max_moves=max_moves if max_moves is not None else default_max_moves(size),
        kind="3d",
    )


def make_hyper_task(
    depth: int,
    seed: int = 0,
    max_moves: int | None = None,
    *,
    size: int = 3,
    ndim: int = 4,
) -> EvalTask:
    cube = HyperCube(size=size, ndim=ndim)
    scramble = generate_hyper_scramble(depth, seed, size=size, ndim=ndim)
    cube.apply(scramble)
    shape = "x".join([str(size)] * ndim)
    return EvalTask(
        id=f"{shape}-d{depth}-s{seed}",
        size=size,
        scramble_depth=depth,
        seed=seed,
        state=cube.to_dict(),
        max_moves=max_moves if max_moves is not None else max(120, size * ndim * 20),
        kind=f"{ndim}d",
        ndim=ndim,
    )


def load_solution(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8").strip()
    if text.startswith("{"):
        data = json.loads(text)
        if "solution" in data:
            return data["solution"]
        if "moves" in data:
            moves = data["moves"]
            return moves if isinstance(moves, str) else " ".join(moves)
    return " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))


def parse_solution(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    try:
        parse_moves(text)
    except ValueError:
        parse_hyper_moves(text)
    return text
