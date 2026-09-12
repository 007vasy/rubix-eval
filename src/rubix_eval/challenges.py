"""Challenge catalog. Each request draws a fresh random instance."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from .task import EvalTask, make_hyper_task, make_task

# 2×2×2 through 10×10×10, then 40×40×40 and 100×100×100.
SIZES = (2, 3, 4, 5, 6, 7, 8, 9, 10, 40, 100)
# Browser/computer-use pool. 40³ and 100³ are too heavy to draw as meshes.
VISUAL_SIZES = (2, 3, 4, 5, 6, 7, 8, 9, 10)
# 1–10 random turns from solved, plus a full scramble.
DEPTH_LABELS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "full")

_FULL_DEPTH = {
    2: 11,
    3: 25,
    4: 45,
    5: 60,
    6: 80,
    7: 100,
    8: 120,
    9: 140,
    10: 160,
    40: 480,
    100: 1200,
}


def full_scramble_depth(size: int, kind: str = "3d") -> int:
    """WCA-style 'fully scrambled' length for this cube."""
    if kind == "4d":
        return 40
    return _FULL_DEPTH.get(size, max(25, size * 12))


def resolve_depth(size: int, depth: int | str, kind: str = "3d") -> tuple[int, str]:
    if depth in ("full", "FULL"):
        return full_scramble_depth(size, kind), "full"
    n = int(depth)
    if n < 0:
        raise ValueError("depth must be >= 0")
    return n, str(n)


def catalog(*, kind: str = "3d", visual: bool = False) -> list[dict[str, Any]]:
    """All challenge types (not instances)."""
    if kind == "4d":
        sizes: tuple[int, ...] = (3,)
    else:
        sizes = VISUAL_SIZES if visual else SIZES
    entries = []
    for size in sizes:
        for label in DEPTH_LABELS:
            depth = full_scramble_depth(size, kind) if label == "full" else int(label)
            prefix = "4d" if kind == "4d" else f"n{size}"
            entries.append(
                {
                    "id": f"{prefix}-d{label}",
                    "kind": kind,
                    "size": size,
                    "depth_label": label,
                    "scramble_depth": depth,
                }
            )
    return entries


@dataclass
class Challenge:
    challenge_id: str
    depth_label: str
    task: EvalTask

    def public_dict(self) -> dict[str, Any]:
        data = self.task.to_dict()
        data["challenge_id"] = self.challenge_id
        data["depth_label"] = self.depth_label
        return data


def request_challenge(
    *,
    size: int | None = None,
    depth: int | str | None = None,
    kind: str = "3d",
    seed: int | None = None,
    visual: bool = False,
) -> Challenge:
    """Build one instance. Size, depth, and seed are randomized when omitted."""
    entries = catalog(kind=kind, visual=visual)
    if size is not None:
        entries = [row for row in entries if row["size"] == size]
    if depth is not None:
        label = "full" if depth in ("full", "FULL") else str(int(depth))
        entries = [row for row in entries if row["depth_label"] == label]
    if not entries:
        raise ValueError("no challenge matches size/depth/kind")
    pick = entries[secrets.randbelow(len(entries))]
    instance_seed = secrets.randbelow(2**31) if seed is None else int(seed)
    if pick["kind"] == "4d":
        task = make_hyper_task(pick["scramble_depth"], instance_seed)
    else:
        task = make_task(pick["size"], pick["scramble_depth"], instance_seed)
    return Challenge(
        challenge_id=pick["id"],
        depth_label=pick["depth_label"],
        task=task,
    )
