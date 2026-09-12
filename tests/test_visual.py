from rubix_eval.visual_session import boot_payload, grade_progress, new_session, session_from_task
from rubix_eval.task import make_task


def test_boot_hides_scramble_and_oracle() -> None:
    session = new_session(size=3, depth=8, seed=1)
    boot = boot_payload(session)
    assert "oracle" not in boot
    assert "scramble_depth" not in boot
    assert "seed" not in boot
    assert boot["kind"] == "3d"
    assert boot["size"] == 3
    assert "faces" in boot["state"]
    assert session["oracle"]
    assert session["scramble_depth"] == 8


def test_boot_4d() -> None:
    session = new_session(kind="4d", depth=5, seed=2)
    boot = boot_payload(session)
    assert boot["kind"] == "4d"
    assert "cells" in boot["state"]
    assert "oracle" not in boot


def test_grade_progress_uses_server_depth() -> None:
    session = session_from_task(make_task(3, 8, 1))
    grade = grade_progress(session, {"solved": True, "htm": 10, "qtm": 12, "misplaced": 0})
    assert grade["solved"] is True
    assert grade["scramble_depth"] == 8
    assert grade["excess_htm"] == 2
    assert grade["efficiency"] == 0.8


def test_over_max_moves_not_solved() -> None:
    session = new_session(size=3, depth=2, seed=0, max_moves=3)
    grade = grade_progress(session, {"solved": True, "htm": 9, "qtm": 9, "misplaced": 0})
    assert grade["solved"] is False
    assert grade["error"]
