"""Inspect entrypoint.

    inspect eval evals/inspect_rubix.py@rubix -T sizes=3 -T depths=1
    inspect eval evals/inspect_rubix.py@rubix_visual
"""

from inspect_ai import Task, task

from rubix_eval.inspect_eval import (
    rubix as _rubix,
    rubix_full as _rubix_full,
    rubix_oracle as _rubix_oracle,
    rubix_visual as _rubix_visual,
)


@task
def rubix(
    sizes: str = "2,3",
    depths: str = "1,5",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
) -> Task:
    return _rubix(sizes=sizes, depths=depths, trials=trials, seed=seed, kind=kind)


@task
def rubix_visual(
    sizes: str = "3",
    depths: str = "1,2,5",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
    attempts: int = 1,
) -> Task:
    return _rubix_visual(
        sizes=sizes,
        depths=depths,
        trials=trials,
        seed=seed,
        kind=kind,
        attempts=attempts,
    )


@task
def rubix_oracle(
    sizes: str = "3",
    depths: str = "1",
    trials: int = 1,
    seed: int = 0,
    kind: str = "3d",
) -> Task:
    return _rubix_oracle(sizes=sizes, depths=depths, trials=trials, seed=seed, kind=kind)


@task
def rubix_full(kind: str = "3d", trials: int = 1, seed: int = 0) -> Task:
    return _rubix_full(kind=kind, trials=trials, seed=seed)
