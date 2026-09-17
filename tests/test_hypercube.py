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
