"""ASCII cube nets for agent prompts and terminals."""

from __future__ import annotations

from .cube import Cube, FACE_COLOR

_ANSI = {
    "W": "\033[97m",
    "Y": "\033[93m",
    "G": "\033[92m",
    "B": "\033[94m",
    "O": "\033[38;5;208m",
    "R": "\033[91m",
}
_RESET = "\033[0m"


def _cell(sticker: str, color: bool) -> str:
    if not color:
        return sticker
    return f"{_ANSI.get(sticker, '')}{sticker}{_RESET}"


def ascii_net(cube: Cube, *, color: bool = False) -> str:
    """Unfolded net: U on top, L F R B in a row, D on the bottom."""
    n = cube.size
    u, d, f, b, l, r = (cube.face_grid(face) for face in ("U", "D", "F", "B", "L", "R"))
    pad = " " * (n * 2)
    lines: list[str] = []
    for row in u:
        lines.append(pad + " ".join(_cell(s, color) for s in row))
    for i in range(n):
        band = [
            " ".join(_cell(s, color) for s in l[i]),
            " ".join(_cell(s, color) for s in f[i]),
            " ".join(_cell(s, color) for s in r[i]),
            " ".join(_cell(s, color) for s in b[i]),
        ]
        lines.append("  ".join(band))
    for row in d:
        lines.append(pad + " ".join(_cell(s, color) for s in row))
    return "\n".join(lines)


def legend() -> str:
    names = {
        "W": "white  (U)",
        "Y": "yellow (D)",
        "G": "green  (F)",
        "B": "blue   (B)",
        "O": "orange (L)",
        "R": "red    (R)",
    }
    return "Colors: " + ", ".join(f"{ch}={name}" for ch, name in names.items())


def solved_face_color(face: str) -> str:
    return FACE_COLOR[face]
