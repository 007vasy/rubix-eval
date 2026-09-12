"""NxNxN Rubik's cube.

Coordinates: x right (0=L .. n-1=R), y up (0=D .. n-1=U), z front (0=B .. n-1=F).
A quarter turn is clockwise as viewed from outside the named face (WCA).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .moves import Move, parse_moves

FACES = ("U", "D", "F", "B", "L", "R")
FACE_COLOR = {"U": "W", "D": "Y", "F": "G", "B": "B", "L": "O", "R": "R"}
COLOR_TO_FACE = {color: face for face, color in FACE_COLOR.items()}

# WCA clockwise quarter turns, as right-hand rotations about +axis:
# R,U use +1; L,D use -1; F uses -1; B uses +1. See module tests.
_FACE_AXIS = {"R": 0, "L": 0, "U": 1, "D": 1, "F": 2, "B": 2}
_FACE_LAYER_FROM_ZERO = {"L": True, "D": True, "B": True, "R": False, "U": False, "F": False}
# Quarter-turn sign about the +axis so each named face is WCA-clockwise
# from outside. Tuned against the standard nets (F-right goes to U on R, etc.).
_FACE_DIR = {"R": -1, "L": 1, "U": -1, "D": 1, "F": -1, "B": 1}

# Color cycles for +1 right-hand quarter turn about each +axis.
_COLOR_CYCLE = {
    0: ("U", "F", "D", "B"),
    1: ("R", "B", "L", "F"),
    2: ("R", "U", "L", "D"),
}


class Cube:
    """Mutable NxNxN cube. Stickers live on outer cubies only."""

    def __init__(self, size: int = 3, state: Mapping[str, Any] | None = None) -> None:
        if size < 2:
            raise ValueError("Cube size must be >= 2")
        self.size = size
        self._cubies: dict[tuple[int, int, int], dict[str, str]] = {}
        if state is None:
            self.reset()
        else:
            self.set_faces(state["faces"] if "faces" in state else state)

    def reset(self) -> None:
        n = self.size
        self._cubies.clear()
        for x in range(n):
            for y in range(n):
                for z in range(n):
                    if not _is_outer(x, y, z, n):
                        continue
                    colors: dict[str, str] = {}
                    if x == 0:
                        colors["L"] = FACE_COLOR["L"]
                    if x == n - 1:
                        colors["R"] = FACE_COLOR["R"]
                    if y == 0:
                        colors["D"] = FACE_COLOR["D"]
                    if y == n - 1:
                        colors["U"] = FACE_COLOR["U"]
                    if z == 0:
                        colors["B"] = FACE_COLOR["B"]
                    if z == n - 1:
                        colors["F"] = FACE_COLOR["F"]
                    self._cubies[(x, y, z)] = colors

    def copy(self) -> Cube:
        clone = Cube.__new__(Cube)
        clone.size = self.size
        clone._cubies = {pos: dict(colors) for pos, colors in self._cubies.items()}
        return clone

    def is_solved(self) -> bool:
        n = self.size
        for face in FACES:
            grid = self.face_grid(face)
            expected = FACE_COLOR[face]
            for row in grid:
                for sticker in row:
                    if sticker != expected:
                        return False
            if len(grid) != n:
                return False
        return True

    def apply(self, moves: str | Iterable[Move]) -> list[Move]:
        parsed = parse_moves(moves) if isinstance(moves, str) else list(moves)
        for move in parsed:
            self._apply_move(move)
        return parsed

    def _apply_move(self, move: Move) -> None:
        n = self.size
        axis = _FACE_AXIS[move.face]
        from_zero = _FACE_LAYER_FROM_ZERO[move.face]
        layers = move.layers(n)
        if from_zero:
            slice_indices = [layer - 1 for layer in layers]
        else:
            slice_indices = [n - layer for layer in layers]
        direction = (_FACE_DIR[move.face] * move.turns) % 4
        if direction == 0:
            return
        self._rotate_slices(axis, slice_indices, direction)

    def _rotate_slices(self, axis: int, slice_indices: list[int], turns: int) -> None:
        n = self.size
        moving = {
            pos: colors
            for pos, colors in self._cubies.items()
            if pos[axis] in slice_indices
        }
        for pos in moving:
            del self._cubies[pos]
        for (x, y, z), colors in moving.items():
            nx, ny, nz = _rotate_position(x, y, z, n, axis, turns)
            self._cubies[(nx, ny, nz)] = _rotate_colors(colors, axis, turns)

    def face_grid(self, face: str) -> list[list[str]]:
        n = self.size
        grid = [[""] * n for _ in range(n)]
        for r in range(n):
            for c in range(n):
                x, y, z = _face_coords(face, r, c, n)
                grid[r][c] = self._cubies[(x, y, z)][face]
        return grid

    def faces(self) -> dict[str, list[list[str]]]:
        return {face: self.face_grid(face) for face in FACES}

    def set_faces(self, faces: Mapping[str, list[list[str]]]) -> None:
        n = self.size
        self._cubies.clear()
        for face, grid in faces.items():
            if face not in FACES:
                raise ValueError(f"Unknown face {face!r}")
            if len(grid) != n or any(len(row) != n for row in grid):
                raise ValueError(f"Face {face} is not {n}x{n}")
            for r in range(n):
                for c in range(n):
                    x, y, z = _face_coords(face, r, c, n)
                    self._cubies.setdefault((x, y, z), {})[face] = str(grid[r][c])
        expected = sum(1 for x in range(n) for y in range(n) for z in range(n) if _is_outer(x, y, z, n))
        if len(self._cubies) != expected:
            raise ValueError("Incomplete cube state")

    def facelet_string(self, order: Iterable[str] = ("U", "R", "F", "D", "L", "B")) -> str:
        return "".join("".join("".join(row) for row in self.face_grid(face)) for face in order)

    def cubie_at(self, pos: tuple[int, int, int]) -> dict[str, str]:
        return dict(self._cubies[pos])

    def misplaced_stickers(self) -> int:
        count = 0
        for face in FACES:
            expected = FACE_COLOR[face]
            for row in self.face_grid(face):
                count += sum(1 for sticker in row if sticker != expected)
        return count

    def to_dict(self) -> dict[str, Any]:
        return {"size": self.size, "faces": self.faces()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Cube:
        return cls(size=int(data["size"]), state=data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cube):
            return NotImplemented
        return self.size == other.size and self._cubies == other._cubies

    def __hash__(self) -> int:
        items = tuple(sorted((pos, tuple(sorted(colors.items()))) for pos, colors in self._cubies.items()))
        return hash((self.size, items))


def _is_outer(x: int, y: int, z: int, n: int) -> bool:
    return x in (0, n - 1) or y in (0, n - 1) or z in (0, n - 1)


def _rotate_position(x: int, y: int, z: int, n: int, axis: int, turns: int) -> tuple[int, int, int]:
    turns %= 4
    for _ in range(turns):
        if axis == 0:
            y, z = n - 1 - z, y
        elif axis == 1:
            x, z = z, n - 1 - x
        else:
            x, y = n - 1 - y, x
    return x, y, z


def _rotate_colors(colors: dict[str, str], axis: int, turns: int) -> dict[str, str]:
    turns %= 4
    if turns == 0:
        return dict(colors)
    cycle = _COLOR_CYCLE[axis]
    mapping = {cycle[i]: cycle[(i + turns) % 4] for i in range(4)}
    return {mapping.get(face, face): color for face, color in colors.items()}


def _face_coords(face: str, row: int, col: int, n: int) -> tuple[int, int, int]:
    if face == "U":
        return col, n - 1, row
    if face == "D":
        return col, 0, n - 1 - row
    if face == "F":
        return col, n - 1 - row, n - 1
    if face == "B":
        return n - 1 - col, n - 1 - row, 0
    if face == "L":
        return 0, n - 1 - row, col
    if face == "R":
        return n - 1, n - 1 - row, n - 1 - col
    raise ValueError(f"Unknown face {face!r}")
