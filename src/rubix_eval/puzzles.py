"""On-demand n^d puzzles and which ones have a human record.

Sources: MagicCube4D Hall of Fame, MPUlt, Hypercubing leaderboards
(https://github.com/cutelyaware/magiccube4d, https://github.com/cutelyaware/MPUlt,
https://hypercubing.xyz/leaderboards/records/).
"""

from __future__ import annotations

from typing import Any

# Equal-sided n^d cubes we can instantiate on demand.
# visual: 4D size 2–5 is drawable; higher D is JSON/ASCII only.
ND_PUZZLES: tuple[dict[str, Any], ...] = (
    {"ndim": 4, "size": 2, "visual": True, "full_depth": 20},
    {"ndim": 4, "size": 3, "visual": True, "full_depth": 40},
    {"ndim": 4, "size": 4, "visual": True, "full_depth": 80},
    {"ndim": 4, "size": 5, "visual": True, "full_depth": 120},
    {"ndim": 4, "size": 6, "visual": False, "full_depth": 160},
    {"ndim": 4, "size": 7, "visual": False, "full_depth": 200},
    {"ndim": 5, "size": 2, "visual": False, "full_depth": 40},
    {"ndim": 5, "size": 3, "visual": False, "full_depth": 80},
    {"ndim": 5, "size": 4, "visual": False, "full_depth": 160},
    {"ndim": 6, "size": 2, "visual": False, "full_depth": 60},
    {"ndim": 6, "size": 3, "visual": False, "full_depth": 120},
    {"ndim": 7, "size": 2, "visual": False, "full_depth": 80},
    {"ndim": 7, "size": 3, "visual": False, "full_depth": 160},
)


def nd_label(ndim: int, size: int) -> str:
    return "×".join([str(size)] * ndim) + f" ({ndim}D)"


def nd_key(ndim: int, size: int) -> str:
    return "x".join([str(size)] * ndim)


def find_puzzle(ndim: int, size: int) -> dict[str, Any] | None:
    for row in ND_PUZZLES:
        if row["ndim"] == ndim and row["size"] == size:
            return dict(row)
    return None


def infer_ndim(kind: str | None, size: int | None = None, ndim: int | None = None) -> int:
    if ndim:
        return int(ndim)
    if kind and kind.endswith("d") and kind[0].isdigit():
        return int(kind[0])
    return 3


def puzzle_label(kind: str | None, size: int, ndim: int | None = None, depth_label: str | None = None, scramble_depth: int | None = None) -> str:
    d = infer_ndim(kind, size, ndim)
    n = int(size or 3)
    shape = nd_label(d, n) if d >= 4 else f"{n}×{n}×{n}"
    if depth_label == "full":
        return f"{shape} · full"
    if depth_label:
        return f"{shape} · d{depth_label}"
    if scramble_depth is not None:
        return f"{shape} · d{scramble_depth}"
    return shape


def difficulty_tuple(
    *,
    kind: str | None,
    size: int | None,
    scramble_depth: int | None,
    depth_label: str | None = None,
    ndim: int | None = None,
) -> tuple[int, int, int, int]:
    """Harder first when sorted reverse: dimension, size, full scramble, depth."""
    d = infer_ndim(kind, size, ndim)
    n = int(size or 3)
    depth = int(scramble_depth or 0)
    full = 1 if depth_label == "full" else 0
    return (d, n, full, depth)


def difficulty_score(key: tuple[int, int, int, int]) -> int:
    d, n, full, depth = key
    return d * 1_000_000 + n * 1_000 + full * 500 + depth


def ensure_puzzle(ndim: int, size: int) -> dict[str, Any]:
    """Allow any 4–7D size 2–7 on demand, even if not in the stock list."""
    stock = find_puzzle(ndim, size)
    if stock:
        return stock
    if not 4 <= ndim <= 7 or not 2 <= size <= 7:
        raise ValueError("on-demand nD cubes are ndim 4–7 and size 2–7")
    return {
        "ndim": ndim,
        "size": size,
        "visual": ndim == 4 and size <= 5,
        "full_depth": max(20, size * ndim * 5),
    }
