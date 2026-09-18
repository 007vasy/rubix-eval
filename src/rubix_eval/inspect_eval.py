"""Inspect (UK AISI) tasks for the Rubik's cube eval.

Text task: the model sees an ASCII net + JSON state and returns WCA/Zhao moves.
Visual task: the model only gets `look` / `twist` tools (no scramble, no oracle).

Run:
    inspect eval evals/inspect_rubix.py@rubix -T sizes=3 -T depths=1,5
    inspect eval evals/inspect_rubix.py@rubix_visual --solver rubix_eval.inspect_eval.copy_target
"""

from __future__ import annotations

from typing import Any

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    stderr,
    scorer,
)
from inspect_ai.solver import Generate, TaskState, generate, solver
from inspect_ai.tool import tool
from inspect_ai.util import store

from .eval_runner import DEFAULT_SUITE, DEFAULT_SUITE_4D, build_suite
from .metrics import grade_solution
from .render import ascii_hyper_net, ascii_net
from .task import EvalTask

_VISUAL_INSTRUCTIONS = (
    "Solve the cube using tools. Call look() to see stickers, "
    "twist(moves) to turn layers, then submit() with the move string you applied. "
    "You are not given the scramble sequence."
)


def _parse_int_list(value: str | list[int] | tuple[int, ...]) -> list[int]:
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return [int(part.strip()) for part in str(value).split(",") if part.strip()]


def samples_from_suite(
    *,
    sizes: str = "2,3",
    depths: str = "1,5",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
    include_json_state: bool = True,
) -> list[Sample]:
    """Build Inspect samples. Oracle is the target, never the prompt."""
    size_list = _parse_int_list(sizes)
    depth_list = _parse_int_list(depths)
    pairs = [(size, depth) for size in size_list for depth in depth_list]
    tasks = build_suite(pairs=pairs, trials=trials, seed=seed, kind=kind)
    samples: list[Sample] = []
    for task in tasks:
        prompt = task.prompt() if include_json_state else _visual_prompt(task)
        samples.append(
            Sample(
                id=task.id,
                input=prompt,
                target=task.oracle_solution(),
                metadata=_sample_metadata(task),
            )
        )
    return samples


def _visual_prompt(task: EvalTask) -> str:
    shape = (
        "×".join([str(task.size)] * (task.ndim or 3))
        if task.kind != "3d"
        else f"{task.size}×{task.size}×{task.size}"
    )
    return "\n".join(
        [
            f"Solve this {shape} Rubik's cube ({task.kind}).",
            f"It is {task.scramble_depth} random turns from solved.",
            _VISUAL_INSTRUCTIONS,
            f"Aim for under {task.max_moves} HTM moves; a solved cube still counts if you go over.",
        ]
    )


def _sample_metadata(task: EvalTask) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "size": task.size,
        "kind": task.kind,
        "ndim": task.ndim,
        "scramble_depth": task.scramble_depth,
        "seed": task.seed,
        "max_moves": task.max_moves,
        "state": task.state,
    }


def grade_completion(completion: str, metadata: dict[str, Any]) -> Score:
    """Apply the model's move string to the withheld scrambled state."""
    from .cube import Cube
    from .hypercube import HyperCube

    kind = metadata.get("kind") or "3d"
    state = metadata["state"]
    cube = Cube.from_dict(state) if kind == "3d" else HyperCube.from_dict(state)
    grade = grade_solution(
        cube,
        completion,
        int(metadata["scramble_depth"]),
        metadata.get("max_moves"),
    )
    return Score(
        value=CORRECT if grade.solved else INCORRECT,
        answer=" ".join(grade.applied) if grade.applied else completion.strip(),
        explanation=grade.error or ("solved" if grade.solved else f"{grade.misplaced_stickers} stickers left"),
        metadata={
            "solved": grade.solved,
            "htm": grade.cost.htm,
            "qtm": grade.cost.qtm,
            "excess_htm": grade.cost.excess_htm,
            "efficiency": grade.cost.efficiency,
            "misplaced_stickers": grade.misplaced_stickers,
        },
    )


@scorer(metrics=[accuracy(), stderr()])
def cube_grade():
    async def score(state: TaskState, target: Target) -> Score:
        history = ""
        try:
            history = str(store().get("history") or "")
        except Exception:
            history = ""
        completion = (history or state.output.completion or "").strip()
        if not completion:
            return Score(value=INCORRECT, explanation="no moves", answer="")
        return grade_completion(completion, state.metadata or {})

    return score


