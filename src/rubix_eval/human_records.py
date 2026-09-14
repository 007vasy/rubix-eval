"""Human speed records for a fully scrambled cube, by puzzle version.

WCA singles as of 31 August 2026 (https://www.worldcubeassociation.org/results/records).
Unofficial big cubes (8×8+) use the Speedsolving.com unofficial world record list.
4D (3×3×3×3) uses the Hypercubing leaderboard, whose lineage is the MagicCube4D
Hall of Fame (https://superliminal.com/cube/halloffame.htm,
https://github.com/cutelyaware/magiccube4d). Higher-D analog software:
MPUlt by Andrey Astrelin (https://github.com/cutelyaware/MPUlt).
There is no competitive human record for 40³ / 100³.
"""

from __future__ import annotations

from typing import Any

# Seconds. `source` is "wca" or "unofficial".
HUMAN_RECORDS: dict[str, dict[str, Any]] = {
    "2x2x2": {
        "seconds": 0.39,
        "person": "Ziyu Ye (叶梓渝)",
        "event": "Hefei Open 2025",
        "date": "2025-10-25",
        "source": "wca",
        "kind": "single",
    },
    "3x3x3": {
        "seconds": 2.76,
        "person": "Teodor Zajder",
        "event": "GLS Big Cubes Gdańsk 2026",
        "date": "2026-02-08",
        "source": "wca",
        "kind": "single",
    },
    "4x4x4": {
        "seconds": 15.18,
        "person": "Tymon Kolasiński",
        "event": "Spanish Championship 2025",
        "date": "2025-12-06",
        "source": "wca",
        "kind": "single",
    },
    "5x5x5": {
        "seconds": 29.49,
        "person": "Tymon Kolasiński",
        "event": "All Rounders Katowice I 2026",
        "date": "2026-05-01",
        "source": "wca",
        "kind": "single",
    },
    "6x6x6": {
        "seconds": 57.69,
        "person": "Max Park",
        "event": "Burbank Big Cubes 2025",
        "date": "2025-04-26",
        "source": "wca",
        "kind": "single",
    },
    "7x7x7": {
        "seconds": 90.59,
        "person": "Max Park",
        "event": "Rubik's WCA North American Championship 2026",
        "date": "2026-07-02",
        "source": "wca",
        "kind": "single",
    },
    "8x8x8": {
        "seconds": 180.105,
        "person": "ChunPao Ni",
        "event": "Unofficial (Meilong V3M)",
        "date": None,
        "source": "unofficial",
        "kind": "single",
    },
    "9x9x9": {
        "seconds": 276.763,
        "person": "-__Sirius__-",
        "event": "Unofficial (Meilong V3M)",
        "date": None,
        "source": "unofficial",
        "kind": "single",
    },
    "10x10x10": {
        "seconds": 381.714,
        "person": "ap",
        "event": "Unofficial (Meilong V2M)",
        "date": None,
        "source": "unofficial",
        "kind": "single",
    },
    "3x3x3x3": {
        "seconds": 93.52,
        "person": "Andrew Farkas (Hactar)",
        "event": "Hypercubing WR · Hyperspeedcube (MC4D lineage)",
        "date": "2025-09-27",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
        "shortest_twists": 191,
        "shortest_person": "Charles Doan",
        "shortest_date": "2021-11-13",
        "reference": "https://hypercubing.xyz/leaderboards/records/ · https://github.com/cutelyaware/magiccube4d",
    },
    # Bigger 4D — MagicCube4D / Hyperspeedcube (lb.hypercubing.xyz, 2025).
    "2x2x2x2": {
        "seconds": 14.0,
        "person": "Bilal Mourad",
        "event": "Hypercubing WR · Hyperspeedcube",
        "date": "2025-03-21",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
        "reference": "https://hypercubing.xyz/leaderboards/records/",
    },
    "4x4x4x4": {
        "seconds": 437.75,
        "person": "Grant Staten",
        "event": "Hypercubing WR · Hyperspeedcube",
        "date": "2025-10-07",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
        "shortest_twists": 978,
        "shortest_person": "Andrey Astrelin",
        "shortest_date": "2010-06-07",
        "reference": "https://github.com/cutelyaware/magiccube4d",
    },
    "5x5x5x5": {
        "seconds": 1136.19,
        "person": "Grant Staten",
        "event": "Hypercubing WR · Hyperspeedcube",
        "date": "2025-09-29",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
        "shortest_twists": 1981,
        "shortest_person": "Andrey Astrelin",
        "shortest_date": "2010-06-01",
        "reference": "https://github.com/cutelyaware/magiccube4d",
    },
    "6x6x6x6": {
        "seconds": 2394.87,
        "person": "Nenri",
        "event": "Hypercubing WR · Hyperspeedcube",
        "date": "2025-10-03",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
    },
    "7x7x7x7": {
        "seconds": 5125.73,
        "person": "Nenri",
        "event": "Hypercubing WR · Hyperspeedcube",
        "date": "2025-05-31",
        "source": "hypercubing",
        "kind": "single",
        "program": "HSC",
    },
    # 5D–7D — MC5D / MC7D / MPUlt lineage.
    "2x2x2x2x2": {
        "seconds": 246.77,
        "person": "Logan Maciejewski (The Cube Dude)",
        "event": "Hypercubing WR · MC7D",
        "date": "2025-09-11",
        "source": "hypercubing",
        "kind": "single",
        "program": "MC7D",
        "reference": "https://github.com/cutelyaware/MPUlt",
    },
    "3x3x3x3x3": {
        "seconds": 1656.51,
        "person": "Nenri",
        "event": "Hypercubing WR · MC7D",
        "date": "2025-09-19",
        "source": "hypercubing",
        "kind": "single",
        "program": "MC7D",
        "reference": "https://github.com/cutelyaware/MPUlt",
    },
    "4x4x4x4x4": {
        "seconds": 38936.7,
        "person": "Logan Maciejewski (The Cube Dude)",
        "event": "Hypercubing WR · MC7D",
        "date": "2025-04-25",
        "source": "hypercubing",
        "kind": "single",
        "program": "MC7D",
    },
    "3x3x3x3x3x3": {
        "seconds": 39561.59,
        "person": "Logan Maciejewski (The Cube Dude)",
        "event": "Hypercubing WR · MC7D",
        "date": "2025-09-01",
        "source": "hypercubing",
        "kind": "single",
        "program": "MC7D",
        "reference": "https://github.com/cutelyaware/MPUlt",
    },
}


def version_key(kind: str, size: int, ndim: int | None = None) -> str:
    if ndim and ndim >= 4:
        return "x".join([str(size)] * ndim)
    if kind and kind.endswith("d") and kind[0].isdigit():
        d = int(kind[0])
        if d >= 4:
            return "x".join([str(size)] * d)
    if kind == "4d":
        return "x".join([str(size)] * 4)
    return "x".join([str(size)] * 3)


def human_record(kind: str, size: int, ndim: int | None = None) -> dict[str, Any] | None:
    rec = HUMAN_RECORDS.get(version_key(kind, size, ndim))
    return dict(rec) if rec else None
