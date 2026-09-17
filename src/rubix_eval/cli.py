"""Command-line interface for rubix-eval."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _default_port() -> int:
    return int(os.environ.get("PORT") or "8765")

from .eval_runner import (
    build_suite,
    command_solver,
    oracle_solver,
    run_suite,
    write_report,
)
from .hyper_moves import format_hyper_moves, parse_hyper_moves
from .moves import format_moves, parse_moves
from .paths import web_dir
from .render import ascii_hyper_net, ascii_net, hyper_legend, legend
from .task import EvalTask, load_solution, make_hyper_task, make_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rubix-eval",
        description="NxNxN and 3×3×3×3 (4D) Rubik's cube eval: scramble depth, step cost, offline agents.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    task_p = sub.add_parser("task", help="Create a scrambled eval task JSON")
    _add_puzzle_args(task_p)
    task_p.add_argument("-o", "--output", help="Write JSON to this path (default stdout)")

    show_p = sub.add_parser("show", help="Print an ASCII net of a task or a fresh scramble")
    show_p.add_argument("task", nargs="?", help="Task JSON path")
    _add_puzzle_args(show_p)
    show_p.add_argument("--no-color", action="store_true")

    grade_p = sub.add_parser("grade", help="Grade a solution against a task")
    grade_p.add_argument("task", help="Task JSON path")
    grade_p.add_argument("-s", "--solution", help="Solution file or move string")
    grade_p.add_argument("--stdin", action="store_true", help="Read solution from stdin")

    sub.add_parser("oracle", help="Print the inverse scramble (engine check, not for agents)")
    # redefine with task arg
    oracle_p = sub.choices["oracle"]
    oracle_p.add_argument("task", help="Task JSON path")

    run_p = sub.add_parser("run", help="Run a suite of tasks against a solver command")
    run_p.add_argument("--solver", nargs="+", help="Solver command. Reads task JSON on stdin, writes moves on stdout.")
    run_p.add_argument("--sizes", default="", help="Comma-separated cube sizes, e.g. 2,3,4")
    run_p.add_argument("--depths", default="", help="Comma-separated scramble depths, e.g. 1,5,10")
    run_p.add_argument("--trials", type=int, default=1)
    run_p.add_argument("--seed", type=int, default=0)
    run_p.add_argument("--timeout", type=float, default=None)
    run_p.add_argument("--oracle", action="store_true", help="Use the inverse-scramble oracle instead of --solver")
    run_p.add_argument("--4d", dest="four_d", action="store_true", help="Run 3×3×3×3 (4D) tasks instead of 3D")
    run_p.add_argument("-o", "--output", help="Write JSON report")

    view_p = sub.add_parser("view", help="Serve the interactive 3D cube in a browser")
    view_p.add_argument("--host", default="0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    view_p.add_argument("--port", type=int, default=_default_port())

    vis_p = sub.add_parser(
        "visual",
        help="Visual-only eval: agent sees the cube and turns it with the pointer (computer use)",
    )
    vis_p.add_argument("--size", type=int, default=None, help="Pin cube size N (3D N^3 or 4D N^4)")
    vis_p.add_argument("--ndim", type=int, default=None, help="4–7 for hypercubes")
    vis_p.add_argument("--depth", default=None, help="Pin 1–10 or 'full'; omit to randomize")
    vis_p.add_argument("--seed", type=int, default=None)
    vis_p.add_argument("--max-moves", type=int, default=None)
    vis_p.add_argument("--4d", dest="four_d", action="store_true")
    vis_p.add_argument("--host", default="0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    vis_p.add_argument("--port", type=int, default=_default_port())
    vis_p.add_argument("--no-open", action="store_true", help="Do not open a browser")
    vis_p.add_argument(
        "--ai",
        default=None,
        help="Name of the AI / model taking the visual eval (stored on each solve)",
    )
    vis_p.add_argument(
        "--challenge",
        action="store_true",
        default=True,
        help="Draw a random catalog challenge on every page load (default)",
    )

    solves_p = sub.add_parser(
        "solves",
        help="List recorded visual solves and how they compare to known algorithms",
    )
    solves_p.add_argument("record", nargs="?", help="Record id (prints full JSON)")
    solves_p.add_argument("--dir", help="Solves directory (default: ./solves)")
    solves_p.add_argument("--limit", type=int, default=50)

    board_p = sub.add_parser(
        "leaderboard",
        help="Per-version full-solve and end-step leaderboard (algorithm time + human WR)",
    )
    board_p.add_argument("--bench", action="store_true", help="Time the local solvers and cache the result")
    board_p.add_argument("--all-sizes", action="store_true", help="Include 40³ and 100³")
    board_p.add_argument("--ai", action="store_true", dest="ai_only", help="AI-only ranking by hardest solved challenge")
    board_p.add_argument("--json", action="store_true", dest="as_json")

    ch_p = sub.add_parser(
        "challenge",
        help="Request a randomized challenge (fresh seed every call)",
    )
    ch_p.add_argument("--size", type=int, default=None, help="Pin cube size N, otherwise random")
    ch_p.add_argument(
        "--depth",
        default=None,
        help="Pin 1–10 or 'full', otherwise random",
    )
    ch_p.add_argument("--4d", dest="four_d", action="store_true")
    ch_p.add_argument("--list", action="store_true", help="Print the challenge catalog and exit")
    ch_p.add_argument("--visual-pool", action="store_true", help="Only sizes 2–10 (browser-safe)")
    ch_p.add_argument("-o", "--output", help="Write JSON to this path")

    apply_p = sub.add_parser("apply", help="Apply moves to a task and print the new net")
    apply_p.add_argument("task", help="Task JSON path")
    apply_p.add_argument("moves", nargs="+", help="Moves to apply")

    pub_p = sub.add_parser(
        "publish-verified",
        help="Mark a recorded solve as verified (offline, internet disallowed) and rewrite it",
    )
    pub_p.add_argument("record", help="Record id")
    pub_p.add_argument("--dir", help="Solves directory (default: ./solves or RUBIX_SOLVES_BUCKET)")

    args = parser.parse_args(argv)
    handlers = {
        "task": _cmd_task,
        "show": _cmd_show,
        "grade": _cmd_grade,
        "oracle": _cmd_oracle,
        "run": _cmd_run,
        "view": _cmd_view,
        "visual": _cmd_visual,
        "challenge": _cmd_challenge,
        "apply": _cmd_apply,
        "solves": _cmd_solves,
        "leaderboard": _cmd_leaderboard,
        "publish-verified": _cmd_publish_verified,
    }
    return handlers[args.cmd](args)


def _add_puzzle_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--size", type=int, default=3, help="Cube size N for an NxNxN cube")
    parser.add_argument("--depth", type=int, default=8, help="Random turns away from solved")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-moves", type=int, default=None)
    parser.add_argument("--4d", dest="four_d", action="store_true", help="nD hypercube (default 3^4; use --size / --ndim)")
    parser.add_argument("--ndim", type=int, default=None, help="Dimension 4–7 for hypercubes")


def _cmd_task(args: argparse.Namespace) -> int:
    ndim = args.ndim or (4 if args.four_d else 3)
    task = (
        make_hyper_task(args.depth, args.seed, args.max_moves, size=args.size, ndim=ndim)
        if ndim >= 4
        else make_task(args.size, args.depth, args.seed, args.max_moves)
    )
    text = task.dumps() + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    if args.task:
        task = EvalTask.load(args.task)
        cube = task.cube()
        print(f"{task.id}  kind={task.kind}  depth={task.scramble_depth}  seed={task.seed}")
    else:
        ndim = args.ndim or (4 if args.four_d else 3)
        task = (
            make_hyper_task(args.depth, args.seed, args.max_moves, size=args.size, ndim=ndim)
            if ndim >= 4
            else make_task(args.size, args.depth, args.seed, args.max_moves)
        )
        cube = task.cube()
        print(f"{task.id}")
    color = sys.stdout.isatty() and not args.no_color
    if task.kind == "4d":
        print(hyper_legend())
        print(ascii_hyper_net(cube, color=color))
    else:
        print(legend())
        print(ascii_net(cube, color=color))
    print(f"solved={cube.is_solved()}  misplaced={cube.misplaced_stickers()}")
    return 0


def _cmd_grade(args: argparse.Namespace) -> int:
    task = EvalTask.load(args.task)
    if args.stdin:
        solution = sys.stdin.read()
    elif args.solution:
        path = Path(args.solution)
        solution = load_solution(path) if path.exists() else args.solution
    else:
        print("pass --solution or --stdin", file=sys.stderr)
        return 2
    result = task.grade(solution)
    json.dump(result.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.solved else 1


def _cmd_oracle(args: argparse.Namespace) -> int:
    task = EvalTask.load(args.task)
    print(task.oracle_solution())
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    if not args.oracle and not args.solver:
        print("pass --solver CMD or --oracle", file=sys.stderr)
        return 2
    sizes = [int(x) for x in args.sizes.split(",") if x.strip()] or None
    depths = [int(x) for x in args.depths.split(",") if x.strip()] or None
    tasks = build_suite(
        sizes=sizes,
        depths=depths,
        trials=args.trials,
        seed=args.seed,
        kind="4d" if args.four_d else "3d",
    )
    solver = oracle_solver if args.oracle else command_solver(args.solver)
    report = run_suite(tasks, solver, timeout=args.timeout)
    summary = report.summary()
    if args.output:
        write_report(report, args.output)
    public = {k: v for k, v in summary.items() if k != "results"}
    json.dump({"summary": public, "results": summary["results"]}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report.solved == report.total else 1


def _cmd_view(args: argparse.Namespace) -> int:
    from .serve import serve

    root = web_dir()
    if not (root / "index.html").exists():
        print(f"web UI not found at {root}", file=sys.stderr)
        return 1
    print(f"cube viewer: http://{args.host}:{args.port}/")
    print(f"visual eval: http://{args.host}:{args.port}/eval")
    print(f"solve log:    http://{args.host}:{args.port}/solves")
    print(f"leaderboard:  http://{args.host}:{args.port}/leaderboard")
    print(f"AI ranks:     http://{args.host}:{args.port}/ai")
    serve(root, args.host, args.port)
    return 0


def _cmd_visual(args: argparse.Namespace) -> int:
    import webbrowser
    from urllib.parse import urlencode

    from .serve import serve
    from .visual_session import random_visual_session

    root = web_dir()
    if not (root / "eval.html").exists():
        print(f"visual eval page not found at {root}", file=sys.stderr)
        return 1
    query: dict[str, str] = {"random": "1"}
    if args.ndim:
        query["kind"] = f"{args.ndim}d"
        query["size"] = str(args.size or 3)
    elif args.four_d:
        query["kind"] = "4d"
    if args.size:
        query["size"] = str(args.size)
    if args.depth is not None:
        query["depth"] = str(args.depth)
    if args.ai:
        query["ai"] = args.ai
    session = random_visual_session(
        size=int(query["size"]) if "size" in query else None,
        depth=query.get("depth"),
        kind=query.get("kind", "3d"),
    )
    if args.ai:
        session["ai"] = args.ai
    url = f"http://{args.host}:{args.port}/eval?{urlencode(query)}"
    print("Visual-only eval (computer use). Each load draws a fresh random scramble.")
    print(f"  cube:   {url}")
    print(f"  grade:  http://{args.host}:{args.port}/api/visual/grade")
    print(f"  solves:      http://{args.host}:{args.port}/solves")
    print(f"  leaderboard: http://{args.host}:{args.port}/leaderboard")
    print(f"  AI ranks:    http://{args.host}:{args.port}/ai")
    print(f"  verified:    http://{args.host}:{args.port}/verified")
    print("  github:   https://github.com/007vasy/rubix-eval")
    print("  issues:   https://github.com/007vasy/rubix-eval/issues")
    print("Each Done click is recorded and compared to inverse-scramble, HTM search, and Kociemba.")
    if args.ai:
        print(f"  AI:     {args.ai}")
    print("Left click = 90° CW · right click = 90° CCW · double-click = 180°")
    print("Drag empty space to orbit · green circle = submit")
    if not args.no_open:
        webbrowser.open(url)
    serve(root, args.host, args.port, visual_session=session)
    return 0


def _cmd_challenge(args: argparse.Namespace) -> int:
    from .challenges import catalog, request_challenge

    kind = "4d" if args.four_d else "3d"
    if args.list:
        rows = catalog(kind=kind, visual=args.visual_pool)
        json.dump({"count": len(rows), "challenges": rows}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    try:
        challenge = request_challenge(
            size=args.size,
            depth=args.depth,
            kind=kind,
            visual=args.visual_pool,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    text = json.dumps(challenge.public_dict(), indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_solves(args: argparse.Namespace) -> int:
    from .records import list_records, load_record, solves_dir

    directory = Path(args.dir) if args.dir else solves_dir()
    if args.record:
        record = load_record(args.record, directory)
        if not record:
            print(f"no record matching {args.record!r} in {directory}", file=sys.stderr)
            return 1
        json.dump(record, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    rows = list_records(directory, limit=args.limit)
    if not rows:
        print(f"no recorded solves in {directory}")
        return 0
    print(
        f"{'when':<22} {'solver':<16} {'puzzle':<10} {'htm':>4} {'best':>4} {'ratio':>6} {'alg':<18} result"
    )
    for row in rows:
        when = (row.get("recorded_at") or "")[:19]
        puzzle = "4d" if row.get("kind") == "4d" else f"{row.get('size')}³"
        depth = row.get("scramble_depth")
        puzzle = f"{puzzle} d{depth}"
        htm = row.get("ai_htm")
        best = row.get("best_htm")
        ratio = row.get("optimality_ratio")
        solver = (row.get("ai") or "unspecified AI")[:16]
        flag = "SOLVED" if row.get("solved") else "fail"
        if row.get("optimal"):
            flag = "OPTIMAL"
        print(
            f"{when:<22} {solver:<16} {puzzle:<10} "
            f"{htm if htm is not None else '—':>4} {best if best is not None else '—':>4} "
            f"{ratio if ratio is not None else '—':>6} {str(row.get('best_algorithm') or '—'):<18} {flag}"
        )
    return 0


def _fmt_seconds(value: float | None) -> str:
    if value is None:
        return "—"
    if value <= 0:
        return "< 1 µs"
    if value < 0.001:
        return f"{max(1, round(value * 1_000_000))} µs"
    if value < 0.1:
        return f"{value * 1000:.2f} ms"
    if value < 60:
        return f"{value:.2f} s"
    minutes = int(value // 60)
    rest = value - minutes * 60
    return f"{minutes}:{rest:05.2f}"


def _cmd_leaderboard(args: argparse.Namespace) -> int:
    from .leaderboard import build_ai_leaderboard, build_leaderboard

    if args.ai_only:
        data = build_ai_leaderboard()
        if args.as_json:
            json.dump(data, sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
        if not data["ais"]:
            print("no AI solves recorded yet")
            return 0
        print(f"{'#':>3} {'AI':<20} {'hardest':<28} {'htm':>5} {'solves':>6}")
        for row in data["ais"]:
            h = row["hardest"]
            print(
                f"{row['rank']:>3} {row['ai'][:20]:<20} {h['puzzle']:<28} "
                f"{h['htm'] if h['htm'] is not None else '—':>5} {row['solves']:>6}"
            )
        return 0

    data = build_leaderboard(bench=args.bench, visual_only=not args.all_sizes)
    if args.as_json:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    for board in data["boards"]:
        print(f"\n== {board['label']} ==")
        for group in board.get("groups") or []:
            print(f"  {group['title']}")
            if not group["entries"]:
                print("    (no times yet — run with --bench)")
                continue
            for row in group["entries"]:
                mark = " ★ Human WR" if row.get("highlight") else ""
                print(
                    f"    {row['rank']:>2}. {_fmt_seconds(row['seconds']):>10}  {row['who']}{mark}"
                )
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    task = EvalTask.load(args.task)
    cube = task.cube()
    text = " ".join(args.moves)
    if task.kind == "4d":
        moves = parse_hyper_moves(text)
        cube.apply(moves)
        print(format_hyper_moves(moves))
        print(ascii_hyper_net(cube, color=sys.stdout.isatty()))
    else:
        moves = parse_moves(text)
        cube.apply(moves)
        print(format_moves(moves))
        print(ascii_net(cube, color=sys.stdout.isatty()))
    print(f"solved={cube.is_solved()}  misplaced={cube.misplaced_stickers()}")
    return 0


def _cmd_publish_verified(args: argparse.Namespace) -> int:
    from .records import publish_verified, solves_dir

    directory = Path(args.dir) if args.dir else None
    try:
        rec = publish_verified(args.record, directory)
    except FileNotFoundError:
        root = directory or solves_dir()
        print(f"no record matching {args.record!r} in {root}", file=sys.stderr)
        return 1
    print(json.dumps({"record_id": rec.get("record_id"), "lane": rec.get("lane"), "attested": rec.get("attested")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
