from rubix_eval.challenges import (
    SIZES,
    VISUAL_SIZES,
    catalog,
    full_scramble_depth,
    request_challenge,
)


def test_catalog_covers_requested_sizes_and_depths() -> None:
    rows = catalog()
    sizes = {row["size"] for row in rows}
    labels = {row["depth_label"] for row in rows}
    assert sizes == set(SIZES)
    assert labels == {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "full"}
    assert len(rows) == len(SIZES) * 11


def test_visual_pool_excludes_giant_cubes() -> None:
    sizes = {row["size"] for row in catalog(visual=True)}
    assert sizes == set(VISUAL_SIZES)
    assert 40 not in sizes
    assert 100 not in sizes


def test_full_scramble_lengths() -> None:
    assert full_scramble_depth(2) == 11
    assert full_scramble_depth(3) == 25
    assert full_scramble_depth(10) == 160
    assert full_scramble_depth(40) == 480
    assert full_scramble_depth(100) == 1200
    assert full_scramble_depth(3, "4d") == 40


def test_request_randomizes_seed() -> None:
    seeds = {request_challenge(size=2, depth=1).task.seed for _ in range(16)}
    assert len(seeds) > 1


def test_request_randomizes_size_and_depth() -> None:
    picks = {request_challenge(visual=True).challenge_id for _ in range(30)}
    assert len(picks) > 1


def test_public_payload_hides_oracle() -> None:
    challenge = request_challenge(size=2, depth=1)
    public = challenge.public_dict()
    assert "oracle" not in public
    assert public["challenge_id"] == "n2-d1"
    assert public["depth_label"] == "1"
    assert public["size"] == 2


def test_full_label_uses_wca_length() -> None:
    challenge = request_challenge(size=3, depth="full")
    assert challenge.depth_label == "full"
    assert challenge.task.scramble_depth == 25
    assert not challenge.task.cube().is_solved()
