"""n-dimensional N^n Rubik's cubes (MagicCube4D / MPUlt / MC5D–7D analog).

Default is the 3×3×3×3 (3^4): eight cubic cells R L U D F B I O.
Bigger 4D cubes (2^4 … 7^4) use the same eight cells with inner slices.
5D–7D add cell pairs A/K (ana/kata), S/T, M/N — 2n cells total.

A 4D 2c twist `RU` rotates the R cell around U (plane = the other two axes).
A 5D+ 2-plane twist `RUA` rotates the R slice in the U–A plane.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .hyper_moves import HyperMove, parse_hyper_moves

# (negative-extreme letter, positive-extreme letter) per axis.
# 0–3 match MagicCube4D; 4+ follow hypercubing ana/kata then extra pairs.
AXIS_PAIRS = (
    ("L", "R"),
    ("D", "U"),
    ("B", "F"),
    ("I", "O"),
    ("A", "K"),
    ("S", "T"),
    ("M", "N"),
)
CELL_COLOR = {
    "R": "R",
    "L": "O",
    "U": "W",
    "D": "Y",
    "F": "G",
    "B": "B",
    "I": "P",
    "O": "C",
    "A": "A",
    "K": "K",
    "S": "S",
    "T": "T",
    "M": "M",
    "N": "N",
}
OPPOSITE_CELL = {lo: hi for lo, hi in AXIS_PAIRS}
OPPOSITE_CELL.update({hi: lo for lo, hi in AXIS_PAIRS})

# 3^4 defaults (tests and Zhao notation).
CELLS = ("R", "L", "U", "D", "F", "B", "I", "O")
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
AXIS_CELL = {value: key for key, value in CELL_AXIS.items()}


def cells_for(ndim: int) -> tuple[str, ...]:
    if not 3 <= ndim <= 7:
        raise ValueError("ndim must be 3–7")
    names: list[str] = []
    for lo, hi in AXIS_PAIRS[:ndim]:
        names.extend((hi, lo))
    return tuple(names)


def axis_maps(ndim: int, size: int) -> tuple[dict[str, tuple[int, int]], dict[tuple[int, int], str]]:
    cell_axis: dict[str, tuple[int, int]] = {}
    axis_cell: dict[tuple[int, int], str] = {}
    for axis, (lo, hi) in enumerate(AXIS_PAIRS[:ndim]):
        cell_axis[lo] = (axis, 0)
        cell_axis[hi] = (axis, size - 1)
        axis_cell[(axis, 0)] = lo
        axis_cell[(axis, size - 1)] = hi
    return cell_axis, axis_cell


def puzzle_id(ndim: int, size: int) -> str:
    return "x".join([str(size)] * ndim)


def kind_for(ndim: int) -> str:
    return "3d" if ndim == 3 else f"{ndim}d"


def adjacent_cells(cell: str, ndim: int = 4, size: int = 3) -> tuple[str, ...]:
    cell_axis, _ = axis_maps(ndim, size)
    if cell not in cell_axis:
        raise ValueError(f"unknown cell {cell!r} for {ndim}D")
    axis, _ext = cell_axis[cell]
    return tuple(name for name, (a, _) in cell_axis.items() if a != axis)


def two_plane_partners(cell: str, ndim: int, size: int) -> list[tuple[str, str]]:
    """Axis-cell pairs that span a real 2-plane in the cell (distinct axes)."""
    cell_axis, _ = axis_maps(ndim, size)
    if cell not in cell_axis:
        raise ValueError(f"unknown cell {cell!r} for {ndim}D")
    my_axis = cell_axis[cell][0]
    names = [name for name, (axis, _) in cell_axis.items() if axis != my_axis]
    pairs: list[tuple[str, str]] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if cell_axis[a][0] != cell_axis[b][0]:
                pairs.append((a, b))
                pairs.append((b, a))
    return pairs


def _perm_sign(seq: list[int]) -> int:
    inversions = 0
    for i, a in enumerate(seq):
        for b in seq[i + 1 :]:
            if a > b:
                inversions += 1
    return -1 if inversions % 2 else 1


def oriented_plane(cell_axis: int, rot_axis: int, ndim: int = 4, plane: tuple[int, int] | None = None) -> tuple[int, int]:
    """Return (i, j) so +90° in that plane is RH in the cell's remaining space."""
    if plane is not None:
        return plane
    others = [a for a in range(ndim) if a not in (cell_axis, rot_axis)]
    if len(others) < 2:
        raise ValueError("need a 2-plane")
    i, j = others[0], others[1]
    if ndim == 4 and _perm_sign([cell_axis, rot_axis, i, j]) < 0:
        i, j = j, i
    return i, j


