"""Live subprocess image-to-dominant-contour endpoint-trace evidence."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.contours", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_local_shape_reaches_actual_endpoint_trace_png(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "contour-trace.png"
    image = Image.new("L", (48, 32), 0)
    ImageDraw.Draw(image).ellipse((10, 5, 37, 26), fill=255)
    image.save(source)

    completed = run_cli(
        str(source),
        "--output",
        str(output),
        "--samples",
        "64",
        "--harmonics",
        "12",
        "--frames",
        "5",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width > 100
        assert rendered.height > 100
    assert "opencv/" in completed.stdout
    assert "64 samples" in completed.stdout
    assert "6 trace points" in completed.stdout


def test_blank_image_is_explicit_empty_live_result(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    output = tmp_path / "must-not-exist.png"
    Image.new("L", (16, 12), 0).save(source)

    completed = run_cli(str(source), "--output", str(output), "--locale", "pseudo")

    assert completed.returncode == 0, completed.stderr
    assert "[!!" in completed.stdout
    assert "opencv/" in completed.stdout
    assert not output.exists()
