"""Per-version leaderboards: full scramble (algorithm time + human record)
and end-step depths 1–10 (algorithm time only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .challenges import DEPTH_LABELS, SIZES, VISUAL_SIZES, full_scramble_depth
from .human_records import human_record, version_key
from .puzzles import ND_PUZZLES, difficulty_score, difficulty_tuple, nd_label, puzzle_label
from .records import list_records, solves_dir
from .solvers import compare_algorithms
from .visual_session import session_from_task
from .task import make_hyper_task, make_task

END_STEP_LABELS = tuple(label for label in DEPTH_LABELS if label != "full")
VERSIONS: tuple[tuple[str, int], ...] = tuple(("3d", n) for n in SIZES) + (("4d", 3),)


def named_ai(value: Any) -> str | None:
    """Leaderboard rows need an explicit AI name; untagged solves are omitted."""
    name = str(value or "").strip()
    if not name or name.lower() in {"unspecified ai", "unspecified"}:
        return None
    return name


def bench_path() -> Path:
    return solves_dir() / "algorithm_bench.json"


# Solver timings precomputed with `rubix-eval leaderboard --bench --bench-out ...` and shipped
# with the package, so the public board never has to time the solvers on a page load.
BUNDLED_BENCH = Path(__file__).resolve().parent / "data" / "algorithm_bench.json"


def effective_depth(
    kind: str | None, size: int, scramble_depth: int | None, depth_label: str | None, ndim: int | None = None
) -> tuple[str | None, bool]:
    """(depth label to rank by, legacy). A run labelled "full" only counts as full if its
    scramble was at least today's full length; the old 40-twist 3x3x3x3 "full" (drawn by
    the broken v1 generator) is ranked as the 40 random turns it was."""
    if depth_label != "full" or not scramble_depth:
        return depth_label, False
    full = full_scramble_depth(int(size or 3), kind or "3d", ndim)
    if int(scramble_depth) < full:
        return str(int(scramble_depth)), True
    return depth_label, False


def _label_for(kind: str, size: int, scramble_depth: int, depth_label: str | None) -> str:
    depth_label, _legacy = effective_depth(kind, size, scramble_depth, depth_label)
    if depth_label:
        return str(depth_label)
    if scramble_depth == full_scramble_depth(size, kind):
        return "full"
    return str(scramble_depth)


def _alg_entry(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row.get("solved"):
        return None
    elapsed = row.get("elapsed_sec")
    if elapsed is None:
        return None
    return {
        "algorithm": row.get("algorithm"),
        "label": row.get("label") or row.get("algorithm"),
        "seconds": float(elapsed),
        "htm": row.get("htm"),
        "optimal": bool(row.get("optimal")),
    }


def _read_bench(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_bench() -> dict[str, Any]:
    """The newest of the local bench (solves/) and the bundled precomputed one."""
    found = [b for b in (_read_bench(bench_path()), _read_bench(BUNDLED_BENCH)) if b]
    if not found:
        return {"versions": {}}
    return max(found, key=lambda b: str(b.get("updated_at") or ""))


def save_bench(data: dict[str, Any], path: Path | None = None) -> Path:
    path = path or bench_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def benchmark_slot(
    kind: str,
    size: int,
    depth_label: str,
    *,
    seed: int = 1,
    time_limit: float = 1.5,
) -> dict[str, Any]:
    depth = full_scramble_depth(size, kind) if depth_label == "full" else int(depth_label)
    ndim = int(kind[0]) if kind and kind[0].isdigit() and kind.endswith("d") else 3
    task = (
        make_hyper_task(depth, seed, size=size, ndim=ndim)
        if ndim >= 4
        else make_task(size, depth, seed)
    )
    session = session_from_task(task, challenge_id=f"{'4d' if kind == '4d' else f'n{size}'}-d{depth_label}", depth_label=depth_label)
    algs = compare_algorithms(session, time_limit=time_limit)
    return {
        "kind": kind,
        "size": size,
        "depth_label": depth_label,
        "scramble_depth": depth,
        "algorithms": [entry for row in algs if (entry := _alg_entry(row))],
    }


def _search_budget(kind: str, size: int, depth_label: str, time_limit: float) -> float:
    """Keep big-cube HTM search from blocking the leaderboard."""
    if kind != "3d":
        ndim = int(kind[0]) if kind[0].isdigit() else 4
        if ndim > 4 or size > 3:
            return 0.0
        return time_limit if depth_label in {"1", "2", "3", "5"} else min(0.2, time_limit)
    if size <= 3:
        return time_limit
    if size <= 5 and depth_label != "full" and int(depth_label) <= 4:
        return min(0.4, time_limit)
    if size >= 8:
        return 0.0
    return 0.05


def run_benchmark(
    *,
    visual_only: bool = True,
    time_limit: float = 0.8,
    seed: int = 1,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Time the local solvers on every board (3D sizes and the nD puzzles). Inverse
    scramble is always run; HTM search / Kociemba run where they finish inside the
    per-slot budget."""
    sizes = VISUAL_SIZES if visual_only else SIZES
    out: dict[str, Any] = {"updated_at": _now(), "seed": seed, "versions": {}}
    for kind, size, ndim in versions_for(sizes):
        key = version_key(kind, size, ndim)
        slots: dict[str, Any] = {}
        labels = list(END_STEP_LABELS) + ["full"]
        if size >= 40:
            labels = ["1", "2", "full"]
        for label in labels:
            slots[label] = benchmark_slot(
                kind,
                size,
                label,
                seed=seed,
                time_limit=_search_budget(kind, size, label, time_limit),
            )
        out["versions"][key] = slots
    save_bench(out, out_path)
    return out


