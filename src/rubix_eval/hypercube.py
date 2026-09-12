"""3×3×3×3 (3^4) Rubik's cube — the 4D analog of a 3×3×3.

A tesseract with two cuts on each of four axes. Eight cubic *cells*
(R L U D F B I O) hold 3×3×3 cubical stickers. A twist rotates one cell
in its 3-space; the basic generators are 90° 2c-clicks (Zhao notation:
`RU` = twist the R cell around the U axis).

Coordinates: x (L=0 .. R=2), y (D=0 .. U=2), z (B=0 .. F=2), w (I=0 .. O=2).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .hyper_moves import HyperMove, parse_hyper_moves

CELLS = ("R", "L", "U", "D", "F", "B", "I", "O")
# Cell -> (axis, extreme). Axis 0=x, 1=y, 2=z, 3=w.
CELL_AXIS = {
    "R": (0, 2),
    "L": (0, 0),
    "U": (1, 2),
    "D": (1, 0),
    "F": (2, 2),
    "B": (2, 0),
    "O": (3, 2),
    "I": (3, 0),
}
AXIS_CELL = {
    (0, 2): "R",
    (0, 0): "L",
    (1, 2): "U",
    (1, 0): "D",
    (2, 2): "F",
    (2, 0): "B",
    (3, 2): "O",
    (3, 0): "I",
}
CELL_COLOR = {
    "R": "R",
    "L": "O",
    "U": "W",
    "D": "Y",
    "F": "G",
    "B": "B",
    "I": "P",
    "O": "C",
}
OPPOSITE_CELL = {
    "R": "L",
    "L": "R",
    "U": "D",
    "D": "U",
    "F": "B",
    "B": "F",
    "I": "O",
    "O": "I",
}


def adjacent_cells(cell: str) -> tuple[str, ...]:
    axis, _ = CELL_AXIS[cell]
    return tuple(name for name, (a, _) in CELL_AXIS.items() if a != axis)


def _perm_sign(seq: list[int]) -> int:
    inversions = 0
    for i, a in enumerate(seq):
        for b in seq[i + 1 :]:
            if a > b:
                inversions += 1
    return -1 if inversions % 2 else 1


def oriented_plane(cell_axis: int, rot_axis: int) -> tuple[int, int]:
    """Return (i, j) so +90° in that plane is RH in the cell 3-space."""
    others = [a for a in range(4) if a not in (cell_axis, rot_axis)]
    i, j = others[0], others[1]
    if _perm_sign([cell_axis, rot_axis, i, j]) < 0:
        i, j = j, i
    return i, j


class HyperCube:
    """Mutable 3×3×3×3. Stickers live on cubies with at least one extreme coord."""

    size = 3
    ndim = 4
    kind = "4d"

    def __init__(self, state: Mapping[str, Any] | None = None) -> None:
        self._cubies: dict[tuple[int, int, int, int], dict[str, str]] = {}
        if state is None:
            self.reset()
        else:
            self.set_cells(state["cells"] if "cells" in state else state)

    def reset(self) -> None:
        n = self.size
        self._cubies.clear()
        for x in range(n):
            for y in range(n):
                for z in range(n):
                    for w in range(n):
                        pos = (x, y, z, w)
                        colors: dict[str, str] = {}
                        for coord, axis in ((x, 0), (y, 1), (z, 2), (w, 3)):
                            if coord in (0, n - 1):
                                cell = AXIS_CELL[(axis, coord)]
                                colors[cell] = CELL_COLOR[cell]
                        if colors:
                            self._cubies[pos] = colors

    def copy(self) -> HyperCube:
        clone = HyperCube.__new__(HyperCube)
        clone._cubies = {pos: dict(colors) for pos, colors in self._cubies.items()}
        return clone

    def is_solved(self) -> bool:
        for cell in CELLS:
            expected = CELL_COLOR[cell]
            for sticker in self.cell_stickers_flat(cell):
                if sticker != expected:
                    return False
        return True

    def apply(self, moves: str | Iterable[HyperMove]) -> list[HyperMove]:
        parsed = parse_hyper_moves(moves) if isinstance(moves, str) else list(moves)
        for move in parsed:
            self._apply_move(move)
        return parsed

    def _apply_move(self, move: HyperMove) -> None:
        if move.cell not in CELL_AXIS or move.axis not in CELL_AXIS:
            raise ValueError(f"invalid 4D move {move}")
        if CELL_AXIS[move.cell][0] == CELL_AXIS[move.axis][0]:
            raise ValueError(f"{move}: cell and axis must be on different 4D axes")
        if move.order == 4:
            self._twist_90(move.cell, move.axis, move.turns)
        elif move.order == 2:
            self._twist_90(move.cell, move.axis, (move.turns * 2) % 4)
        else:
            self._twist_120(move.cell, move.axis_cells, move.turns)

    def _twist_90(self, cell: str, axis_cell: str, turns: int) -> None:
        n = self.size
        cell_axis, cell_ext = CELL_AXIS[cell]
        rot_axis, rot_ext = CELL_AXIS[axis_cell]
        turns %= 4
        if rot_ext == 0:
            turns = (-turns) % 4
        if cell_ext == 0:
            turns = (-turns) % 4
        if turns == 0:
            return
        i, j = oriented_plane(cell_axis, rot_axis)
        plus_i = AXIS_CELL[(i, n - 1)]
        minus_i = AXIS_CELL[(i, 0)]
        plus_j = AXIS_CELL[(j, n - 1)]
        minus_j = AXIS_CELL[(j, 0)]
        cycle = [plus_i, plus_j, minus_i, minus_j]
        mapping = {cycle[k]: cycle[(k + turns) % 4] for k in range(4)}

        moving = {pos: colors for pos, colors in self._cubies.items() if pos[cell_axis] == cell_ext}
        for pos in moving:
            del self._cubies[pos]
        for pos, colors in moving.items():
            new_pos = list(pos)
            ci, cj = pos[i], pos[j]
            for _ in range(turns):
                ci, cj = n - 1 - cj, ci
            new_pos[i] = ci
            new_pos[j] = cj
            new_colors = {mapping.get(face, face): color for face, color in colors.items()}
            self._cubies[tuple(new_pos)] = new_colors

    def _twist_120(self, cell: str, axis_cells: tuple[str, ...], turns: int) -> None:
        """120° around a space diagonal of the cubic cell (4c click)."""
        n = self.size
        cell_axis, cell_ext = CELL_AXIS[cell]
        if len(axis_cells) != 3:
            raise ValueError("4c twist needs three axis cells")
        turns %= 3
        if turns == 0:
            return
        cell_axes = [CELL_AXIS[name][0] for name in axis_cells]
        if sorted(cell_axes) != sorted(a for a in range(4) if a != cell_axis):
            raise ValueError("4c axis cells must be the three axes of the cell")
        # Cycle the three cell-subspace coordinates.
        a, b, c = cell_axes
        if cell_ext == 0:
            turns = (-turns) % 3
        moving = {pos: colors for pos, colors in self._cubies.items() if pos[cell_axis] == cell_ext}
        for pos in moving:
            del self._cubies[pos]
        names = [axis_cells[0], axis_cells[1], axis_cells[2]]
        name_cycle = {names[k]: names[(k + turns) % 3] for k in range(3)}
        # Also cycle opposite cells the same way (the other extreme of each axis).
        opp = [OPPOSITE_CELL[n] for n in names]
        for k in range(3):
            name_cycle[opp[k]] = opp[(k + turns) % 3]
        for pos, colors in moving.items():
            coords = [pos[a], pos[b], pos[c]]
            for _ in range(turns):
                coords = [coords[2], coords[0], coords[1]]
            new_pos = list(pos)
            new_pos[a], new_pos[b], new_pos[c] = coords
            new_colors = {name_cycle.get(face, face): color for face, color in colors.items()}
            self._cubies[tuple(new_pos)] = new_colors

    def cubie_at(self, pos: tuple[int, int, int, int]) -> dict[str, str]:
        return dict(self._cubies[pos])

    def piece_counts(self) -> dict[int, int]:
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for colors in self._cubies.values():
            counts[len(colors)] += 1
        return counts

    def cell_local_axes(self, cell: str) -> tuple[int, int, int]:
        cell_axis, _ = CELL_AXIS[cell]
        return tuple(a for a in range(4) if a != cell_axis)  # type: ignore[return-value]

    def cell_stickers(self, cell: str) -> list[list[list[str]]]:
        """3×3×3 sticker colors on `cell`, indexed by the three local axes."""
        n = self.size
        cell_axis, cell_ext = CELL_AXIS[cell]
        a, b, c = self.cell_local_axes(cell)
        grid = [[[""] * n for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    pos = [0, 0, 0, 0]
                    pos[cell_axis] = cell_ext
                    pos[a], pos[b], pos[c] = i, j, k
                    grid[k][j][i] = self._cubies[tuple(pos)][cell]
        return grid

    def cell_stickers_flat(self, cell: str) -> list[str]:
        return [sticker for layer in self.cell_stickers(cell) for row in layer for sticker in row]

    def cells(self) -> dict[str, list[list[list[str]]]]:
        return {cell: self.cell_stickers(cell) for cell in CELLS}

    def set_cells(self, cells: Mapping[str, list[list[list[str]]]]) -> None:
        n = self.size
        self._cubies.clear()
        for cell, grid in cells.items():
            cell_axis, cell_ext = CELL_AXIS[cell]
            a, b, c = self.cell_local_axes(cell)
            for k in range(n):
                for j in range(n):
                    for i in range(n):
                        pos = [0, 0, 0, 0]
                        pos[cell_axis] = cell_ext
                        pos[a], pos[b], pos[c] = i, j, k
                        key = tuple(pos)
                        self._cubies.setdefault(key, {})[cell] = str(grid[k][j][i])

    def misplaced_stickers(self) -> int:
        count = 0
        for cell in CELLS:
            expected = CELL_COLOR[cell]
            count += sum(1 for s in self.cell_stickers_flat(cell) if s != expected)
        return count

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "4d", "size": 3, "ndim": 4, "cells": self.cells()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HyperCube:
        return cls(state=data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HyperCube):
            return NotImplemented
        return self._cubies == other._cubies