@solver
def load_cube():
    """Put the scrambled state in the Inspect store for visual tools."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        meta = state.metadata or {}
        store().set("state", meta["state"])
        store().set("kind", meta.get("kind") or "3d")
        store().set("history", "")
        return state

    return solve


@solver
def copy_target():
    """Dry-run solver: play the withheld oracle (for engine checks, not agents)."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        text = state.target.text if state.target else ""
        store().set("history", text)
        state.output = ModelOutput.from_content("oracle", text)
        return state

    return solve


def _live_cube():
    from .cube import Cube
    from .hypercube import HyperCube

    kind = store().get("kind") or "3d"
    state = store().get("state")
    if kind == "3d":
        return Cube.from_dict(state)
    return HyperCube.from_dict(state)


def _render(cube) -> str:
    if getattr(cube, "ndim", 3) > 3 or getattr(cube, "kind", "3d") != "3d":
        try:
            return ascii_hyper_net(cube)
        except Exception:
            return ascii_net(cube)
    return ascii_net(cube)


@tool
def look():
    async def execute() -> str:
        """See the current cube stickers as an ASCII net. No scramble is included."""
        return _render(_live_cube())

    return execute


@tool
def twist():
    async def execute(moves: str) -> str:
        """Apply WCA (3D) or Zhao (nD) moves, then show the cube.

        Args:
            moves: Move string such as "R U R'" or "RU IF'".
        """
        cube = _live_cube()
        kind = store().get("kind") or "3d"
        if kind == "3d":
            cube.apply(moves)
        else:
            cube.apply(moves)
        store().set("state", cube.to_dict())
        prev = str(store().get("history") or "").strip()
        store().set("history", (prev + " " + moves.strip()).strip())
        return _render(cube)

    return execute


@task
def rubix(
    sizes: str = "2,3",
    depths: str = "1,5",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
) -> Task:
    """Text cube eval: ASCII + JSON state in, move string out."""
    return Task(
        dataset=MemoryDataset(
            samples_from_suite(
                sizes=sizes,
                depths=depths,
                trials=trials,
                seed=seed,
                kind=kind,
                include_json_state=True,
            )
        ),
        solver=generate(),
        scorer=cube_grade(),
        name="rubix",
        display_name="Rubik's cube (text)",
    )


@task
def rubix_visual(
    sizes: str = "3",
    depths: str = "1,2,5",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
    attempts: int = 1,
) -> Task:
    """Tool-use cube eval: look/twist only. No scramble, no oracle, no JSON net in the prompt."""
    return Task(
        dataset=MemoryDataset(
            samples_from_suite(
                sizes=sizes,
                depths=depths,
                trials=trials,
                seed=seed,
                kind=kind,
                include_json_state=False,
            )
        ),
        solver=[
            load_cube(),
            react(
                prompt=_VISUAL_INSTRUCTIONS,
                tools=[look(), twist()],
                attempts=attempts,
            ),
        ],
        scorer=cube_grade(),
        name="rubix_visual",
        display_name="Rubik's cube (tools)",
        message_limit=80,
    )


@task
def rubix_oracle(
    sizes: str = "3",
    depths: str = "1",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
) -> Task:
    """Engine check: play the withheld inverse scramble through Inspect."""
    return Task(
        dataset=MemoryDataset(
            samples_from_suite(
                sizes=sizes,
                depths=depths,
                trials=trials,
                seed=seed,
                kind=kind,
                include_json_state=True,
            )
        ),
        solver=copy_target(),
        scorer=cube_grade(),
        name="rubix_oracle",
        display_name="Rubik's cube (oracle dry-run)",
    )


@task
def rubix_full(kind: str = "3d", trials: int = 1, seed: int = 0) -> Task:
    """Default 3D or 4D suite from eval_runner."""
    pairs = DEFAULT_SUITE_4D if kind == "4d" else DEFAULT_SUITE
    sizes = ",".join(str(p[0]) for p in pairs)
    # build_suite with pairs is more accurate than unique sizes×depths
    tasks = build_suite(pairs=pairs, trials=trials, seed=seed, kind=kind)
    samples = [
        Sample(
            id=t.id,
            input=t.prompt(),
            target=t.oracle_solution(),
            metadata=_sample_metadata(t),
        )
        for t in tasks
    ]
    return Task(
        dataset=MemoryDataset(samples),
        solver=generate(),
        scorer=cube_grade(),
        name="rubix_full",
        display_name="Rubik's cube (full suite)",
    )
