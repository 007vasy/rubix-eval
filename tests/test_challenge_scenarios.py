"""Two scenarios for every catalog challenge: a non-solve, and an n-step solve.

Non-solve: the agent hits Done without turning (computer-use empty history).
N-step solve: the withheld inverse scramble, which is exactly `scramble_depth`
turns — including one-step (d1) and deeper end-steps / full scrambles.

100×100×100 `full` is omitted: constructing and replaying 1200 turns takes ~15s.
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from rubix_eval.challenges import catalog, request_challenge
from rubix_eval.visual_session import grade_progress, session_from_challenge


def _scenario_catalog() -> list[dict]:
    rows = catalog() + catalog(kind="4d", visual=True)
    return [
        row
        for row in rows
        if not (row["size"] >= 100 and row["depth_label"] == "full")
    ]


SCENARIOS = _scenario_catalog()


@lru_cache(maxsize=None)
def _challenge(kind: str, size: int, depth_label: str):
    return request_challenge(
        size=size,
        depth="full" if depth_label == "full" else int(depth_label),
        kind=kind,
        seed=1,
    )


def _session(row: dict):
    challenge = _challenge(row["kind"], row["size"], row["depth_label"])
    assert challenge.challenge_id == row["id"]
    return session_from_challenge(challenge)


@pytest.mark.parametrize("row", SCENARIOS, ids=lambda row: f"{row['id']}-non-solve")
def test_challenge_non_solve(row: dict) -> None:
    session = _session(row)
    grade = grade_progress(
        session,
        {"solved": True, "htm": 0, "qtm": 0, "misplaced": 0, "history": []},
        compare=False,
    )
    assert grade["solved"] is False
    assert grade["verified_from_history"] is True
    assert grade["htm"] == 0
    assert grade["challenge_id"] == row["id"]
    assert grade["depth_label"] == row["depth_label"]
    assert grade["misplaced_stickers"] > 0
    assert grade["error"] is None


@pytest.mark.parametrize("row", SCENARIOS, ids=lambda row: f"{row['id']}-n-step-solve")
def test_challenge_n_step_solve(row: dict) -> None:
    session = _session(row)
    assert session["oracle"]
    grade = grade_progress(session, {"history": session["oracle"]}, compare=False)
    assert grade["solved"] is True
    assert grade["htm"] == row["scramble_depth"]
    assert grade["excess_htm"] == 0
    assert grade["misplaced_stickers"] == 0
    assert grade["challenge_id"] == row["id"]
    assert grade["depth_label"] == row["depth_label"]
    assert grade["error"] is None
    assert grade["verified_from_history"] is True
