from pathlib import Path

from inspect_ai import eval as inspect_eval

from rubix_eval.inspect_eval import (
    copy_target,
    cube_grade,
    grade_completion,
    rubix,
    rubix_visual,
    samples_from_suite,
)
from rubix_eval.task import make_task


def test_grade_completion_oracle_solves() -> None:
    task = make_task(3, 1, seed=1)
    score = grade_completion(task.oracle_solution(), {
        "kind": "3d",
        "state": task.state,
        "scramble_depth": 1,
        "max_moves": task.max_moves,
    })
    assert score.value == "C"
    assert score.metadata["solved"] is True
    assert score.metadata["htm"] == 1


def test_grade_completion_solved_over_max_moves() -> None:
    task = make_task(3, 2, seed=0, max_moves=1)
    score = grade_completion(
        task.oracle_solution(),
        {
            "kind": "3d",
            "state": task.state,
            "scramble_depth": 2,
            "max_moves": 1,
        },
    )
    assert score.value == "C"
    assert score.metadata["solved"] is True
    assert score.metadata["htm"] > 1


def test_grade_completion_wrong_moves_unsolved() -> None:
    task = make_task(3, 2, seed=2)
    score = grade_completion("R", {
        "kind": "3d",
        "state": task.state,
        "scramble_depth": 2,
        "max_moves": task.max_moves,
    })
    assert score.value == "I"
    assert score.metadata["solved"] is False


def test_samples_hide_oracle_from_prompt() -> None:
    samples = samples_from_suite(sizes="3", depths="3", trials=1, seed=0)
    assert samples
    sample = samples[0]
    oracle = str(sample.target)
    assert oracle
    assert "oracle" not in sample.input.lower()
    assert f"solution: {oracle}" not in sample.input.lower()
    assert "oracle" not in (sample.metadata or {})
    assert "state" in (sample.metadata or {})


def test_inspect_text_task_oracle_solver(tmp_path: Path) -> None:
    logs = inspect_eval(
        rubix(sizes="3", depths="1", trials=1, seed=1),
        solver=copy_target(),
        model="mockllm/model",
        log_dir=str(tmp_path),
        display="none",
    )
    assert len(logs) == 1
    log = logs[0]
    assert log.status == "success"
    scores = log.results.scores
    assert scores
    accuracy = scores[0].metrics["accuracy"].value
    assert accuracy == 1.0


def test_inspect_visual_task_oracle_solver(tmp_path: Path) -> None:
    logs = inspect_eval(
        rubix_visual(sizes="2", depths="1", trials=1, seed=3),
        solver=[copy_target()],
        model="mockllm/model",
        log_dir=str(tmp_path),
        display="none",
    )
    log = logs[0]
    assert log.status == "success"
    assert log.results.scores[0].metrics["accuracy"].value == 1.0


def test_cube_grade_registered() -> None:
    assert callable(cube_grade())
