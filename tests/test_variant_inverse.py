"""Every cube variant: random legal moves, then the inverse, must solve.

Forward path never returns to solved and never repeats a consecutive state.
Inverse path stays unsolved until the last move, which restores solved.
"""

from __future__ import annotations

import random
from typing import Any, Callable

import pytest

from rubix_eval.challenges import SIZES
from rubix_eval.cube import Cube
from rubix_eval.hyper_moves import HyperMove, invert_hyper_moves
from rubix_eval.hypercube import HyperCube, adjacent_cells, cells_for, two_plane_partners
from rubix_eval.moves import Move, invert_moves
from rubix_eval.puzzles import ND_PUZZLES

_FACES = ("U", "D", "F", "B", "L", "R")
_TURNS = (1, 2, 3)
_DEPTH = 8
_SEEDS = (0, 1, 7)


def _variants() -> list[tuple[str, int, int]]:
    rows = [("3d", size, 3) for size in SIZES]
    for puzzle in ND_PUZZLES:
        rows.append((f"{puzzle['ndim']}d", int(puzzle["size"]), int(puzzle["ndim"])))
    return rows


def _id(kind: str, size: int, ndim: int) -> str:
    if ndim <= 3:
        return f"{size}x{size}x{size}"
    return "x".join([str(size)] * ndim)


def _fingerprint(cube: Cube | HyperCube) -> tuple[Any, ...]:
    items = tuple(
        sorted((pos, tuple(sorted(colors.items()))) for pos, colors in cube._cubies.items())
    )
    if isinstance(cube, HyperCube):
        return (cube.ndim, cube.size, items)
    return (cube.size, items)


def _legal_3d(size: int) -> list[Move]:
    moves: list[Move] = []
    max_layer = size - 1 if size > 2 else 1
    for face in _FACES:
        for layer in range(1, max_layer + 1):
            for turns in _TURNS:
                moves.append(Move(face=face, layer=layer, wide=False, turns=turns))
            if layer >= 2:
                for turns in _TURNS:
                    moves.append(Move(face=face, layer=layer, wide=True, turns=turns))
    return moves


def _legal_nd(size: int, ndim: int) -> list[HyperMove]:
    moves: list[HyperMove] = []
    cells = list(cells_for(ndim))
    max_layer = size - 1 if size > 2 else 1
    layers = [None] if max_layer <= 1 else [None, *range(2, max_layer + 1)]
    for cell in cells:
        neighbors = list(adjacent_cells(cell, ndim=ndim, size=size))
        for layer in layers:
            if ndim == 4:
                for axis in neighbors:
                    for turns in _TURNS:
                        moves.append(HyperMove(cell, axis, turns, 4, (axis,), layer))
            else:
                for a, b in two_plane_partners(cell, ndim, size):
                    for turns in _TURNS:
                        moves.append(HyperMove(cell, a, turns, 4, (a, b), layer))
    return moves


def _make_cube(size: int, ndim: int) -> Cube | HyperCube:
    if ndim <= 3:
        return Cube(size)
    return HyperCube(size=size, ndim=ndim)


def _random_path(
    factory: Callable[[], Cube | HyperCube],
    legal: list[Any],
    rng: random.Random,
    depth: int,
) -> list[Any]:
    cube = factory()
    assert cube.is_solved()
    seen = {_fingerprint(cube)}
    moves: list[Any] = []
    tries = 0
    limit = max(2000, depth * 80)
    while len(moves) < depth:
        tries += 1
        if tries > limit:
            raise AssertionError(
                f"could not build a {depth}-move non-repeating path after {tries} draws"
            )
        move = rng.choice(legal)
        trial = cube.copy()
        trial.apply([move])
        fp = _fingerprint(trial)
        if trial.is_solved() or fp in seen:
            continue
        cube = trial
        seen.add(fp)
        moves.append(move)
    return moves


def _play(
    cube: Cube | HyperCube,
    moves: list[Any],
    *,
    expect_solved_at_end: bool,
) -> None:
    prev = _fingerprint(cube)
    for i, move in enumerate(moves):
        cube.apply([move])
        now = _fingerprint(cube)
        assert now != prev, f"move {i} {move} was a no-op"
        last = i == len(moves) - 1
        if expect_solved_at_end and last:
            assert cube.is_solved(), f"inverse did not solve after {move}"
        else:
            assert not cube.is_solved(), f"solved too early at move {i} {move}"
        prev = now
    if expect_solved_at_end:
        assert cube.is_solved()


@pytest.mark.parametrize("kind,size,ndim", _variants(), ids=lambda v: _id(*v) if isinstance(v, tuple) else str(v))
@pytest.mark.parametrize("seed", _SEEDS)
def test_random_moves_invert_to_solved(kind: str, size: int, ndim: int, seed: int) -> None:
    depth = 3 if size >= 40 else _DEPTH
    factory = lambda: _make_cube(size, ndim)
    legal = _legal_3d(size) if ndim <= 3 else _legal_nd(size, ndim)
    assert legal, f"no legal moves for {kind} n={size}"
    rng = random.Random(seed * 1009 + size * 17 + ndim)
    scramble = _random_path(factory, legal, rng, depth)
    assert len(scramble) == depth

    cube = factory()
    _play(cube, scramble, expect_solved_at_end=False)
    assert not cube.is_solved()

    inverse = invert_moves(scramble) if ndim <= 3 else invert_hyper_moves(scramble)
    _play(cube, inverse, expect_solved_at_end=True)


@pytest.mark.parametrize("size,ndim", [(2, 5), (3, 5), (2, 6), (3, 7)])
def test_nd_single_move_inverts(size: int, ndim: int) -> None:
    legal = _legal_nd(size, ndim)
    rng = random.Random(ndim * 10 + size)
    sample = rng.sample(legal, min(40, len(legal)))
    for move in sample:
        cube = HyperCube(size=size, ndim=ndim)
        cube.apply([move])
        assert not cube.is_solved()
        cube.apply([move.inverted()])
        assert cube.is_solved(), f"{move} then inverse left the {size}^{ndim} unsolved"
        cube = HyperCube(size=size, ndim=ndim)
        for _ in range(4):
            cube.apply([move])
        assert cube.is_solved(), f"{move}^4 is not identity"
