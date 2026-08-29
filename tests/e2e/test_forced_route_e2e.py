"""Live subprocess FS-017 image-to-route diagnostic."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def test_branched_components_reach_forced_route_png_and_cost(tmp_path: Path) -> None:
    source = tmp_path / "route.png"
    output = tmp_path / "forced.png"
    image = Image.new("L", (72, 40), 0)
    draw = ImageDraw.Draw(image)
    draw.line((6, 12, 30, 12), fill=255, width=5)
    draw.line((18, 4, 18, 21), fill=255, width=5)
    draw.line((45, 30, 65, 30), fill=255, width=5)
    image.save(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.forced_route",
            str(source),
            "--output",
            str(output),
            "--samples",
            "64",
            "--harmonics",
            "12",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "duplicated" in completed.stdout and "bridges" in completed.stdout
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
