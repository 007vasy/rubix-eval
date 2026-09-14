"""Kociemba two-phase solver for 3×3×3.

Phase 1 reaches the <U,D,L2,R2,F2,B2> subgroup (G1). Phase 2 finishes the cube.
Move tables are derived from the eval engine so notation matches WCA HTM.
"""

from __future__ import annotations

import math
import time
from typing import Any

from .cube import Cube
from .moves import Move, format_moves

# URFDLB facelet indices, row-major on each face.
U, R, F, D, L, B = 0, 9, 18, 27, 36, 45
CORNER_FACELETS = (
    (U + 8, R + 0, F + 2),  # URF
    (U + 6, F + 0, L + 2),  # UFL
    (U + 0, L + 0, B + 2),  # ULB
    (U + 2, B + 0, R + 2),  # UBR
    (D + 2, F + 8, R + 6),  # DFR
    (D + 0, L + 8, F + 6),  # DLF
    (D + 6, B + 8, L + 6),  # DBL
    (D + 8, R + 8, B + 6),  # DRB
)
EDGE_FACELETS = (
    (U + 5, R + 1),  # UR
    (U + 7, F + 1),  # UF
    (U + 3, L + 1),  # UL
    (U + 1, B + 1),  # UB
    (D + 5, R + 7),  # DR
    (D + 1, F + 7),  # DF
    (D + 3, L + 7),  # DL
    (D + 7, B + 7),  # DB
    (F + 5, R + 3),  # FR
    (F + 3, L + 5),  # FL
    (B + 5, L + 3),  # BL
    (B + 3, R + 5),  # BR
)
# Color letter -> face, matching Cube.FACE_COLOR.
_COLOR_FACE = {ord("W"): 0, ord("R"): 1, ord("G"): 2, ord("Y"): 3, ord("O"): 4, ord("B"): 5}
# Face index -> which of U/R/F/D/L/B. Corner id is the bitset of its three faces.
_CORNER_ID = {
    frozenset((0, 1, 2)): 0,  # URF
    frozenset((0, 2, 4)): 1,  # UFL
    frozenset((0, 4, 5)): 2,  # ULB
    frozenset((0, 5, 1)): 3,  # UBR
    frozenset((3, 2, 1)): 4,  # DFR
    frozenset((3, 4, 2)): 5,  # DLF
    frozenset((3, 5, 4)): 6,  # DBL
    frozenset((3, 1, 5)): 7,  # DRB
}
_EDGE_ID = {
    frozenset((0, 1)): 0,  # UR
    frozenset((0, 2)): 1,  # UF
    frozenset((0, 4)): 2,  # UL
    frozenset((0, 5)): 3,  # UB
    frozenset((3, 1)): 4,  # DR
    frozenset((3, 2)): 5,  # DF
    frozenset((3, 4)): 6,  # DL
    frozenset((3, 5)): 7,  # DB
    frozenset((2, 1)): 8,  # FR
    frozenset((2, 4)): 9,  # FL
    frozenset((5, 4)): 10,  # BL
    frozenset((5, 1)): 11,  # BR
}

MOVES_18 = [Move(face, 1, False, turns) for face in "URFDLB" for turns in (1, 2, 3)]
# Phase 2 generators: U, D, and 180° on the side faces.
PHASE2 = (0, 1, 2, 9, 10, 11, 4, 13, 7, 16)


def _facelets(cube: Cube) -> bytes:
    return "".join("".join("".join(row) for row in cube.face_grid(face)) for face in "URFDLB").encode(
        "ascii"
    )


def _cubies(facelets: bytes) -> tuple[list[int], list[int], list[int], list[int]]:
    cperm = [0] * 8
    cori = [0] * 8
    for slot, idxs in enumerate(CORNER_FACELETS):
        cols = [facelets[i] for i in idxs]
        faces = [_COLOR_FACE[c] for c in cols]
        cperm[slot] = _CORNER_ID[frozenset(faces)]
        ori = 0
        while faces[ori] not in (0, 3) and ori < 2:
            ori += 1
        cori[slot] = ori
    eperm = [0] * 12
    eori = [0] * 12
    for slot, idxs in enumerate(EDGE_FACELETS):
        cols = [facelets[i] for i in idxs]
        faces = [_COLOR_FACE[c] for c in cols]
        eperm[slot] = _EDGE_ID[frozenset(faces)]
        # 0 if the U/D (or F/B for E-slice cubies) colour sits on the first facelet
        # of the cubie's home slot. Equivalent: first colour's face is U/D when the
        # cubie owns a U/D colour, else F/B.
        cubie = eperm[slot]
        if cubie <= 7:
            eori[slot] = 0 if faces[0] in (0, 3) else 1
        else:
            eori[slot] = 0 if faces[0] in (2, 5) else 1
    return cperm, cori, eperm, eori


