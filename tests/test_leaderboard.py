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


def test_publish_verified_rewrites_lane(tmp_path, monkeypatch) -> None:
    from rubix_eval.records import load_record, publish_verified
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    monkeypatch.setenv("RUBIX_LANE", "verified")
    session = session_from_task(make_task(2, 1, seed=1), ai="OfflineBot")
    assert session["lane"] == "verified"
    assert session["web_access"] is False
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade = grade_progress(session, {"history": history}, compare=False, record=True)
    rec = publish_verified(grade["record_id"], tmp_path)
    assert rec["lane"] == "verified"
    assert rec["web_access"] is False
    assert rec["attested"] is True
    stored = load_record(grade["record_id"], tmp_path)
    assert stored["lane"] == "verified"


def test_publish_verified_rejects_open_lane(tmp_path, monkeypatch) -> None:
    from rubix_eval.records import publish_verified
    from rubix_eval.solvers import history_to_moves

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    monkeypatch.delenv("RUBIX_LANE", raising=False)
    session = session_from_task(make_task(2, 1, seed=1), ai="BrowserBot")
    moves = history_to_moves("3d", session["oracle"])
    history = [{"face": m.face, "layer": m.layer, "wide": m.wide, "turns": m.turns} for m in moves]
    grade = grade_progress(session, {"history": history}, compare=False, record=True)
    try:
        publish_verified(grade["record_id"], tmp_path)
    except ValueError as exc:
        assert "refusing to attest" in str(exc)
    else:
        raise AssertionError("open records must not be attested")


