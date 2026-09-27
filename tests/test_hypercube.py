from __future__ import annotations

from rubix_eval.hyper_moves import format_hyper_moves, invert_hyper_moves, parse_hyper_moves
from rubix_eval.hypercube import CELL_COLOR, CELLS, HyperCube
from rubix_eval.scramble import generate_hyper_scramble


def test_new_hypercube_is_solved() -> None:
    cube = HyperCube()
    assert cube.is_solved()
    assert cube.piece_counts() == {1: 8, 2: 24, 3: 32, 4: 16}


def test_ru_four_times_identity() -> None:
    cube = HyperCube()
    cube.apply("RU RU RU RU")
    assert cube.is_solved()


def test_ru_then_prime() -> None:
    cube = HyperCube()
    cube.apply("RU RU'")
    assert cube.is_solved()


def test_ru2_twice() -> None:
    cube = HyperCube()
    cube.apply("RU2 RU2")
    assert cube.is_solved()


def test_ru_scrambles() -> None:
    cube = HyperCube()
    cube.apply("RU")
    assert not cube.is_solved()
    assert cube.misplaced_stickers() > 0


def test_solved_allows_whole_puzzle_reorientation() -> None:
    cube = HyperCube()
    swap = {"R": "O", "O": "R", "W": "Y", "Y": "W"}
    cube._cubies = {
        pos: {cell: swap.get(color, color) for cell, color in colors.items()}
        for pos, colors in cube._cubies.items()
    }
    assert cube.is_solved()
    assert cube.misplaced_stickers() == 0


def test_parse_hyper_notation() -> None:
    moves = parse_hyper_moves("RU IF' OL2")
    assert [m.notation() for m in moves] == ["RU", "IF'", "OL2"]


def test_inverse_scramble_solves() -> None:
    for depth in (1, 4, 8, 16):
        cube = HyperCube()
        scramble = generate_hyper_scramble(depth, seed=depth * 11)
        cube.apply(scramble)
        if depth:
            assert not cube.is_solved()
        cube.apply(invert_hyper_moves(scramble))
        assert cube.is_solved(), f"failed depth={depth}"


def test_centers_stay_put() -> None:
    cube = HyperCube()
    cube.apply("RU IF BD LO")
    for cell in CELLS:
        # 1c center of each cell is the middle cubie of that cell.
        stickers = cube.cell_stickers(cell)
        assert stickers[1][1][1] == CELL_COLOR[cell]


def test_state_roundtrip() -> None:
    cube = HyperCube()
    cube.apply(generate_hyper_scramble(9, seed=4))
    restored = HyperCube.from_dict(cube.to_dict())
    assert restored == cube


def test_seed_stable() -> None:
    text = format_hyper_moves(generate_hyper_scramble(8, seed=1))
    assert text == format_hyper_moves(generate_hyper_scramble(8, seed=1))
    assert parse_hyper_moves(text)


def test_scramble_uses_every_layer_and_axis() -> None:
    """Regression: low-bit LCG picks locked a 3^4 scramble to one layer and half the axes."""
    from collections import Counter

    from rubix_eval.challenges import full_scramble_depth, official_seed

    depth = full_scramble_depth(3, "4d", 4)
    moves = generate_hyper_scramble(depth, official_seed("4d", 3, "full"), size=3, ndim=4)
    layers = Counter(m.layer for m in moves)
    assert set(layers) == {None, 2} and min(layers.values()) > depth // 4
    per_cell_axes = {}
    for m in moves:
        per_cell_axes.setdefault(m.cell, set()).add(m.axis)
    assert len(per_cell_axes) == 8
    assert all(len(axes) >= 5 for axes in per_cell_axes.values())
    for seed in range(1, 30):
        assert len({m.layer for m in generate_hyper_scramble(40, seed, size=3, ndim=4)}) == 2


def test_full_3x3x3x3_scramble_mixes_every_cell() -> None:
    from rubix_eval.challenges import full_scramble_depth, official_seed

    cube = HyperCube(size=3, ndim=4)
    cube.apply(generate_hyper_scramble(full_scramble_depth(3, "4d", 4), official_seed("4d", 3, "full"), size=3, ndim=4))
    assert all(len(set(cube.cell_stickers_flat(cell))) == 8 for cell in cube._cells)