def _pack_twist(cori: list[int]) -> int:
    n = 0
    for i in range(7):
        n = 3 * n + cori[i]
    return n


def _pack_flip(eori: list[int]) -> int:
    n = 0
    for i in range(11):
        n = 2 * n + eori[i]
    return n


def _lex_rank_comb(items: list[int], n: int = 12, k: int = 4) -> int:
    rank = 0
    prev = -1
    for i, x in enumerate(items):
        for j in range(prev + 1, x):
            rank += math.comb(n - 1 - j, k - 1 - i)
        prev = x
    return rank


def _unrank_comb(rank: int, n: int = 12, k: int = 4) -> list[int]:
    items: list[int] = []
    x = 0
    for remaining in range(k, 0, -1):
        while True:
            comb = math.comb(n - 1 - x, remaining - 1)
            if rank < comb:
                items.append(x)
                x += 1
                break
            rank -= comb
            x += 1
    return items


def _pack_slice(eperm: list[int]) -> int:
    """0 when the four E-slice cubies sit in slots 8–11 (G1)."""
    occupied = [i for i in range(12) if eperm[i] >= 8]
    return 494 - _lex_rank_comb(occupied)


def _pack_cperm(cperm: list[int]) -> int:
    n = 0
    for i in range(8):
        left = 0
        for j in range(i + 1, 8):
            if cperm[j] < cperm[i]:
                left += 1
        n += left * math.factorial(7 - i)
    return n


def _pack_edge4(eperm: list[int]) -> int:
    """Permutation of the four E-slice edges in slots 8–11."""
    seq = [eperm[i] - 8 for i in range(8, 12)]
    n = 0
    for i in range(4):
        left = 0
        for j in range(i + 1, 4):
            if seq[j] < seq[i]:
                left += 1
        n += left * math.factorial(3 - i)
    return n


def _pack_edge8(eperm: list[int]) -> int:
    seq = [eperm[i] for i in range(8)]
    n = 0
    for i in range(8):
        left = 0
        for j in range(i + 1, 8):
            if seq[j] < seq[i]:
                left += 1
        n += left * math.factorial(7 - i)
    return n


class _Move:
    __slots__ = ("cp", "co", "ep", "eo")

    def __init__(self, cp: list[int], co: list[int], ep: list[int], eo: list[int]) -> None:
        self.cp = cp
        self.co = co
        self.ep = ep
        self.eo = eo


def _build_moves() -> list[_Move]:
    out: list[_Move] = []
    for move in MOVES_18:
        cube = Cube(3)
        cube.apply([move])
        cperm, cori, eperm, eori = _cubies(_facelets(cube))
        out.append(_Move(cperm, cori, eperm, eori))
    return out


def _apply_move(cperm, cori, eperm, eori, mv: _Move) -> tuple[list[int], list[int], list[int], list[int]]:
    ncp = [cperm[i] for i in mv.cp]
    nco = [(cori[i] + mv.co[slot]) % 3 for slot, i in enumerate(mv.cp)]
    nep = [eperm[i] for i in mv.ep]
    neo = [(eori[i] + mv.eo[slot]) % 2 for slot, i in enumerate(mv.ep)]
    return ncp, nco, nep, neo


def _bfs_pruning(n_states: int, apply_coord, move_ids: tuple[int, ...]) -> list[int]:
    dist = [-1] * n_states
    dist[0] = 0
    queue = [0]
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        d = dist[cur] + 1
        for mi in move_ids:
            nxt = apply_coord(cur, mi)
            if dist[nxt] == -1:
                dist[nxt] = d
                queue.append(nxt)
    return dist


