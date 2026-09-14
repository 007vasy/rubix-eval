from rubix_eval.human_records import human_record, version_key
from rubix_eval.hypercube import HyperCube
from rubix_eval.puzzles import ND_PUZZLES, nd_key
from rubix_eval.task import make_hyper_task


def test_2_to_the_4_roundtrip() -> None:
    cube = HyperCube(size=2, ndim=4)
    assert cube.ndim == 4
    assert cube.size == 2
    cube.apply("RU")
    assert not cube.is_solved()
    cube.apply("RU'")
    assert cube.is_solved()


def test_4_to_the_4_inner_slice() -> None:
    task = make_hyper_task(5, seed=1, size=4, ndim=4)
    cube = task.cube()
    assert cube.size == 4
    cube.apply(task.oracle_solution())
    assert cube.is_solved()


def test_3_to_the_5_exists() -> None:
    cube = HyperCube(size=3, ndim=5)
    assert len(cube._cells) == 10
    assert cube.is_solved()
    task = make_hyper_task(3, seed=2, size=3, ndim=5)
    work = task.cube()
    work.apply(task.oracle_solution())
    assert work.is_solved()


def test_human_records_cover_nd() -> None:
    assert version_key("4d", 4) == "4x4x4x4"
    assert human_record("4d", 2)["seconds"] == 14.0
    assert human_record("4d", 4)["person"].startswith("Grant")
    assert human_record("5d", 3)["seconds"] == 1656.51
    assert nd_key(4, 7) in {nd_key(p["ndim"], p["size"]) for p in ND_PUZZLES}
