"""rubix-eval: NxNxN Rubik's cube engine and offline agent evaluation."""

from .cube import Cube
from .metrics import grade_solution, step_cost
from .moves import Move, parse_moves, invert_moves
from .scramble import generate_scramble
from .task import EvalTask, make_task

__version__ = "0.1.0"

__all__ = [
    "Cube",
    "EvalTask",
    "Move",
    "generate_scramble",
    "grade_solution",
    "invert_moves",
    "make_task",
    "parse_moves",
    "step_cost",
]