class HyperCube:
    """Mutable N^n cube. Stickers live on cubies with at least one extreme coord."""

    def __init__(
        self,
        state: Mapping[str, Any] | None = None,
        *,
        size: int = 3,
        ndim: int = 4,
    ) -> None:
        if state is not None:
            size = int(state.get("size", size))
            ndim = int(state.get("ndim", ndim))
        if not 2 <= size <= 7:
            raise ValueError("nD cube size must be 2–7")
        if not 4 <= ndim <= 7:
            raise ValueError("ndim must be 4–7")
        if size ** ndim > 20000:
            raise ValueError(f"{size}^{ndim} is too large to instantiate")
        self.size = size
        self.ndim = ndim
        self.kind = kind_for(ndim)
        self._cell_axis, self._axis_cell = axis_maps(ndim, size)
        self._cells = cells_for(ndim)
        self._cubies: dict[tuple[int, ...], dict[str, str]] = {}
        if state is None:
            self.reset()
        elif "cubies" in state:
            self._load_cubies(state["cubies"])
        else:
            self.set_cells(state["cells"] if "cells" in state else state)

    def reset(self) -> None:
        n = self.size
        d = self.ndim
        self._cubies.clear()

        def walk(prefix: list[int]) -> None:
            if len(prefix) == d:
                pos = tuple(prefix)
                colors: dict[str, str] = {}
                for axis, coord in enumerate(pos):
                    if coord in (0, n - 1):
                        cell = self._axis_cell[(axis, coord)]
                        colors[cell] = CELL_COLOR[cell]
                if colors:
                    self._cubies[pos] = colors
                return
            for i in range(n):
                prefix.append(i)
                walk(prefix)
                prefix.pop()

        walk([])

    def copy(self) -> HyperCube:
        clone = HyperCube.__new__(HyperCube)
        clone.size = self.size
        clone.ndim = self.ndim
        clone.kind = self.kind
        clone._cell_axis = self._cell_axis
        clone._axis_cell = self._axis_cell
        clone._cells = self._cells
        clone._cubies = {pos: dict(colors) for pos, colors in self._cubies.items()}
        return clone

    def is_solved(self) -> bool:
        """Solved if every cell is one color and those colors are all different.

        A whole-puzzle 4D rotation (e.g. R/L swapped, U/D swapped) still counts:
        each cell is uniform, just sitting in another orientation.
        """
        seen: set[str] = set()
        expected = {CELL_COLOR[cell] for cell in self._cells}
        for cell in self._cells:
            stickers = self.cell_stickers_flat(cell)
            if not stickers:
                return False
            color = stickers[0]
            if color not in expected or any(s != color for s in stickers):
                return False
            if color in seen:
                return False
            seen.add(color)
        return seen == expected

    def apply(self, moves: str | Iterable[HyperMove]) -> list[HyperMove]:
        parsed = (
            parse_hyper_moves(moves, ndim=self.ndim) if isinstance(moves, str) else list(moves)
        )
        for move in parsed:
            self._apply_move(move)
        return parsed

    def _layer_coord(self, cell: str, layer: int | None) -> int:
        _axis, ext = self._cell_axis[cell]
        if layer is None or layer <= 1:
            return ext
        step = 1 if ext == 0 else -1
        coord = ext + step * (layer - 1)
        if coord < 0 or coord >= self.size:
            raise ValueError(f"layer {layer} out of range for size {self.size}")
        return coord

    def _apply_move(self, move: HyperMove) -> None:
        if move.cell not in self._cell_axis:
            raise ValueError(f"invalid nD move {move}")
        if move.order == 4:
            plane = None
            axis = move.axis
            if self.ndim > 4 and len(move.axis_cells) >= 2:
                plane = (
                    self._cell_axis[move.axis_cells[0]][0],
                    self._cell_axis[move.axis_cells[1]][0],
                )
                if plane[0] == plane[1]:
                    raise ValueError(f"{move}: 2-plane needs two distinct axes")
                axis = move.axis_cells[0]
            if axis not in self._cell_axis:
                raise ValueError(f"invalid nD move {move}")
            if self._cell_axis[move.cell][0] == self._cell_axis[axis][0] and plane is None:
                raise ValueError(f"{move}: cell and axis must be on different axes")
            self._twist_90(move.cell, axis, move.turns, layer=move.layer, plane=plane)
        elif move.order == 2:
            axis = move.axis_cells[0] if move.axis_cells else move.axis[0]
            self._twist_90(move.cell, axis, (move.turns * 2) % 4, layer=move.layer)
        else:
            self._twist_120(move.cell, move.axis_cells, move.turns)

    def _twist_90(
        self,
        cell: str,
        axis_cell: str,
        turns: int,
        *,
        layer: int | None = None,
        plane: tuple[int, int] | None = None,
    ) -> None:
        n = self.size
        cell_axis, cell_ext = self._cell_axis[cell]
        rot_axis, rot_ext = self._cell_axis[axis_cell]
        layer_coord = self._layer_coord(cell, layer)
        turns %= 4
        if rot_ext == 0:
            turns = (-turns) % 4
        if cell_ext == 0:
            turns = (-turns) % 4
        if turns == 0:
            return
        i, j = oriented_plane(cell_axis, rot_axis, self.ndim, plane)
        plus_i = self._axis_cell[(i, n - 1)]
        minus_i = self._axis_cell[(i, 0)]
        plus_j = self._axis_cell[(j, n - 1)]
        minus_j = self._axis_cell[(j, 0)]
        cycle = [plus_i, plus_j, minus_i, minus_j]
        mapping = {cycle[k]: cycle[(k + turns) % 4] for k in range(4)}

        moving = {pos: colors for pos, colors in self._cubies.items() if pos[cell_axis] == layer_coord}
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
        """120° around a space diagonal of the cubic cell (4c click). 4D only."""
        n = self.size
        cell_axis, cell_ext = self._cell_axis[cell]
        if len(axis_cells) != 3:
            raise ValueError("4c twist needs three axis cells")
        turns %= 3
        if turns == 0:
            return
        cell_axes = [self._cell_axis[name][0] for name in axis_cells]
        if sorted(cell_axes) != sorted(a for a in range(self.ndim) if a != cell_axis)[:3]:
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

    def cubie_at(self, pos: tuple[int, ...]) -> dict[str, str]:
        return dict(self._cubies[pos])

    def piece_counts(self) -> dict[int, int]:
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for colors in self._cubies.values():
            counts[len(colors)] += 1
        return counts

    def cell_local_axes(self, cell: str) -> tuple[int, ...]:
        cell_axis, _ = self._cell_axis[cell]
        return tuple(a for a in range(self.ndim) if a != cell_axis)

    def cell_stickers(self, cell: str) -> list[list[list[str]]]:
        """3×3×3 sticker colors on `cell`, indexed by the three local axes."""
        n = self.size
        cell_axis, cell_ext = self._cell_axis[cell]
        local = self.cell_local_axes(cell)
        if len(local) != 3:
            raise ValueError("cell_stickers 3D grid is only for 4D cells")
        a, b, c = local
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
        if self.ndim == 4:
            return [sticker for layer in self.cell_stickers(cell) for row in layer for sticker in row]
        cell_axis, cell_ext = self._cell_axis[cell]
        return [
            colors[cell]
            for pos, colors in self._cubies.items()
            if pos[cell_axis] == cell_ext and cell in colors
        ]

    def cells(self) -> dict[str, list[list[list[str]]]]:
        return {cell: self.cell_stickers(cell) for cell in self._cells}

    def set_cells(self, cells: Mapping[str, list[list[list[str]]]]) -> None:
        n = self.size
        self._cubies.clear()
        for cell, grid in cells.items():
            cell_axis, cell_ext = self._cell_axis[cell]
            a, b, c = self.cell_local_axes(cell)[:3]
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
        for cell in self._cells:
            stickers = self.cell_stickers_flat(cell)
            if not stickers:
                continue
            color = stickers[0]
            count += sum(1 for s in stickers if s != color)
        return count

    def _load_cubies(self, cubies: Iterable[Mapping[str, Any]]) -> None:
        self._cubies.clear()
        for row in cubies:
            pos = tuple(int(v) for v in row["pos"])
            self._cubies[pos] = {str(k): str(v) for k, v in dict(row["colors"]).items()}

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "size": self.size,
            "ndim": self.ndim,
            "cubies": [
                {"pos": list(pos), "colors": dict(colors)}
                for pos, colors in sorted(self._cubies.items())
            ],
        }
        if self.ndim == 4:
            data["cells"] = self.cells()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HyperCube:
        return cls(state=data, size=int(data.get("size", 3)), ndim=int(data.get("ndim", 4)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HyperCube):
            return NotImplemented
        return self._cubies == other._cubies
