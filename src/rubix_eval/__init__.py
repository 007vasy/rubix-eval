"""rubix-eval: NxNxN Rubik's cube engine and offline agent evaluation."""

from .cube import Cube
from .hyper_moves import HyperMove, parse_hyper_moves
from .hypercube import HyperCube
from .metrics import grade_solution, step_cost
from .moves import Move, invert_moves, parse_moves
from .scramble import generate_hyper_scramble, generate_scramble
from .task import EvalTask, make_hyper_task, make_task

__version__ = "0.1.0"

__all__ = [
    "Cube",
    "EvalTask",
    "HyperCube",
    "HyperMove",
    "Move",
    "generate_hyper_scramble",
    "generate_scramble",
    "grade_solution",
    "invert_moves",
    "make_hyper_task",
    "make_task",
    "parse_hyper_moves",
    "parse_moves",
    "step_cost",
]
