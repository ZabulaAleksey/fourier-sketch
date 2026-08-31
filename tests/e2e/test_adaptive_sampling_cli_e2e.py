"""Live subprocess image-to-adaptive comparison evidence for FS-028."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def test_image_contour_reaches_uniform_and_adaptive_timeline_panels(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "adaptive-comparison.png"
    image = Image.new("L", (64, 48), 0)
    ImageDraw.Draw(image).polygon(((8, 40), (30, 6), (36, 30), (56, 8), (54, 42)), fill=255)
    image.save(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.contours",
            str(source),
            "--output",
            str(output),
            "--samples",
            "64",
            "--harmonics",
            "12",
            "--frames",
            "3",
            "--adaptive-curvature-weight",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width > 500
        assert rendered.height > 500
    assert "adaptive-weighted-arc-length-v1" in completed.stdout
    assert "sampled RMSE" in completed.stdout
    assert "4 trace points per panel" in completed.stdout
