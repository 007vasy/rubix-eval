"""Command-line interface for rubix-eval."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    view_p.add_argument("--host", default="127.0.0.1")
    view_p.add_argument("--port", type=int, default=8765)

    apply_p = sub.add_parser("apply", help="Apply moves to a task and print the new net")
    apply_p.add_argument("task", help="Task JSON path")
    apply_p.add_argument("moves", nargs="+", help="Moves to apply")

    args = parser.parse_args(argv)
    handlers = {
        "task": _cmd_task,
        "show": _cmd_show,
        "grade": _cmd_grade,
        "oracle": _cmd_oracle,
        "run": _cmd_run,
        "view": _cmd_view,
        "apply": _cmd_apply,
    }
    return handlers[args.cmd](args)


def _add_puzzle_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--size", type=int, default=3, help="Cube size N for an NxNxN cube")
    parser.add_argument("--depth", type=int, default=8, help="Random turns away from solved")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-moves", type=int, default=None)
    parser.add_argument("--4d", dest="four_d", action="store_true", help="3×3×3×3 hypercube instead of 3D")


def _cmd_task(args: argparse.Namespace) -> int:
    task = (
        make_hyper_task(args.depth, args.seed, args.max_moves)
        if args.four_d
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
        task = (
            make_hyper_task(args.depth, args.seed, args.max_moves)
            if args.four_d
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
    serve(root, args.host, args.port)
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


if __name__ == "__main__":
    raise SystemExit(main())
