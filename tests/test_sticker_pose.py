import shutil
import subprocess
from pathlib import Path


def test_sticker_planes_face_their_normals() -> None:
    node = shutil.which("node")
    assert node
    script = Path("tests/test_sticker_pose.mjs")
    subprocess.run([node, str(script)], check=True, cwd=Path(__file__).resolve().parents[1])
