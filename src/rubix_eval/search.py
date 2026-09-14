"""HTM search over the eval's own move set (God's algorithm when it finishes).

Uses facelet permutations so NxN and 4D share the same bidirectional BFS.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from .cube import FACES, Cube
from .hyper_moves import HyperMove, format_hyper_moves
from .hypercube import CELLS, HyperCube, adjacent_cells
from .moves import Move, format_moves

FACELET_ORDER = ("U", "R", "F", "D", "L", "B")


def eval_moves_3d(size: int) -> list[Move]:
    """Face/slice turns in the eval metric.

    2×2 and 3×3 use the 18 outer HTM generators (God's number is defined on
    these). Bigger cubes include inner slices, which both the scramble and
    sticker-clicks use.
    """
    max_layer = 1 if size <= 3 else size - 1
    return [
        Move(face, layer, False, turns)
        for face in "URFDLB"
        for layer in range(1, max_layer + 1)
        for turns in (1, 2, 3)
    ]


def eval_moves_4d() -> list[HyperMove]:
    return [
        HyperMove(cell, axis, turns)
        for cell in CELLS
        for axis in adjacent_cells(cell)
        for turns in (1, 2, 3)
    ]


def facelets_3d(cube: Cube) -> bytes:
    parts: list[str] = []
    for face in FACELET_ORDER:
        for row in cube.face_grid(face):
            parts.extend(row)
    return "".join(parts).encode("ascii")


def facelets_4d(cube: HyperCube) -> bytes:
    return "".join(cube.cell_stickers_flat(cell) for cell in CELLS).encode("ascii")


def _flat_labeled_3d(cube: Cube) -> list[str]:
    return [cell for face in FACELET_ORDER for row in cube.face_grid(face) for cell in row]


def _move_perm_3d(size: int, move: Move) -> tuple[int, ...]:
    faces: dict[str, list[list[str]]] = {}
    index = 0
    for face in FACES:
        grid = []
        for _r in range(size):
            row = []
            for _c in range(size):
                row.append(f"{index:04d}")
                index += 1
            grid.append(row)
        faces[face] = grid
    cube = Cube(size)
    cube.set_faces(faces)
    before = _flat_labeled_3d(cube)
    cube.apply([move])
    after = _flat_labeled_3d(cube)
    loc = {label: i for i, label in enumerate(before)}
    return tuple(loc[label] for label in after)


def _move_perm_4d(move: HyperMove) -> tuple[int, ...]:
    n = 3
    cells: dict[str, list[list[list[str]]]] = {}
    index = 0
    for cell in CELLS:
        grid = [[[""] * n for _ in range(n)] for _ in range(n)]
        for k in range(n):
            for j in range(n):
                for i in range(n):
                    grid[k][j][i] = f"{index:04d}"
                    index += 1
        cells[cell] = grid
    cube = HyperCube()
    cube.set_cells(cells)
    before = [s for cell in CELLS for s in cube.cell_stickers_flat(cell)]
    cube.apply([move])
    after = [s for cell in CELLS for s in cube.cell_stickers_flat(cell)]
    loc = {label: i for i, label in enumerate(before)}
    return tuple(loc[label] for label in after)


def _apply(state: bytes, perm: tuple[int, ...]) -> bytes:
    return bytes(state[i] for i in perm)


class _Table3D:
    def __init__(self, size: int) -> None:
        self.size = size
        self.moves = eval_moves_3d(size)
        self.perms = [_move_perm_3d(size, move) for move in self.moves]
        self.faces = [move.face for move in self.moves]
        self.layers = [move.layer for move in self.moves]


class _Table4D:
    def __init__(self) -> None:
        self.moves = eval_moves_4d()
        self.perms = [_move_perm_4d(move) for move in self.moves]
        self.faces = [move.cell for move in self.moves]
        self.layers = [0] * len(self.moves)


_TABLES_3D: dict[int, _Table3D] = {}
_TABLE_4D: _Table4D | None = None


def _table_3d(size: int) -> _Table3D:
    table = _TABLES_3D.get(size)
    if table is None:
        table = _Table3D(size)
        _TABLES_3D[size] = table
    return table


def _table_4d() -> _Table4D:
    global _TABLE_4D
    if _TABLE_4D is None:
        _TABLE_4D = _Table4D()
    return _TABLE_4D


def _reconstruct(
    meet: bytes,
    parents_a: dict[bytes, tuple[bytes, int] | None],
    parents_b: dict[bytes, tuple[bytes, int] | None],
    moves: list,
    invert_index: list[int],
) -> list:
    path: list = []
    node = meet
    while parents_a[node] is not None:
        parent, mi = parents_a[node]
        path.append(moves[mi])
        node = parent
    path.reverse()
    node = meet
    while parents_b[node] is not None:
        parent, mi = parents_b[node]
        path.append(moves[invert_index[mi]])
        node = parent
    return path


def _invert_index(moves: list) -> list[int]:
    index = []
    for move in moves:
        inv = move.inverted()
        for i, other in enumerate(moves):
            if other == inv:
                index.append(i)
                break
        else:
            raise RuntimeError(f"no inverse for {move}")
    return index


def bidirectional_htm(
    start: bytes,
    goal: bytes,
    table: _Table3D | _Table4D,
    *,
    node_limit: int,
    time_limit: float,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    if start == goal:
        return {
            "solved": True,
            "moves": [],
            "htm": 0,
            "optimal": True,
            "nodes": 0,
            "elapsed_sec": 0.0,
            "error": None,
        }
    moves = table.moves
    perms = table.perms
    faces = table.faces
    layers = table.layers
    inv = _invert_index(moves)
    parents_a: dict[bytes, tuple[bytes, int] | None] = {start: None}
    parents_b: dict[bytes, tuple[bytes, int] | None] = {goal: None}
    last_a: dict[bytes, tuple[str, int]] = {start: ("", -1)}
    last_b: dict[bytes, tuple[str, int]] = {goal: ("", -1)}
    qa: deque[bytes] = deque([start])
    qb: deque[bytes] = deque([goal])
    nodes = 0

    def expand(
        queue: deque[bytes],
        parents: dict[bytes, tuple[bytes, int] | None],
        last: dict[bytes, tuple[str, int]],
        other: dict[bytes, tuple[bytes, int] | None],
    ) -> bytes | None:
        nonlocal nodes
        if not queue:
            return None
        count = len(queue)
        for _ in range(count):
            state = queue.popleft()
            prev_face, prev_layer = last[state]
            for mi, perm in enumerate(perms):
                if faces[mi] == prev_face and layers[mi] == prev_layer:
                    continue
                nxt = _apply(state, perm)
                if nxt in parents:
                    continue
                parents[nxt] = (state, mi)
                last[nxt] = (faces[mi], layers[mi])
                queue.append(nxt)
                nodes += 1
                if nxt in other:
                    return nxt
                if nodes >= node_limit:
                    return None
        return None

    meet = None
    while qa and qb and nodes < node_limit:
        if time.perf_counter() - t0 >= time_limit:
            break
        if len(parents_a) <= len(parents_b):
            meet = expand(qa, parents_a, last_a, parents_b)
        else:
            meet = expand(qb, parents_b, last_b, parents_a)
        if meet is not None:
            path = _reconstruct(meet, parents_a, parents_b, moves, inv)
            elapsed = time.perf_counter() - t0
            return {
                "solved": True,
                "moves": path,
                "htm": len(path),
                "optimal": True,
                "nodes": nodes,
                "elapsed_sec": round(elapsed, 4),
                "error": None,
            }
    elapsed = time.perf_counter() - t0
    return {
        "solved": False,
        "moves": [],
        "htm": None,
        "optimal": False,
        "nodes": nodes,
        "elapsed_sec": round(elapsed, 4),
        "error": "search budget exhausted",
    }


def solve_optimal(
    cube: Cube | HyperCube,
    *,
    node_limit: int | None = None,
    time_limit: float = 1.5,
) -> dict[str, Any]:
    skipped = {
        "algorithm": "god_htm",
        "label": "God's algorithm (HTM search)",
        "solved": False,
        "moves": [],
        "text": "",
        "htm": None,
        "optimal": False,
        "nodes": 0,
        "elapsed_sec": 0.0,
        "error": "search skipped",
    }
    if time_limit <= 0:
        return skipped
    if getattr(cube, "ndim", 3) >= 4:
        if getattr(cube, "size", 3) != 3 or getattr(cube, "ndim", 4) != 4:
            skipped["error"] = "HTM search is only tabled for 3×3×3×3"
            return skipped
        table = _table_4d()
        start = facelets_4d(cube)  # type: ignore[arg-type]
        goal = facelets_4d(HyperCube())
        limit = node_limit if node_limit is not None else 40_000
        result = bidirectional_htm(start, goal, table, node_limit=limit, time_limit=time_limit)
        result["algorithm"] = "god_htm"
        result["label"] = "God's algorithm (HTM search)"
        result["move_set"] = "4d-2c"
        result["text"] = format_hyper_moves(result["moves"])
        return result
    size = cube.size
    table = _table_3d(size)
    start = facelets_3d(cube)  # type: ignore[arg-type]
    goal = facelets_3d(Cube(size))
    if node_limit is None:
        if size <= 2:
            limit = 80_000
        elif size == 3:
            limit = 250_000
        else:
            limit = 60_000
    else:
        limit = node_limit
    result = bidirectional_htm(start, goal, table, node_limit=limit, time_limit=time_limit)
    result["algorithm"] = "god_htm"
    result["label"] = "God's algorithm (HTM search)"
    result["move_set"] = f"{size}x{size}x{size}-layers"
    result["text"] = format_moves(result["moves"])
    return result
