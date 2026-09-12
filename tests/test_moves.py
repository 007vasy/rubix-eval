from rubix_eval.moves import format_moves, invert_moves, parse_moves


def test_roundtrip_notation() -> None:
    text = "R U R' U' Rw 2R 3Uw2"
    parsed = parse_moves(text)
    assert format_moves(parsed) == "R U R' U' Rw 2R 3Uw2"


def test_invert() -> None:
    moves = parse_moves("R U2 F'")
    assert format_moves(invert_moves(moves)) == "F U2 R'"


def test_lowercase_wide() -> None:
    assert parse_moves("r")[0].wide is True
    assert parse_moves("r")[0].layer == 2
