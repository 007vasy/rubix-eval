"""WCA-style move notation for NxNxN cubes."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PARSE_RE = re.compile(
    r"""
    \s*
    (?:
        (?P<depth>\d+)?(?P<face>[UDLRFBudlrfb])(?P<wide>w)?(?P<mod>2'|2|'|3)?
        |
        (?P<rot>[xyzXYZ])(?P<rot_mod>2'|2|'|3)?
        |
        (?P<slice>[MESmes])(?P<slice_mod>2'|2|'|3)?
    )
    """,
    re.VERBOSE,
)

_LOWER_WIDE = {"u": "U", "d": "D", "l": "L", "r": "R", "f": "F", "b": "B"}
_TURNS = {None: 1, "": 1, "2": 2, "'": 3, "2'": 2, "3": 3}


@dataclass(frozen=True)
class Move:
    """One layer turn.

    `layer` is 1-indexed from `face`. `wide` turns every layer from the face
    through `layer` (so Rw on 4x4 is layers 1 and 2 from R).
    `turns` is 1, 2, or 3 quarter-turns clockwise.
    """

    face: str
    layer: int = 1
    wide: bool = False
    turns: int = 1

    def __post_init__(self) -> None:
        if self.face not in "UDLRFB":
            raise ValueError(f"Invalid face {self.face!r}")
        if self.layer < 1:
            raise ValueError("layer must be >= 1")
        object.__setattr__(self, "turns", ((self.turns - 1) % 4) + 1)
        if self.turns == 4:
            object.__setattr__(self, "turns", 0)

    def layers(self, size: int) -> list[int]:
        if self.layer > size:
            raise ValueError(f"{self} exceeds cube size {size}")
        if self.wide:
            return list(range(1, self.layer + 1))
        return [self.layer]

    def inverted(self) -> Move:
        if self.turns == 0:
            return self
        return Move(self.face, self.layer, self.wide, 4 - self.turns)

    def qtm_cost(self) -> int:
        if self.turns == 0:
            return 0
        return 2 if self.turns == 2 else 1

    def htm_cost(self) -> int:
        return 0 if self.turns == 0 else 1

    def notation(self) -> str:
        if self.turns == 0:
            return ""
        prefix = ""
        face = self.face
        suffix = {1: "", 2: "2", 3: "'"}[self.turns]
        if self.wide:
            if self.layer == 2:
                return f"{face}w{suffix}"
            return f"{self.layer}{face}w{suffix}"
        if self.layer == 1:
            return f"{face}{suffix}"
        return f"{self.layer}{face}{suffix}"

    def __str__(self) -> str:
        return self.notation()


def parse_moves(algorithm: str) -> list[Move]:
    """Parse a space- or concatenation-friendly move string."""
    if not algorithm or not algorithm.strip():
        return []
    text = algorithm.strip()
    moves: list[Move] = []
    pos = 0
    length = len(text)
    while pos < length:
        if text[pos].isspace() or text[pos] in ",;":
            pos += 1
            continue
        match = _PARSE_RE.match(text, pos)
        if not match:
            raise ValueError(f"Invalid move notation at {text[pos:]!r}")
        pos = match.end()
        if match.group("rot"):
            raise ValueError("Whole-cube rotations (x/y/z) are not allowed during eval")
        if match.group("slice"):
            slice_face = match.group("slice").upper()
            turns = _TURNS[match.group("slice_mod")]
            # M follows L, E follows D, S follows F, on the middle layer.
            face = {"M": "L", "E": "D", "S": "F"}[slice_face]
            moves.append(Move(face=face, layer=2, wide=False, turns=turns))
            continue
        raw_face = match.group("face")
        wide = match.group("wide") is not None
        depth = int(match.group("depth") or 0)
        turns = _TURNS[match.group("mod")]
        if raw_face in _LOWER_WIDE:
            face = _LOWER_WIDE[raw_face]
            wide = True
            layer = depth if depth else 2
        else:
            face = raw_face
            if wide:
                layer = depth if depth else 2
            elif depth:
                layer = depth
            else:
                layer = 1
        moves.append(Move(face=face, layer=layer, wide=wide, turns=turns))
    return moves


def invert_moves(moves: list[Move]) -> list[Move]:
    return [move.inverted() for move in reversed(moves)]


def format_moves(moves: list[Move]) -> str:
    return " ".join(move.notation() for move in moves if move.turns)
