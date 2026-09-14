"""Scrambles that are a fixed number of steps from solved.

Uses a portable LCG so the same (size, depth, seed) matches the web viewer.
"""

from __future__ import annotations

from .hyper_moves import HyperMove, format_hyper_moves
from .hypercube import adjacent_cells, cells_for, two_plane_partners
from .moves import Move, format_moves

_FACES = ("U", "D", "L", "R", "F", "B")
_OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L", "F": "B", "B": "F"}
_TURNS = (1, 2, 3)

# Numerical Recipes LCG, 32-bit. Shared with web/js/engine.js.
_LCG_A = 1664525
_LCG_C = 1013904223
_LCG_M = 2**32


class LCG:
    def __init__(self, seed: int = 0) -> None:
        self.state = seed % _LCG_M

    def next_int(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        self.state = (_LCG_A * self.state + _LCG_C) % _LCG_M
        return self.state % n

    def choice(self, seq):
        return seq[self.next_int(len(seq))]

    def randint(self, lo: int, hi: int) -> int:
        return lo + self.next_int(hi - lo + 1)


def generate_scramble(
    size: int,
    depth: int,
    seed: int | None = None,
    *,
    inner_slices: bool | None = None,
) -> list[Move]:
    """Return `depth` random moves starting from solved.

    Consecutive moves never share a face. For 3x3-style outer-only scrambles
    on odd cubes, axis cancellation (U then D then U) is also avoided.
    Inner slices default on for size >= 4.
    """
    if depth < 0:
        raise ValueError("depth must be >= 0")
    if inner_slices is None:
        inner_slices = size >= 4
    rng = LCG(0 if seed is None else seed)
    max_layer = size if inner_slices else 1
    # Do not turn the far outer layer from this face (that is the opposite face).
    max_layer = min(max_layer, size - 1) if size > 2 else 1

    moves: list[Move] = []
    last_face: str | None = None
    last_axis_face: str | None = None
    for _ in range(depth):
        faces = list(_FACES)
        if last_face is not None:
            faces = [face for face in faces if face != last_face]
            if last_axis_face is not None and last_axis_face in faces and len(faces) > 1:
                # Avoid U D U axis spam on outer-only odd cubes.
                if not inner_slices or size <= 3:
                    faces = [face for face in faces if face != last_axis_face] or faces
        face = rng.choice(faces)
        layer = 1 if max_layer <= 1 else rng.randint(1, max_layer)
        turns = rng.choice(_TURNS)
        moves.append(Move(face=face, layer=layer, wide=False, turns=turns))
        if last_face is not None and _OPPOSITE.get(face) == last_face:
            last_axis_face = face
        else:
            last_axis_face = None
        last_face = face
    return moves


def scramble_text(size: int, depth: int, seed: int | None = None, **kwargs) -> str:
    return format_moves(generate_scramble(size, depth, seed, **kwargs))


def generate_hyper_scramble(
    depth: int,
    seed: int | None = None,
    *,
    size: int = 3,
    ndim: int = 4,
) -> list[HyperMove]:
    """`depth` random cell/2-plane twists. Consecutive twists avoid the same cell."""
    if depth < 0:
        raise ValueError("depth must be >= 0")
    rng = LCG(0 if seed is None else seed)
    cells = list(cells_for(ndim))
    max_layer = size - 1 if size > 2 else 1
    moves: list[HyperMove] = []
    last_cell: str | None = None
    for _ in range(depth):
        pool = [c for c in cells if c != last_cell] if last_cell else cells
        cell = rng.choice(pool)
        turns = rng.choice(_TURNS)
        layer = 1 if max_layer <= 1 else rng.randint(1, max_layer)
        if ndim == 4:
            neighbors = list(adjacent_cells(cell, ndim=ndim, size=size))
            axis = rng.choice(neighbors)
            moves.append(HyperMove(cell, axis, turns, 4, (axis,), layer if layer > 1 else None))
        else:
            a, b = rng.choice(two_plane_partners(cell, ndim, size))
            moves.append(HyperMove(cell, a, turns, 4, (a, b), layer if layer > 1 else None))
        last_cell = cell
    return moves


def hyper_scramble_text(depth: int, seed: int | None = None, **kwargs) -> str:
    return format_hyper_moves(generate_hyper_scramble(depth, seed, **kwargs))
