"""Live subprocess evidence for the FS-016 pen-up diagnostic."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def test_two_components_reach_piecewise_png_without_bridge(tmp_path: Path) -> None:
    source = tmp_path / "separate.png"
    output = tmp_path / "piecewise.png"
    image = Image.new("L", (64, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 8, 25, 8), fill=255, width=5)
    draw.line((38, 23, 58, 23), fill=255, width=5)
    image.save(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.piecewise",
            str(source),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "2 segments" in completed.stdout
    assert "1 pen-up boundaries" in completed.stdout
    with Image.open(output) as rendered:
        assert rendered.width >= 1000


def test_corrupt_input_fails_without_private_path_disclosure(tmp_path: Path) -> None:
    source = tmp_path / "private-corrupt.png"
    output = tmp_path / "piecewise.png"
    source.write_bytes(b"not an image")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.piecewise",
            str(source),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 2
    assert not output.exists()
    assert str(source) not in completed.stderr
    assert "safely decoded" in completed.stderr
