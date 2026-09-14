"""Zhao-style 4D move notation for the 3×3×3×3.

`RU`  — twist the R cell 90° around the U axis (2c click on the R sticker of RU).
`RU'` — counter-clockwise.
`RU2` — 180°.

A 4c click is written with four letters (`RUFO`); a 3c click with three (`RUF`).
Eval scrambles use 2c 90° twists only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CELLS = frozenset("UDLRFBIOAKSTMN")
_PARSE_RE = re.compile(
    r"\s*(?P<layer>\d+)?(?P<letters>[UDLRFBIOAKSTMN]{2,4})(?P<mod>2'|2|'|3)?"
)
_TURNS = {None: 1, "": 1, "2": 2, "'": 3, "2'": 2, "3": 3}


@dataclass(frozen=True)
class HyperMove:
    cell: str
    axis: str
    turns: int = 1
    order: int = 4  # 4 = 90° (2c / 2-plane), 2 = 180° (3c), 3 = 120° (4c)
    axis_cells: tuple[str, ...] = ()
    layer: int | None = None

    def __post_init__(self) -> None:
        if self.cell not in _CELLS:
            raise ValueError(f"invalid cell {self.cell!r}")
        if self.order == 4:
            if not self.axis_cells:
                if self.axis not in _CELLS or self.axis == self.cell:
                    raise ValueError(f"invalid 2c axis {self.axis!r}")
                object.__setattr__(self, "axis_cells", (self.axis,))
            object.__setattr__(self, "turns", ((self.turns - 1) % 4) + 1)
            if self.turns == 4:
                object.__setattr__(self, "turns", 0)
        elif self.order == 3:
            object.__setattr__(self, "turns", ((self.turns - 1) % 3) + 1)
            if self.turns == 3:
                object.__setattr__(self, "turns", 0)
        elif self.order == 2:
            object.__setattr__(self, "turns", self.turns % 2)

    def inverted(self) -> HyperMove:
        if self.turns == 0:
            return self
        if self.order == 4:
            return HyperMove(self.cell, self.axis, 4 - self.turns, 4, self.axis_cells, self.layer)
        if self.order == 3:
            return HyperMove(self.cell, self.axis, 3 - self.turns, 3, self.axis_cells, self.layer)
        return HyperMove(self.cell, self.axis, self.turns, 2, self.axis_cells, self.layer)

    def htm_cost(self) -> int:
        return 0 if self.turns == 0 else 1

    def qtm_cost(self) -> int:
        if self.turns == 0:
            return 0
        if self.order == 4:
            return 2 if self.turns == 2 else 1
        if self.order == 3:
            return 1
        return 2

    def notation(self) -> str:
        if self.turns == 0:
            return ""
        prefix = str(self.layer) if self.layer and self.layer > 1 else ""
        letters = self.cell + "".join(self.axis_cells or (self.axis,))
        if self.order == 4:
            suffix = {1: "", 2: "2", 3: "'"}[self.turns]
            return prefix + letters + suffix
        elif self.order == 3:
            suffix = {1: "", 2: "2"}.get(self.turns, "")
        else:
            suffix = "2" if self.turns else ""
        return prefix + letters + suffix

    def __str__(self) -> str:
        return self.notation()


def parse_hyper_moves(algorithm: str, *, ndim: int = 4) -> list[HyperMove]:
    if not algorithm or not str(algorithm).strip():
        return []
    text = str(algorithm).strip()
    moves: list[HyperMove] = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace() or text[pos] in ",;":
            pos += 1
            continue
        match = _PARSE_RE.match(text, pos)
        if not match:
            raise ValueError(f"Invalid nD move notation at {text[pos:]!r}")
        pos = match.end()
        letters = match.group("letters")
        turns_raw = _TURNS[match.group("mod")]
        layer = int(match.group("layer")) if match.group("layer") else None
        cell = letters[0]
        rest = tuple(letters[1:])
        if len(rest) == 1:
            moves.append(HyperMove(cell, rest[0], turns_raw, 4, rest, layer))
        elif len(rest) == 2 and ndim >= 5:
            moves.append(HyperMove(cell, rest[0], turns_raw, 4, rest, layer))
        elif len(rest) == 2:
            moves.append(HyperMove(cell, "".join(rest), 1, 2, rest, layer))
        else:
            if match.group("mod") == "2":
                turns = 2
            elif match.group("mod") in ("'", "3"):
                turns = 2
            else:
                turns = 1
            moves.append(HyperMove(cell, "".join(rest), turns, 3, rest, layer))
    return moves


def invert_hyper_moves(moves: list[HyperMove]) -> list[HyperMove]:
    return [move.inverted() for move in reversed(moves)]


def format_hyper_moves(moves: list[HyperMove]) -> str:
    return " ".join(move.notation() for move in moves if move.turns)
