from __future__ import annotations

from rubix_eval.cube import Cube
from rubix_eval.kociemba import solve_kociemba
from rubix_eval.records import list_records
from rubix_eval.search import solve_optimal
from rubix_eval.solvers import compare_algorithms, history_to_moves, score_optimality, verify_attempt
from rubix_eval.task import make_task
from rubix_eval.visual_session import grade_progress, session_from_task


def test_history_replay_does_not_trust_client() -> None:
    session = session_from_task(make_task(3, 1, seed=1))
    fake = {"solved": True, "htm": 1, "qtm": 1, "misplaced": 0, "history": []}
    verified = verify_attempt(session, fake)
    assert verified["solved"] is False
    assert verified["htm"] == 0
    assert verified["verified_from_history"] is True


def test_history_to_moves_keeps_hyper_layer() -> None:
    moves = history_to_moves(
        "4d",
        [{"cell": "R", "axis": "U", "turns": 1, "order": 4, "axisCells": ["U"], "layer": 2}],
    )
    assert moves[0].layer == 2
    assert moves[0].cell == "R"


def test_history_oracle_solves() -> None:
    task = make_task(3, 4, seed=2)
    session = session_from_task(task)
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    verified = verify_attempt(session, {"history": history})
    assert verified["solved"] is True
    assert verified["htm"] == 4


def test_optimal_search_matches_or_beats_oracle_small() -> None:
    task = make_task(3, 4, seed=3)
    result = solve_optimal(task.cube(), time_limit=2.0)
    assert result["solved"] is True
    assert result["optimal"] is True
    assert result["htm"] <= 4
    work = task.cube()
    work.apply(result["moves"])
    assert work.is_solved()


def test_kociemba_solves_3x3() -> None:
    task = make_task(3, 8, seed=4)
    result = solve_kociemba(task.cube(), time_limit=4.0)
    assert result["solved"] is True
    assert result["htm"] >= 1
    work = task.cube()
    work.apply(result["moves"])
    assert work.is_solved()


def test_compare_and_record(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    task = make_task(3, 3, seed=5)
    session = session_from_task(task)
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade = grade_progress(session, {"history": history}, compare=True, record=True, time_limit=3.0)
    assert grade["solved"] is True
    assert grade["record_id"]
    assert grade["optimality"]["best_htm"] <= 3
    assert grade["optimality"]["ai_htm"] == 3
    names = {row["algorithm"] for row in grade["algorithms"]}
    assert "inverse_scramble" in names
    assert "god_htm" in names
    assert "kociemba" in names
    rows = list_records(tmp_path)
    assert len(rows) == 1
    assert rows[0]["solved"] is True


def test_unsolved_still_gets_baselines() -> None:
    session = session_from_task(make_task(2, 2, seed=1))
    algs = compare_algorithms(session, time_limit=1.0)
    opt = score_optimality({"solved": False, "htm": 0}, algs)
    assert opt["ai_solved"] is False
    assert opt["best_htm"] is not None
    assert opt["optimality_ratio"] is None


def test_kociemba_identity() -> None:
    result = solve_kociemba(Cube(3), time_limit=1.0)
    assert result["solved"] is True
    assert result["htm"] == 0
