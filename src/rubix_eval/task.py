"""Eval task: an NxNxN cube scrambled a fixed number of steps from solved."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cube import Cube
from .metrics import GradeResult, grade_solution
from .moves import format_moves, invert_moves, parse_moves
from .render import ascii_net, legend
from .scramble import generate_scramble

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

    def cube(self) -> Cube:
        return Cube.from_dict(self.state)

    def prompt(self) -> str:
        cube = self.cube()
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
        moves = generate_scramble(self.size, self.scramble_depth, self.seed)
        return format_moves(invert_moves(moves))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "size": self.size,
            "scramble_depth": self.scramble_depth,
            "seed": self.seed,
            "state": self.state,
            "max_moves": self.max_moves,
            "metric": self.metric,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(self.dumps() + "\n", encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalTask:
        return cls(
            id=data["id"],
            size=int(data["size"]),
            scramble_depth=int(data["scramble_depth"]),
            seed=int(data["seed"]),
            state=data["state"],
            max_moves=int(data.get("max_moves") or default_max_moves(int(data["size"]))),
            metric=data.get("metric", "HTM"),
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
    parse_moves(text)  # validate
    return text
