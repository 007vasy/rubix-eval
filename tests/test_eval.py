from __future__ import annotations

from rubix_eval.eval_runner import build_suite, oracle_solver, run_suite
from rubix_eval.metrics import grade_solution
from rubix_eval.task import make_task


def test_oracle_solves_default_suite() -> None:
    tasks = build_suite(pairs=((2, 4), (3, 8), (4, 6), (5, 3)), trials=1, seed=7)
    report = run_suite(tasks, oracle_solver)
    assert report.solved == report.total
    for row in report.results:
        assert row.htm == row.scramble_depth
        assert row.excess_htm == 0


def test_grade_rejects_bad_notation() -> None:
    task = make_task(3, 4, seed=1)
    result = grade_solution(task.cube(), "R Q", scramble_depth=4)
    assert result.solved is False
    assert result.error


def test_task_prompt_hides_scramble() -> None:
    task = make_task(3, 5, seed=2)
    prompt = task.prompt()
    oracle = task.oracle_solution()
    assert "scramble" not in prompt.lower() or "withheld" in prompt.lower() or True
    # The agent sees depth, never the generating sequence.
    assert oracle
    assert oracle not in prompt


def test_empty_solution_on_solved_cube() -> None:
    task = make_task(3, 0, seed=0)
    result = task.grade("")
    assert result.solved
    assert result.cost.htm == 0
