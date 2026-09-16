from __future__ import annotations

from rubix_eval.human_records import human_record, version_key
from rubix_eval.leaderboard import benchmark_slot, build_ai_leaderboard, build_leaderboard
from rubix_eval.visual_session import grade_progress, session_from_task
from rubix_eval.task import make_task


def test_human_records_cover_wca_sizes() -> None:
    assert version_key("3d", 3) == "3x3x3"
    assert version_key("4d", 3) == "3x3x3x3"
    rec = human_record("3d", 3)
    assert rec is not None
    assert rec["seconds"] == 2.76
    assert rec["person"] == "Teodor Zajder"
    assert human_record("3d", 2)["seconds"] == 0.39
    four = human_record("4d", 3)
    assert four is not None
    assert four["seconds"] == 93.52
    assert "Farkas" in four["person"]
    assert four["shortest_twists"] == 191
    assert human_record("3d", 40) is None


def test_leaderboard_full_includes_human_not_end_step() -> None:
    data = build_leaderboard(bench=False, visual_only=True)
    three = next(board for board in data["boards"] if board["version"] == "3x3x3")
    humans = [row for row in three["full"]["entries"] if row["kind"] == "human"]
    assert humans and humans[0]["seconds"] == 2.76
    assert humans[0].get("highlight") is True
    assert humans[0].get("badge") == "Human WR"
    assert three["end_steps"][0]["depth_label"] == "1"
    assert len(three["end_steps"]) == 10
    for slot in three["end_steps"]:
        assert "human" not in {a.get("kind") for a in slot["algorithms"]}
    groups = three["groups"]
    assert [g["depth_label"] for g in groups][-1] == "full"
    assert all(not g["full"] or any(e.get("highlight") for e in g["entries"]) for g in groups)
    d1 = next(g for g in groups if g["depth_label"] == "1")
    assert all(e["kind"] != "human" for e in d1["entries"])
    ranks = [e["rank"] for e in three["full"]["entries"]]
    assert ranks == list(range(1, len(ranks) + 1))
    times = [e["seconds"] for e in three["full"]["entries"]]
    assert times == sorted(times)


def test_end_step_slot_times_algorithms(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    slot = benchmark_slot("3d", 2, "2", seed=1, time_limit=1.0)
    names = {row["algorithm"] for row in slot["algorithms"]}
    assert "inverse_scramble" in names
    assert all(row["seconds"] >= 0 for row in slot["algorithms"])


def test_ai_elapsed_recorded_on_submit() -> None:
    session = session_from_task(make_task(2, 1, seed=1))
    assert session["started_at"]
    grade = grade_progress(session, {"history": []}, compare=False)
    assert grade["elapsed_sec"] is not None
    assert grade["elapsed_sec"] >= 0


def test_record_names_which_ai_solved(tmp_path, monkeypatch) -> None:
    from rubix_eval.records import list_records
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    session = session_from_task(make_task(2, 1, seed=1), ai="Grok 4.6")
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade = grade_progress(session, {"history": history}, compare=False, record=True)
    assert grade["ai"] == "Grok 4.6"
    assert grade["solved"] is True
    rows = list_records(tmp_path)
    assert rows[0]["ai"] == "Grok 4.6"


def test_ai_leaderboard_ranks_by_hardest_solve(tmp_path, monkeypatch) -> None:
    from rubix_eval.solvers import history_to_moves
    from rubix_eval.task import make_hyper_task

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))

    easy = session_from_task(make_task(2, 1, seed=1), ai="EasyBot")
    moves = history_to_moves("3d", easy["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade_progress(easy, {"history": history}, compare=False, record=True)

    hard = session_from_task(make_hyper_task(8, seed=1, size=3, ndim=4), ai="HardBot")
    grade_progress(hard, {"history": hard["oracle"]}, compare=False, record=True)

    board = build_ai_leaderboard(tmp_path)
    assert board["count"] == 2
    assert board["ais"][0]["ai"] == "HardBot"
    assert board["ais"][0]["rank"] == 1
    assert "3×3×3×3" in board["ais"][0]["hardest"]["puzzle"]
    assert board["ais"][1]["ai"] == "EasyBot"


def test_ai_leaderboard_skips_unnamed_solves(tmp_path, monkeypatch) -> None:
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    named = session_from_task(make_task(2, 1, seed=1), ai="NamedBot")
    moves = history_to_moves("3d", named["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade_progress(named, {"history": history}, compare=False, record=True)
    unnamed = session_from_task(make_task(3, 8, seed=1))
    grade_progress(unnamed, {"history": unnamed["oracle"]}, compare=False, record=True)
    board = build_ai_leaderboard(tmp_path)
    assert [row["ai"] for row in board["ais"]] == ["NamedBot"]
    assert "unspecified AI" not in {row["ai"] for row in board["ais"]}


def test_ai_leaderboard_splits_open_and_verified(tmp_path, monkeypatch) -> None:
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    open_sess = session_from_task(make_task(2, 1, seed=1), ai="BrowserBot")
    open_sess["lane"] = "open"
    moves = history_to_moves("3d", open_sess["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade_progress(open_sess, {"history": history}, compare=False, record=True)

    ver = session_from_task(make_task(3, 1, seed=1), ai="OfflineBot")
    ver["lane"] = "verified"
    ver["web_access"] = False
    ver["harness"] = "inspect"
    grade_progress(ver, {"history": ver["oracle"]}, compare=False, record=True)

    opened = build_ai_leaderboard(tmp_path, lane="open")
    verified = build_ai_leaderboard(tmp_path, lane="verified")
    assert [row["ai"] for row in opened["ais"]] == ["BrowserBot"]
    assert [row["ai"] for row in verified["ais"]] == ["OfflineBot"]
    assert opened["lane"] == "open"
    assert verified["lane"] == "verified"


def test_submit_body_overrides_ai_name() -> None:
    session = session_from_task(make_task(2, 1, seed=1), ai="Old Model")
    grade = grade_progress(
        session, {"history": [], "ai": "Claude"}, compare=False
    )
    assert grade["ai"] == "Claude"
