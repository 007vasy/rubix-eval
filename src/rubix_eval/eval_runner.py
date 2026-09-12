"""Batch eval runner. The solver never sees the scramble sequence."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .task import EvalTask, make_task

Solver = Callable[[EvalTask], str]

DEFAULT_SUITE = (
    # 2x2x2
    (2, 1),
    (2, 4),
    (2, 8),
    (2, 11),
    # 3x3x3
    (3, 1),
    (3, 5),
    (3, 10),
    (3, 15),
    (3, 20),
    # 4x4x4 ("big cube")
    (4, 1),
    (4, 5),
    (4, 10),
    # n x n x n samples
    (5, 5),
    (7, 5),
)


@dataclass
class TrialResult:
    task_id: str
    size: int
    scramble_depth: int
    seed: int
    solved: bool
    htm: int
    qtm: int
    excess_htm: int
    efficiency: float | None
    elapsed_sec: float
    error: str | None = None
    solution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "size": self.size,
            "scramble_depth": self.scramble_depth,
            "seed": self.seed,
            "solved": self.solved,
            "htm": self.htm,
            "qtm": self.qtm,
            "excess_htm": self.excess_htm,
            "efficiency": self.efficiency,
            "elapsed_sec": round(self.elapsed_sec, 4),
            "error": self.error,
            "solution": self.solution,
        }


@dataclass
class SuiteReport:
    results: list[TrialResult] = field(default_factory=list)

    @property
    def solved(self) -> int:
        return sum(1 for row in self.results if row.solved)

    @property
    def total(self) -> int:
        return len(self.results)

    def summary(self) -> dict[str, Any]:
        solved_rows = [row for row in self.results if row.solved]
        mean_htm = (
            sum(row.htm for row in solved_rows) / len(solved_rows) if solved_rows else None
        )
        mean_excess = (
            sum(row.excess_htm for row in solved_rows) / len(solved_rows) if solved_rows else None
        )
        return {
            "solved": self.solved,
            "total": self.total,
            "solve_rate": round(self.solved / self.total, 4) if self.total else 0.0,
            "mean_htm_solved": None if mean_htm is None else round(mean_htm, 3),
            "mean_excess_htm_solved": None if mean_excess is None else round(mean_excess, 3),
            "results": [row.to_dict() for row in self.results],
        }


def build_suite(
    sizes: Iterable[int] | None = None,
    depths: Iterable[int] | None = None,
    trials: int = 1,
    seed: int = 0,
    pairs: Iterable[tuple[int, int]] | None = None,
) -> list[EvalTask]:
    if pairs is None:
        if sizes is None and depths is None:
            pairs = DEFAULT_SUITE
        else:
            size_list = list(sizes or (2, 3, 4))
            depth_list = list(depths or (1, 5, 10))
            pairs = [(size, depth) for size in size_list for depth in depth_list]
    tasks: list[EvalTask] = []
    index = 0
    for size, depth in pairs:
        for trial in range(trials):
            tasks.append(make_task(size, depth, seed=seed + index))
            index += 1
    return tasks


def run_task(task: EvalTask, solver: Solver, timeout: float | None = None) -> TrialResult:
    started = time.perf_counter()
    error = None
    solution = ""
    try:
        solution = solver(task)
        grade = task.grade(solution)
        elapsed = time.perf_counter() - started
        if timeout is not None and elapsed > timeout:
            error = f"timeout ({elapsed:.2f}s > {timeout}s)"
        return TrialResult(
            task_id=task.id,
            size=task.size,
            scramble_depth=task.scramble_depth,
            seed=task.seed,
            solved=grade.solved and error is None,
            htm=grade.cost.htm,
            qtm=grade.cost.qtm,
            excess_htm=grade.cost.excess_htm,
            efficiency=grade.cost.efficiency,
            elapsed_sec=elapsed,
            error=error or grade.error,
            solution=" ".join(grade.applied),
        )
    except Exception as exc:  # noqa: BLE001 — eval must record solver failures
        elapsed = time.perf_counter() - started
        return TrialResult(
            task_id=task.id,
            size=task.size,
            scramble_depth=task.scramble_depth,
            seed=task.seed,
            solved=False,
            htm=0,
            qtm=0,
            excess_htm=-task.scramble_depth,
            efficiency=0.0,
            elapsed_sec=elapsed,
            error=str(exc),
            solution=solution,
        )


def command_solver(command: list[str], workdir: Path | None = None) -> Solver:
    """Solver that writes the task JSON to stdin and reads moves from stdout."""

    def solve(task: EvalTask) -> str:
        env = os.environ.copy()
        env["RUBIX_TASK_ID"] = task.id
        result = subprocess.run(
            command,
            input=task.dumps(),
            text=True,
            capture_output=True,
            cwd=workdir,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"solver exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )
        return result.stdout.strip()

    return solve


def oracle_solver(task: EvalTask) -> str:
    return task.oracle_solution()


def run_suite(
    tasks: list[EvalTask],
    solver: Solver,
    timeout: float | None = None,
) -> SuiteReport:
    report = SuiteReport()
    for task in tasks:
        report.results.append(run_task(task, solver, timeout=timeout))
    return report


def write_report(report: SuiteReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report.summary(), indent=2) + "\n", encoding="utf-8")