def versions_for(sizes: tuple[int, ...] | list[int] = SIZES) -> list[tuple[str, int, int]]:
    rows = [("3d", n, 3) for n in sizes]
    for puzzle in ND_PUZZLES:
        rows.append((f"{puzzle['ndim']}d", int(puzzle["size"]), int(puzzle["ndim"])))
    return rows


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _recorded_algorithm_times(directory: Path | None = None) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """version -> depth_label -> list of algorithm timing samples from stored solves."""
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    root = directory or solves_dir()
    if not root.exists():
        return grouped
    for path in root.glob("*.json"):
        if path.name in ("algorithm_bench.json", "solves.jsonl"):
            continue
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not rec.get("record_id"):
            continue
        kind = rec.get("kind") or "3d"
        size = int(rec.get("size") or 3)
        key = version_key(kind, size)
        label = _label_for(kind, size, int(rec.get("scramble_depth") or 0), rec.get("depth_label"))
        bucket = grouped.setdefault(key, {}).setdefault(label, [])
        for row in rec.get("algorithms") or []:
            entry = _alg_entry(row)
            if entry:
                bucket.append(entry)
    return grouped


def _best_by_algorithm(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in samples:
        name = row["algorithm"]
        prev = best.get(name)
        if prev is None or row["seconds"] < prev["seconds"]:
            best[name] = row
    return list(best.values())


def _rank_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best first: lowest time, then known algorithms ahead of AI/human on ties."""
    kind_rank = {"algorithm": 0, "ai": 1, "human": 2}

    def key(row: dict[str, Any]) -> tuple:
        sec = row.get("seconds")
        return (
            float(sec) if isinstance(sec, (int, float)) else 1e18,
            kind_rank.get(row.get("kind") or "", 9),
            row.get("htm") if isinstance(row.get("htm"), int) else 10**9,
        )

    out = sorted(entries, key=key)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


def _ai_solves(directory: Path | None = None) -> dict[str, dict[str, list[dict[str, Any]]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    # Summary rows carry everything needed; no second fetch per record.
    for row in list_records(directory, limit=500):
        if not row.get("solved"):
            continue
        kind = row.get("kind") or "3d"
        size = int(row.get("size") or 3)
        label = _label_for(kind, size, int(row.get("scramble_depth") or 0), row.get("depth_label"))
        elapsed = row.get("elapsed_sec")
        if elapsed is None:
            continue
        name = named_ai(row.get("ai"))
        if not name:
            continue
        if (row.get("lane") or "open") == "verified":
            continue
        grouped.setdefault(version_key(kind, size), {}).setdefault(label, []).append(
            {
                "who": name,
                "kind": "ai",
                "seconds": float(elapsed),
                "htm": row.get("ai_htm"),
                "note": row.get("record_id"),
                "record_id": row.get("record_id"),
                "click_count": row.get("click_count"),
                "step_count": row.get("step_count"),
                "tokens_used": row.get("tokens_used"),
                "token_cost_usd": row.get("token_cost_usd"),
                "source": "computer-use",
                "highlight": False,
            }
        )
    for version in grouped.values():
        for label, rows in version.items():
            rows.sort(key=lambda r: r["seconds"])
            version[label] = rows[:8]
    return grouped


def build_leaderboard(
    *,
    directory: Path | None = None,
    bench: bool = False,
    visual_only: bool = True,
) -> dict[str, Any]:
    if bench:
        run_benchmark(visual_only=visual_only)
    cached = load_bench()
    recorded_algs = _recorded_algorithm_times(directory)
    ai_by = _ai_solves(directory)
    sizes = VISUAL_SIZES if visual_only else SIZES
    boards = []
    for kind, size, ndim in versions_for(sizes):
        key = version_key(kind, size, ndim)
        human = human_record(kind, size, ndim)
        cache_slots = (cached.get("versions") or {}).get(key) or {}
        groups = []
        for label in list(END_STEP_LABELS) + ["full"]:
            is_full = label == "full"
            depth = full_scramble_depth(size, kind) if is_full else int(label)
            samples = list(recorded_algs.get(key, {}).get(label) or [])
            for row in (cache_slots.get(label) or {}).get("algorithms") or []:
                samples.append(row)
            entries: list[dict[str, Any]] = []
            for row in _best_by_algorithm(samples):
                entries.append(
                    {
                        "who": row["label"],
                        "kind": "algorithm",
                        "algorithm": row["algorithm"],
                        "seconds": row["seconds"],
                        "htm": row.get("htm"),
                        "note": "known algorithm · CPU time to produce a solution",
                        "source": "rubix-eval",
                        "highlight": False,
                    }
                )
            for row in ai_by.get(key, {}).get(label) or []:
                entries.append(dict(row))
            if is_full and human:
                note = f"{human['event']}" + (f" · {human['date']}" if human.get("date") else "")
                if human.get("shortest_twists"):
                    note += (
                        f" · shortest 3⁴ {human['shortest_twists']} twists"
                        f" ({human.get('shortest_person')}, MC4D Hall of Fame)"
                    )
                entries.append(
                    {
                        "who": human["person"],
                        "kind": "human",
                        "seconds": human["seconds"],
                        "note": note,
                        "source": human["source"],
                        "htm": human.get("shortest_twists"),
                        "highlight": True,
                        "badge": "Human WR",
                    }
                )
            title = (
                f"Full scramble · {depth} random turns"
                if is_full
                else f"{label} turn{'s' if label != '1' else ''} from solved"
            )
            groups.append(
                {
                    "depth_label": label,
                    "scramble_depth": depth,
                    "full": is_full,
                    "title": title,
                    "entries": _rank_entries(entries),
                }
            )
        full_group = next(g for g in groups if g["full"])
        end_steps = [
            {
                "depth_label": g["depth_label"],
                "scramble_depth": g["scramble_depth"],
                "algorithms": [
                    {
                        "algorithm": e.get("algorithm"),
                        "label": e["who"],
                        "seconds": e["seconds"],
                        "htm": e.get("htm"),
                        "optimal": False,
                    }
                    for e in g["entries"]
                    if e["kind"] == "algorithm"
                ],
            }
            for g in groups
            if not g["full"]
        ]
        refs = []
        refs = []
        if ndim >= 4:
            refs = [
                {
                    "name": "MagicCube4D",
                    "url": "https://github.com/cutelyaware/magiccube4d",
                    "note": "Melinda Green, Don Hatch, Jay Berkenbilt, Roice Nelson — nD cube UI. Cheat-solve undoes the scramble.",
                },
                {
                    "name": "MPUlt",
                    "url": "https://github.com/cutelyaware/MPUlt",
                    "note": "Andrey Astrelin — Magic Puzzle Ultimate, higher-dimensional twisty puzzles.",
                },
            ]
        boards.append(
            {
                "version": key,
                "kind": kind,
                "size": size,
                "ndim": ndim,
                "label": nd_label(ndim, size) if ndim >= 4 else f"{size}×{size}×{size}",
                "human": human,
                "references": refs,
                "groups": groups,
                "full": {
                    "scramble_depth": full_group["scramble_depth"],
                    "entries": full_group["entries"],
                },
                "end_steps": end_steps,
            }
        )
    return {
        "updated_at": cached.get("updated_at"),
        "human_records_as_of": "2026-08-31",
        "human_records_source": "WCA records / Hypercubing (MC4D Hall of Fame) / Speedsolving unofficial WR list",
        "boards": boards,
    }


# The visual verified benchmark: 3×3×3, the 2×2×2×2 tesseract and the 3×3×3×3.
VERIFIED_CHARTS: dict[str, dict[str, Any]] = {
    "3d": {"kind": "3d", "size": 3, "ndim": 3, "title": "3×3×3", "slug": "3d"},
    "4d": {"kind": "4d", "size": 2, "ndim": 4, "title": "2×2×2×2", "slug": "4d"},
    "4d3": {"kind": "4d", "size": 3, "ndim": 4, "title": "3×3×3×3", "slug": "3x3x3x3"},
}


def verified_depth_chart(
    kind: str,
    directory: Path | None = None,
) -> dict[str, Any]:
    """Deepest official scramble each model solved, against a full scramble.

    One row per model per lane, so a verified offline run and an open computer-use
    run of the same model are shown (and ranked) separately. A model with only
    failed attempts in a lane is a zero row in that lane.
    """
    spec = VERIFIED_CHARTS.get(kind)
    if spec is None:
        raise ValueError(f"unknown verified chart {kind}")
    cube_kind = spec["kind"]
    size = int(spec["size"])
    full = full_scramble_depth(size, cube_kind, spec["ndim"])
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for row in list_records(directory, limit=10000):
        if row.get("kind") != cube_kind or int(row.get("size") or 0) != size:
            continue
        name = named_ai(row.get("ai"))
        # Harness probes that landed in solves/, not benchmark models.
        if not name or name.lower() in {"cheatbot", "clickprobe"} or name.lower().startswith("onlinetest"):
            continue
        lane = "verified" if (row.get("lane") or "open") == "verified" else "open"
        solved = bool(row.get("solved"))
        # Bars show the scramble the model actually faced, so an old short "full" is not full.
        turns = min(full, int(row.get("scramble_depth") or 0)) if solved else 0
        _label, legacy = effective_depth(cube_kind, size, row.get("scramble_depth"), row.get("depth_label"), spec["ndim"])
        htm = row.get("ai_htm") if solved else None
        current = best.setdefault(
            (name, lane),
            {"ai": name, "lane": lane, "solved_turns": 0, "htm": None, "record_id": None, "legacy_scramble": False},
        )
        if not turns:
            continue
        deeper = turns > int(current["solved_turns"])
        tighter = turns == int(current["solved_turns"]) and (
            current["htm"] is None or (htm is not None and htm < current["htm"])
        )
        if deeper or tighter:
            current.update(solved_turns=turns, htm=htm, record_id=row.get("record_id"), legacy_scramble=legacy)
    models = []
    for row in best.values():
        solved_turns = int(row["solved_turns"])
        models.append(
            {
                "ai": row["ai"],
                "lane": row["lane"],
                "solved_turns": solved_turns,
                "full_turns": full,
                "gap_turns": max(0, full - solved_turns),
                "reached_full": solved_turns >= full and full > 0,
                "htm": row.get("htm"),
                "record_id": row.get("record_id"),
                "legacy_scramble": bool(row.get("legacy_scramble")),
            }
        )
    models.sort(
        key=lambda item: (
            item["lane"] != "verified",
            -item["solved_turns"],
            item["htm"] if item["htm"] is not None else 10**9,
            item["ai"].lower(),
        )
    )
    return {
        "kind": cube_kind,
        "chart": kind,
        "slug": spec["slug"],
        "size": size,
        "ndim": spec["ndim"],
        "title": spec["title"],
        "full_turns": full,
        "lanes": ["verified", "open"],
        "charts": [{"chart": key, "slug": c["slug"], "title": c["title"]} for key, c in VERIFIED_CHARTS.items()],
        "models": models,
    }


def build_ai_leaderboard(directory: Path | None = None, *, lane: str = "open") -> dict[str, Any]:
    """Rank AIs by the hardest challenge each has actually solved."""
    want = "verified" if lane == "verified" else "open"
    rows = list_records(directory, limit=2000)
    by_ai: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not row.get("solved"):
            continue
        row_lane = row.get("lane") or "open"
        if row_lane != want:
            continue
        name = named_ai(row.get("ai"))
        if not name:
            continue
        label, legacy = effective_depth(
            row.get("kind"), int(row.get("size") or 3), row.get("scramble_depth"), row.get("depth_label"), row.get("ndim")
        )
        key = difficulty_tuple(
            kind=row.get("kind"),
            size=row.get("size"),
            scramble_depth=row.get("scramble_depth"),
            depth_label=label,
            ndim=row.get("ndim"),
        )
        puzzle = puzzle_label(row.get("kind"), int(row.get("size") or 3), row.get("ndim"), label, row.get("scramble_depth"))
        entry = {
            **row,
            "difficulty": difficulty_score(key),
            "difficulty_key": list(key),
            "legacy_scramble": legacy,
            "puzzle": f"{puzzle} (old scramble)" if legacy else puzzle,
        }
        by_ai.setdefault(name, []).append(entry)
    ranking = []
    for name, solves in by_ai.items():
        solves.sort(
            key=lambda r: (
                tuple(r["difficulty_key"]),
                -(r["optimality_ratio"] or 0),
                -(1_000_000 - (r["ai_htm"] or 10**9)),
            ),
            reverse=True,
        )
        hardest = solves[0]
        ranking.append(
            {
                "ai": name,
                "solves": len(solves),
                "hardest": {
                    "puzzle": hardest["puzzle"],
                    "kind": hardest.get("kind"),
                    "size": hardest.get("size"),
                    "ndim": hardest.get("ndim"),
                    "depth_label": hardest.get("depth_label"),
                    "scramble_depth": hardest.get("scramble_depth"),
                    "htm": hardest.get("ai_htm"),
                    "elapsed_sec": hardest.get("elapsed_sec"),
                    "click_count": hardest.get("click_count"),
                    "step_count": hardest.get("step_count"),
                    "tokens_used": hardest.get("tokens_used"),
                    "token_cost_usd": hardest.get("token_cost_usd"),
                    "has_replay": hardest.get("has_replay"),
                    "optimality_ratio": hardest.get("optimality_ratio"),
                    "record_id": hardest.get("record_id"),
                    "difficulty": hardest["difficulty"],
                    "legacy_scramble": hardest.get("legacy_scramble", False),
                },
                "solved": [
                    {
                        "puzzle": s["puzzle"],
                        "htm": s.get("ai_htm"),
                        "elapsed_sec": s.get("elapsed_sec"),
                        "click_count": s.get("click_count"),
                        "step_count": s.get("step_count"),
                        "tokens_used": s.get("tokens_used"),
                        "token_cost_usd": s.get("token_cost_usd"),
                        "has_replay": s.get("has_replay"),
                        "record_id": s.get("record_id"),
                        "difficulty": s["difficulty"],
                    }
                    for s in solves
                ],
            }
        )
    ranking.sort(key=lambda r: (r["hardest"]["difficulty"], r["solves"]), reverse=True)
    for i, row in enumerate(ranking, start=1):
        row["rank"] = i
    return {
        "ais": ranking,
        "count": len(ranking),
        "lane": want,
        "github": "https://github.com/007vasy/rubix-eval",
        "issues": "https://github.com/007vasy/rubix-eval/issues",
    }
