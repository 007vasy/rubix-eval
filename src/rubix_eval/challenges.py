"""Challenge catalog. Official instances are deterministic; random=True draws a fresh scramble."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

from .puzzles import ND_PUZZLES, ensure_puzzle, find_puzzle
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


def full_scramble_depth(size: int, kind: str = "3d", ndim: int | None = None) -> int:
    """WCA-style 'fully scrambled' length for this cube."""
    d = ndim
    if d is None and kind and kind.endswith("d") and kind[0].isdigit():
        d = int(kind[0])
    if d and d >= 4:
        puzzle = find_puzzle(d, size) or ensure_puzzle(d, size)
        return int(puzzle["full_depth"])
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
    entries = []
    if kind != "3d":
        d = int(kind[0]) if kind[0].isdigit() else 4
        puzzles = [p for p in ND_PUZZLES if p["ndim"] == d]
        if visual:
            puzzles = [p for p in puzzles if p["visual"]]
        for puzzle in puzzles:
            size = int(puzzle["size"])
            for label in DEPTH_LABELS:
                depth = full_scramble_depth(size, kind, d) if label == "full" else int(label)
                prefix = f"{d}d-n{size}" if not (d == 4 and size == 3) else "4d"
                entries.append(
                    {
                        "id": f"{prefix}-d{label}",
                        "kind": f"{d}d",
                        "size": size,
                        "ndim": d,
                        "depth_label": label,
                        "scramble_depth": depth,
                    }
                )
        return entries
    sizes = VISUAL_SIZES if visual else SIZES
    for size in sizes:
        for label in DEPTH_LABELS:
            depth = full_scramble_depth(size, kind) if label == "full" else int(label)
            entries.append(
                {
                    "id": f"n{size}-d{label}",
                    "kind": kind,
                    "size": size,
                    "ndim": 3,
                    "depth_label": label,
                    "scramble_depth": depth,
                }
            )
    return entries


_OFFICIAL: dict[tuple, Challenge] = {}


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


def official_seed(kind: str, size: int, depth_label: str) -> int:
    """Stable seed so the same catalog slot is always the same scramble."""
    raw = f"rubix-eval|{kind}|{size}|{depth_label}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big") % (2**31)


def request_challenge(
    *,
    size: int | None = None,
    depth: int | str | None = None,
    kind: str = "3d",
    seed: int | None = None,
    visual: bool = False,
    random: bool = True,
) -> Challenge:
    """Build one instance. Official (random=False) reuses a stable seed per slot."""
    entries = catalog(kind=kind, visual=visual)
    if size is not None:
        entries = [row for row in entries if row["size"] == size]
    if depth is not None:
        label = "full" if depth in ("full", "FULL") else str(int(depth))
        entries = [row for row in entries if row["depth_label"] == label]
    if not entries:
        raise ValueError("no challenge matches size/depth/kind")
    if random or size is None or depth is None:
        pick = entries[secrets.randbelow(len(entries))]
    else:
        pick = entries[0]
    if seed is not None:
        instance_seed = int(seed)
    elif random:
        instance_seed = secrets.randbelow(2**31)
    else:
        instance_seed = official_seed(pick["kind"], int(pick["size"]), pick["depth_label"])
    cache_key = (pick["kind"], int(pick["size"]), pick["depth_label"], instance_seed)
    cached = _OFFICIAL.get(cache_key)
    if cached is not None and not random:
        return cached
    if pick["kind"] != "3d":
        task = make_hyper_task(
            pick["scramble_depth"],
            instance_seed,
            size=int(pick["size"]),
            ndim=int(pick.get("ndim") or 4),
        )
    else:
        task = make_task(pick["size"], pick["scramble_depth"], instance_seed)
    challenge = Challenge(
        challenge_id=pick["id"],
        depth_label=pick["depth_label"],
        task=task,
    )
    if not random:
        _OFFICIAL[cache_key] = challenge
    return challenge