class TwoPhase:
    def __init__(self) -> None:
        self.moves = _build_moves()
        self.twist_move = [[0] * 18 for _ in range(2187)]
        self.flip_move = [[0] * 18 for _ in range(2048)]
        self.slice_move = [[0] * 18 for _ in range(495)]
        self.cperm_move = [[0] * 18 for _ in range(40320)]
        self.edge4_move = [[0] * 18 for _ in range(24)]
        self.edge8_move = [[0] * 18 for _ in range(40320)]
        self._fill_coord_tables()
        ids18 = tuple(range(18))
        self.twist_prun = _bfs_pruning(2187, lambda c, m: self.twist_move[c][m], ids18)
        self.flip_prun = _bfs_pruning(2048, lambda c, m: self.flip_move[c][m], ids18)
        self.slice_prun = _bfs_pruning(495, lambda c, m: self.slice_move[c][m], ids18)
        self.cperm_prun = _bfs_pruning(40320, lambda c, m: self.cperm_move[c][m], PHASE2)
        self.edge4_prun = _bfs_pruning(24, lambda c, m: self.edge4_move[c][m], PHASE2)
        self.edge8_prun = _bfs_pruning(40320, lambda c, m: self.edge8_move[c][m], PHASE2)

    def _fill_coord_tables(self) -> None:
        # Twist / flip / slice from each start coord via cubie apply is slow if we
        # unpack naively 2187*18 times through Cube. Instead walk the cubie arrays
        # of a representative for each coordinate by applying identity cubies then
        # the 18 moves — still too many Cube calls. We apply _Move to packed
        # representatives built once per coordinate... that's 2187 Cube-free applies.
        #
        # Represent a coord as cubies on an otherwise-solved cube.
        identity_cp = list(range(8))
        identity_co = [0] * 8
        identity_ep = list(range(12))
        identity_eo = [0] * 12

        def twist_to_co(t: int) -> list[int]:
            co = [0] * 8
            total = 0
            for i in range(6, -1, -1):
                co[i] = t % 3
                total += co[i]
                t //= 3
            co[7] = (-total) % 3
            return co

        def flip_to_eo(f: int) -> list[int]:
            eo = [0] * 12
            total = 0
            for i in range(10, -1, -1):
                eo[i] = f % 2
                total += eo[i]
                f //= 2
            eo[11] = total % 2
            return eo

        def slice_to_ep(s: int) -> list[int]:
            """Place four slice cubies (8-11) so `_pack_slice` recovers `s`."""
            slots = _unrank_comb(494 - s)
            ep = [-1] * 12
            for i, slot in enumerate(slots):
                ep[slot] = 8 + i
            others = [x for x in range(8)]
            for i in range(12):
                if ep[i] == -1:
                    ep[i] = others.pop(0)
            return ep

        def perm_from_lehmer(n: int, size: int) -> list[int]:
            items = list(range(size))
            out = []
            for i in range(size):
                f = math.factorial(size - 1 - i)
                idx = n // f
                n %= f
                out.append(items.pop(idx))
            return out

        for t in range(2187):
            co = twist_to_co(t)
            for mi, mv in enumerate(self.moves):
                _, nco, _, _ = _apply_move(identity_cp, co, identity_ep, identity_eo, mv)
                self.twist_move[t][mi] = _pack_twist(nco)
        for f in range(2048):
            eo = flip_to_eo(f)
            for mi, mv in enumerate(self.moves):
                _, _, _, neo = _apply_move(identity_cp, identity_co, identity_ep, eo, mv)
                self.flip_move[f][mi] = _pack_flip(neo)
        for s in range(495):
            ep = slice_to_ep(s)
            for mi, mv in enumerate(self.moves):
                _, _, nep, _ = _apply_move(identity_cp, identity_co, ep, identity_eo, mv)
                self.slice_move[s][mi] = _pack_slice(nep)
        for p in range(40320):
            cp = perm_from_lehmer(p, 8)
            for mi, mv in enumerate(self.moves):
                ncp, _, _, _ = _apply_move(cp, identity_co, identity_ep, identity_eo, mv)
                self.cperm_move[p][mi] = _pack_cperm(ncp)
        for p in range(24):
            e4 = perm_from_lehmer(p, 4)
            ep = list(range(8)) + [x + 8 for x in e4]
            for mi, mv in enumerate(self.moves):
                _, _, nep, _ = _apply_move(identity_cp, identity_co, ep, identity_eo, mv)
                self.edge4_move[p][mi] = _pack_edge4(nep)
        for p in range(40320):
            e8 = perm_from_lehmer(p, 8)
            ep = e8 + [8, 9, 10, 11]
            for mi, mv in enumerate(self.moves):
                _, _, nep, _ = _apply_move(identity_cp, identity_co, ep, identity_eo, mv)
                self.edge8_move[p][mi] = _pack_edge8(nep)


_SOLVER: TwoPhase | None = None


def _solver() -> TwoPhase:
    global _SOLVER
    if _SOLVER is None:
        _SOLVER = TwoPhase()
    return _SOLVER


def _ida(
    *,
    start: tuple[int, ...],
    apply,
    h,
    move_ids: tuple[int, ...],
    faces: tuple[str, ...],
    max_depth: int,
    deadline: float,
) -> list[int] | None:
    path: list[int] = []

    def search(state: tuple[int, ...], depth: int, last_face: str) -> bool:
        if time.perf_counter() > deadline:
            return False
        if h(state) == 0:
            return True
        if depth == 0 or h(state) > depth:
            return False
        for mi in move_ids:
            face = faces[mi]
            if face == last_face:
                continue
            nxt = apply(state, mi)
            path.append(mi)
            if search(nxt, depth - 1, face):
                return True
            path.pop()
        return False

    bound = h(start)
    for depth in range(bound, max_depth + 1):
        if time.perf_counter() > deadline:
            return None
        path.clear()
        if search(start, depth, ""):
            return list(path)
    return None


