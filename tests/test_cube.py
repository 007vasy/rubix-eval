from __future__ import annotations

import pytest

from rubix_eval.cube import Cube
from rubix_eval.moves import format_moves, invert_moves, parse_moves
from rubix_eval.scramble import generate_scramble


@pytest.mark.parametrize("size", [2, 3, 4, 5, 7])
def test_new_cube_is_solved(size: int) -> None:
    assert Cube(size).is_solved()


def test_r_four_times_identity() -> None:
    cube = Cube(3)
    cube.apply("R R R R")
    assert cube.is_solved()


def test_r_then_prime_identity() -> None:
    cube = Cube(3)
    cube.apply("R R'")
    assert cube.is_solved()


def test_sexy_move_six_times() -> None:
    cube = Cube(3)
    cube.apply("R U R' U'" * 6)
    assert cube.is_solved()


def test_sune_six_times() -> None:
    cube = Cube(3)
    cube.apply("R U R' U R U2 R'" * 6)
    assert cube.is_solved()


def test_t_perm_twice() -> None:
    cube = Cube(3)
    t_perm = "R U R' U' R' F R2 U' R' U' R U R' F'"
    cube.apply(t_perm)
    assert not cube.is_solved()
    cube.apply(t_perm)
    assert cube.is_solved()


def test_r_sends_front_right_to_up() -> None:
    cube = Cube(3)
    cube.apply("R")
    # WCA R: F-right stickers move to U-right.
    assert [row[2] for row in cube.face_grid("U")] == ["G", "G", "G"]
    assert [row[2] for row in cube.face_grid("F")] == ["Y", "Y", "Y"]


def test_u_sends_right_top_to_front() -> None:
    cube = Cube(3)
    cube.apply("U")
    assert cube.face_grid("F")[0] == ["R", "R", "R"]
    assert cube.face_grid("R")[0] == ["B", "B", "B"]


def test_inverse_scramble_solves_any_size() -> None:
    for size in (2, 3, 4, 5):
        for depth in (1, 5, 12):
            cube = Cube(size)
            scramble = generate_scramble(size, depth, seed=size * 100 + depth)
            cube.apply(scramble)
            assert not cube.is_solved() or depth == 0
            cube.apply(invert_moves(scramble))
            assert cube.is_solved(), f"failed size={size} depth={depth}"


def test_wide_rw_on_4x4() -> None:
    cube = Cube(4)
    cube.apply("Rw")
    assert not cube.is_solved()
    cube.apply("Rw'")
    assert cube.is_solved()


def test_inner_slice_2r() -> None:
    cube = Cube(4)
    cube.apply("2R")
    assert not cube.is_solved()
    cube.apply("2R'")
    assert cube.is_solved()


def test_state_roundtrip() -> None:
    cube = Cube(5)
    cube.apply(generate_scramble(5, 9, seed=3))
    restored = Cube.from_dict(cube.to_dict())
    assert restored == cube
    assert restored.facelet_string() == cube.facelet_string()


def test_copy_is_independent() -> None:
    cube = Cube(3)
    clone = cube.copy()
    cube.apply("R")
    assert clone.is_solved()
    assert not cube.is_solved()


def test_parse_concatenated() -> None:
    moves = parse_moves("RUR'U'")
    assert [m.notation() for m in moves] == ["R", "U", "R'", "U'"]


def test_seed_is_stable() -> None:
    assert format_moves(generate_scramble(3, 8, seed=1)) == "U F2 L2 D' F2 L U2 L2"


def test_2x2_faces_only() -> None:
    cube = Cube(2)
    cube.apply("R U R' U' F' U F")
    cube.apply(invert_moves(parse_moves("R U R' U' F' U F")))
    assert cube.is_solved()