def test_verified_depth_chart_shows_the_gap_to_full(tmp_path) -> None:
    import json

    from rubix_eval.leaderboard import verified_depth_chart

    def write(name, **fields):
        record = {
            "record_id": name,
            "ai": "Model",
            "lane": "verified",
            "kind": "4d",
            "size": 2,
            "ndim": 4,
            "attempt": {"solved": True, "htm": 12, "history": [{"turns": 1}]},
        }
        record.update(fields)
        (tmp_path / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")

    write("full", ai="Fable", depth_label="full", scramble_depth=20)
    write("ten", ai="Fable", depth_label="10", scramble_depth=10, attempt={"solved": True, "htm": 30})
    write("miss", ai="Astra", depth_label="5", scramble_depth=5, attempt={"solved": False, "htm": 4})
    write("open", ai="Grok 4.6", lane="open", depth_label="2", scramble_depth=2)
    write("other", ai="Other", kind="3d", size=3, ndim=3, depth_label="2", scramble_depth=2)

    chart = verified_depth_chart("4d", tmp_path)
    assert chart["full_turns"] == 20
    assert chart["title"] == "2×2×2×2"
    by_name = {row["ai"]: row for row in chart["models"]}
    assert set(by_name) == {"Fable", "Astra", "Grok 4.6"}
    assert by_name["Fable"]["solved_turns"] == 20
    assert by_name["Fable"]["gap_turns"] == 0
    assert by_name["Fable"]["reached_full"] is True
    assert by_name["Fable"]["lane"] == "verified"
    assert by_name["Astra"]["solved_turns"] == 0
    assert by_name["Astra"]["gap_turns"] == 20
    assert by_name["Grok 4.6"]["solved_turns"] == 2
    assert by_name["Grok 4.6"]["lane"] == "open"
    assert by_name["Grok 4.6"]["gap_turns"] == 18
    assert chart["models"][0]["ai"] == "Fable"

    three = verified_depth_chart("3d", tmp_path)
    assert three["full_turns"] == 25
    assert [row["ai"] for row in three["models"]] == ["Other"]
    assert three["models"][0]["solved_turns"] == 2
    assert three["models"][0]["gap_turns"] == 23


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


class _FakeBlob:
    def __init__(self, bucket, name, payload, generation):
        self.bucket, self.name, self.payload, self.generation = bucket, name, payload, generation

    def download_as_text(self):
        self.bucket.downloads.append(self.name)
        return self.payload


class _FakeBucket:
    name = "fake-solves"

    def __init__(self):
        self.blobs = {}
        self.downloads = []
        self.listings = 0

    def put(self, name, record, generation=1):
        import json

        self.blobs[name] = _FakeBlob(self, name, json.dumps(record), generation)

    def list_blobs(self):
        self.listings += 1
        return list(self.blobs.values())


def _bucket_record(record_id, ai="Model", solved=True, lane="open"):
    return {
        "record_id": record_id,
        "ai": ai,
        "kind": "3d",
        "size": 3,
        "scramble_depth": 2,
        "depth_label": "2",
        "lane": lane,
        "attempt": {"solved": solved, "htm": 2, "elapsed_sec": 12.5},
    }


def test_bucket_records_are_cached_and_only_changed_blobs_refetched(monkeypatch) -> None:
    from rubix_eval import records

    bucket = _FakeBucket()
    bucket.put("open/20260101T000000-a.json", _bucket_record("20260101T000000-a"))
    bucket.put("verified/20260102T000000-b.json", _bucket_record("20260102T000000-b", lane="verified"))
    bucket.put("open/solves.jsonl", {"ignored": True})
    monkeypatch.setattr(records, "_gcs_bucket", lambda: bucket)
    monkeypatch.setattr(records, "_bucket_cache", {"bucket": None, "listed_at": None, "records": {}})
    monkeypatch.setattr(records, "BUCKET_TTL_SEC", 60.0)

    rows = records.list_records()
    assert [r["record_id"] for r in rows] == ["20260102T000000-b", "20260101T000000-a"]
    assert records.load_record("20260101T000000-a")["ai"] == "Model"
    records.list_records()
    assert bucket.listings == 1  # inside the TTL nothing goes back to the bucket
    assert sorted(bucket.downloads) == ["open/20260101T000000-a.json", "verified/20260102T000000-b.json"]

    monkeypatch.setattr(records, "BUCKET_TTL_SEC", 0.0)
    bucket.downloads.clear()
    bucket.put("open/20260101T000000-a.json", _bucket_record("20260101T000000-a", ai="Renamed"), generation=2)
    bucket.put("open/20260103T000000-c.json", _bucket_record("20260103T000000-c"))
    del bucket.blobs["verified/20260102T000000-b.json"]
    rows = records.list_records()
    assert [r["record_id"] for r in rows] == ["20260103T000000-c", "20260101T000000-a"]
    assert rows[1]["ai"] == "Renamed"
    assert sorted(bucket.downloads) == ["open/20260101T000000-a.json", "open/20260103T000000-c.json"]
    assert records.load_record("20260102T000000-b") is None


def test_ai_board_is_built_from_summaries_without_refetching(monkeypatch) -> None:
    from rubix_eval import leaderboard, records

    bucket = _FakeBucket()
    bucket.put("open/20260101T000000-a.json", _bucket_record("20260101T000000-a", ai="Speedy"))
    bucket.put("open/20260101T000001-x.json", _bucket_record("20260101T000001-x", ai="Slowpoke", solved=False))
    monkeypatch.setattr(records, "_gcs_bucket", lambda: bucket)
    monkeypatch.setattr(records, "_bucket_cache", {"bucket": None, "listed_at": None, "records": {}})
    grouped = leaderboard._ai_solves()
    (row,) = grouped["3x3x3"]["2"]
    assert (row["who"], row["seconds"], row["htm"]) == ("Speedy", 12.5, 2)
    assert len(bucket.downloads) == 2


def test_bundled_bench_covers_every_board_and_newest_wins(tmp_path, monkeypatch) -> None:
    import json

    from rubix_eval import leaderboard
    from rubix_eval.challenges import VISUAL_SIZES
    from rubix_eval.human_records import version_key

    bundled = json.loads(leaderboard.BUNDLED_BENCH.read_text(encoding="utf-8"))
    for kind, size, ndim in leaderboard.versions_for(VISUAL_SIZES):
        slots = bundled["versions"][version_key(kind, size, ndim)]
        assert slots["full"]["algorithms"], (kind, size, ndim)

    monkeypatch.setenv("RUBIX_SOLVES_DIR", str(tmp_path))
    assert leaderboard.load_bench()["updated_at"] == bundled["updated_at"]
    (tmp_path / "algorithm_bench.json").write_text(json.dumps({"updated_at": "1999-01-01", "versions": {}}))
    assert leaderboard.load_bench()["updated_at"] == bundled["updated_at"]
    (tmp_path / "algorithm_bench.json").write_text(json.dumps({"updated_at": "2999-01-01", "versions": {}}))
    assert leaderboard.load_bench()["updated_at"] == "2999-01-01"


def test_verified_chart_ranks_lanes_separately_and_covers_3x3x3x3(tmp_path) -> None:
    import json

    from rubix_eval.leaderboard import verified_depth_chart

    def write(name, **fields):
        record = {"record_id": name, "ai": "Model", "lane": "open", "kind": "4d", "size": 3, "ndim": 4,
                  "attempt": {"solved": True, "htm": 50}}
        record.update(fields)
        (tmp_path / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")

    write("a", ai="Fable", depth_label="full", scramble_depth=40, attempt={"solved": True, "htm": 64})
    write("b", ai="Fable", lane="verified", depth_label="5", scramble_depth=5, attempt={"solved": True, "htm": 9})
    write("c", ai="Opus", depth_label="5", scramble_depth=5, attempt={"solved": True, "htm": 41})
    write("d", ai="Opus", depth_label="5", scramble_depth=5, attempt={"solved": True, "htm": 30})
    write("e", ai="OnlineTest4d", depth_label="1", scramble_depth=1)
    write("f", ai="Tiny", size=2, depth_label="2", scramble_depth=2)

    chart = verified_depth_chart("4d3", tmp_path)
    assert (chart["title"], chart["full_turns"], chart["slug"]) == ("3×3×3×3", 40, "3x3x3x3")
    rows = [(m["ai"], m["lane"], m["solved_turns"], m["htm"]) for m in chart["models"]]
    # Verified rows come first; each lane keeps its own best per model.
    assert rows == [("Fable", "verified", 5, 9), ("Fable", "open", 40, 64), ("Opus", "open", 5, 30)]
    assert chart["models"][1]["reached_full"] is True
    assert {c["chart"] for c in chart["charts"]} == {"3d", "4d", "4d3"}