def solve_kociemba(cube: Cube, *, time_limit: float = 1.5) -> dict[str, Any]:
    if time_limit <= 0:
        return {
            "algorithm": "kociemba",
            "label": "Kociemba two-phase",
            "solved": False,
            "moves": [],
            "text": "",
            "htm": None,
            "optimal": False,
            "elapsed_sec": 0.0,
            "error": "search skipped",
        }
    if cube.size != 3:
        return {
            "algorithm": "kociemba",
            "label": "Kociemba two-phase",
            "solved": False,
            "moves": [],
            "text": "",
            "htm": None,
            "optimal": False,
            "elapsed_sec": 0.0,
            "error": "3×3×3 only",
        }
    cperm, cori, eperm, eori = _cubies(_facelets(cube))
    twist = _pack_twist(cori)
    flip = _pack_flip(eori)
    slc = _pack_slice(eperm)
    engine = _solver()
    t0 = time.perf_counter()
    deadline = t0 + time_limit
    faces = tuple(m.face for m in MOVES_18)

    def apply1(state, mi):
        t, f, s = state
        return (engine.twist_move[t][mi], engine.flip_move[f][mi], engine.slice_move[s][mi])

    def h1(state):
        t, f, s = state
        return max(engine.twist_prun[t], engine.flip_prun[f], engine.slice_prun[s])

    def apply2(state, mi):
        cp, e8, e4 = state
        return (engine.cperm_move[cp][mi], engine.edge8_move[e8][mi], engine.edge4_move[e4][mi])

    def h2(state):
        cp, e8, e4 = state
        return max(engine.cperm_prun[cp], engine.edge8_prun[e8], engine.edge4_prun[e4])

    start1 = (twist, flip, slc)
    p1 = _ida(
        start=start1,
        apply=apply1,
        h=h1,
        move_ids=tuple(range(18)),
        faces=faces,
        max_depth=12,
        deadline=deadline,
    )
    if p1 is None:
        elapsed = time.perf_counter() - t0
        return {
            "algorithm": "kociemba",
            "label": "Kociemba two-phase",
            "solved": False,
            "moves": [],
            "text": "",
            "htm": None,
            "optimal": False,
            "elapsed_sec": round(elapsed, 6),
            "error": "phase 1 timeout",
        }

    def run_phase2(phase1: list[int]) -> list[int] | None:
        cp_l, co_l, ep_l, eo_l = list(cperm), list(cori), list(eperm), list(eori)
        for mi in phase1:
            cp_l, co_l, ep_l, eo_l = _apply_move(cp_l, co_l, ep_l, eo_l, engine.moves[mi])
        start2 = (_pack_cperm(cp_l), _pack_edge8(ep_l), _pack_edge4(ep_l))
        last = faces[phase1[-1]] if phase1 else ""
        path: list[int] = []

        def search(state: tuple[int, int, int], depth: int, last_face: str) -> bool:
            if time.perf_counter() > deadline:
                return False
            if h2(state) == 0:
                return True
            if depth == 0 or h2(state) > depth:
                return False
            for mi in PHASE2:
                face = faces[mi]
                if face == last_face:
                    continue
                nxt = apply2(state, mi)
                path.append(mi)
                if search(nxt, depth - 1, face):
                    return True
                path.pop()
            return False

        bound = h2(start2)
        for depth in range(bound, 19):
            if time.perf_counter() > deadline:
                return None
            path.clear()
            if search(start2, depth, last):
                return list(path)
        return None

    p2 = run_phase2(p1)
    elapsed = time.perf_counter() - t0
    if p2 is None:
        return {
            "algorithm": "kociemba",
            "label": "Kociemba two-phase",
            "solved": False,
            "moves": [],
            "text": "",
            "htm": None,
            "optimal": False,
            "elapsed_sec": round(elapsed, 6),
            "error": "phase 2 timeout",
        }
    ids = p1 + p2
    moves = [MOVES_18[i] for i in ids]
    work = cube.copy()
    work.apply(moves)
    solved = work.is_solved()
    return {
        "algorithm": "kociemba",
        "label": "Kociemba two-phase",
        "solved": solved,
        "moves": moves,
        "text": format_moves(moves),
        "htm": len(moves),
        "optimal": False,
        "elapsed_sec": round(elapsed, 6),
        "error": None if solved else "two-phase did not solve",
        "phase1_len": len(p1),
        "phase2_len": len(p2),
    }
