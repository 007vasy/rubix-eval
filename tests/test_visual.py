from rubix_eval.visual_session import (
    bind_submit_body,
    boot_payload,
    grade_progress,
    new_session,
    session_from_task,
)
from rubix_eval.task import make_task


def test_http_task_endpoint_is_blocked() -> None:
    from pathlib import Path

    src = Path("src/rubix_eval/serve.py").read_text(encoding="utf-8")
    chunk = src.split('if path == "/api/task":', 1)[1][:500]
    assert "cubie JSON is not served over HTTP" in chunk
    assert "task.to_dict()" not in chunk


def test_boot_hides_scramble_and_oracle() -> None:
    session = new_session(size=3, depth=8, seed=1)
    boot = boot_payload(session)
    assert "oracle" not in boot
    assert "scramble_depth" not in boot
    assert "seed" not in boot
    assert boot["kind"] == "3d"
    assert boot["size"] == 3
    assert "oracle" not in boot
    assert "seed" not in boot
    assert "scramble_depth" not in boot
    assert boot["depth"] == "8"
    assert "state" in boot
    assert boot["github"].startswith("https://github.com/")
    assert session["oracle"]
    assert session["scramble_depth"] == 8


def test_boot_4d() -> None:
    session = new_session(kind="4d", depth=5, seed=2)
    boot = boot_payload(session)
    assert boot["kind"] == "4d"
    assert boot["depth"] == "5"
    assert "state" in boot
    assert "oracle" not in boot
    assert "seed" not in boot


def test_url_picks_size_and_turns() -> None:
    from rubix_eval.visual_session import random_visual_session

    session = random_visual_session(size=2, depth=1, kind="3d")
    boot = boot_payload(session)
    assert boot["kind"] == "3d"
    assert boot["size"] == 2
    assert boot["depth"] == "1"
    four = random_visual_session(size=3, depth="full", kind="4d")
    boot4 = boot_payload(four)
    assert boot4["kind"] == "4d"
    assert boot4["size"] == 3
    assert boot4["depth"] == "full"


def test_submit_ignores_client_history_when_server_owns_cube() -> None:
    session = new_session(size=3, depth=1, seed=1)
    session["server_history"] = []
    session["server_clicks"] = [{"x": 1, "y": 2, "button": 0, "kind": "pointer"}]
    body = bind_submit_body(session, {"history": session["oracle"], "solved": True})
    assert body["history"] == []
    assert body["click_count"] == 1


def test_grade_progress_uses_server_depth() -> None:
    session = session_from_task(make_task(3, 8, 1))
    grade = grade_progress(
        session, {"solved": True, "htm": 10, "qtm": 12, "misplaced": 0}, compare=False
    )
    assert grade["solved"] is True
    assert grade["scramble_depth"] == 8
    assert grade["excess_htm"] == 2
    assert grade["efficiency"] == 0.8


def test_solved_over_max_moves_counts_solved() -> None:
    session = new_session(size=3, depth=2, seed=0, max_moves=1)
    grade = grade_progress(session, {"history": session["oracle"]}, compare=False)
    assert grade["solved"] is True
    assert grade["misplaced_stickers"] == 0
    assert grade["htm"] > session["max_moves"]
    assert not grade["error"]


def test_unsolved_over_max_moves_stays_unsolved() -> None:
    session = new_session(size=3, depth=2, seed=0, max_moves=1)
    grade = grade_progress(
        session,
        {"history": [{"face": "R", "layer": 1, "wide": False, "turns": 1}] * 5},
        compare=False,
    )
    assert grade["solved"] is False
    assert grade["htm"] > session["max_moves"]


def test_submit_records_clicks_tokens_and_history(tmp_path, monkeypatch) -> None:
    from rubix_eval.leaderboard import build_ai_leaderboard
    from rubix_eval.records import load_record, public_record
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    session = session_from_task(make_task(2, 1, seed=1), ai="ReplayBot")
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade = grade_progress(
        session,
        {
            "history": history,
            "clicks": [{"t": 12, "x": 640, "y": 400, "button": 0, "kind": "pointer"}],
            "tokens_used": 45319,
            "token_cost_usd": 0.12,
        },
        compare=False,
        record=True,
    )
    assert grade["solved"] is True
    assert grade["click_count"] == 1
    assert grade["step_count"] == 1
    assert grade["tokens_used"] == 45319
    assert grade["token_cost_usd"] == 0.12
    assert grade["history"][0]["face"] == history[0]["face"]
    rec = load_record(grade["record_id"], tmp_path)
    assert rec["attempt"]["clicks"][0]["x"] == 640
    assert rec["attempt"]["history"]
    pub = public_record(rec)
    assert "oracle" not in pub
    assert pub["attempt"]["history"]
    board = build_ai_leaderboard(tmp_path)
    hardest = board["ais"][0]["hardest"]
    assert hardest["click_count"] == 1
    assert hardest["tokens_used"] == 45319
    assert hardest["record_id"] == grade["record_id"]


def test_verified_lane_forces_no_web_access(monkeypatch) -> None:
    monkeypatch.setenv("RUBIX_LANE", "verified")
    monkeypatch.setenv("RUBIX_WEB_ACCESS", "1")
    session = session_from_task(make_task(2, 1, seed=1), ai="OfflineBot")
    assert session["lane"] == "verified"
    assert session["web_access"] is False
    assert session["harness"] == "openshell"
