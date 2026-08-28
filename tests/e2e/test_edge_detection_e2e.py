"""Live local image -> CLI -> preprocessing -> edge backend -> PNG FS-011 paths."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.edges", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("algorithm", ("threshold_boundary", "canny"))
def test_local_image_to_selected_edge_png_live_path(
    algorithm: str,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / f"{algorithm}.png"
    image = Image.new("L", (24, 20), 0)
    ImageDraw.Draw(image).ellipse((5, 3, 18, 16), fill=255)
    image.save(source)

    completed = run_cli(
        str(source),
        "--output",
        str(output),
        "--algorithm",
        algorithm,
        "--canny-low",
        "50",
        "--canny-high",
        "150",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as result:
        assert result.size == (24, 20)
        assert set(result.get_flattened_data()) <= {0, 255}
    assert algorithm in completed.stdout


def test_corrupt_input_fails_without_path_payload_or_contour_claim(tmp_path: Path) -> None:
    source = tmp_path / "private-scan.png"
    output = tmp_path / "must-not-exist.png"
    source.write_bytes(b"private payload that is not an image")

    completed = run_cli(str(source), "--output", str(output), "--locale", "pseudo")

    assert completed.returncode == 2
    assert "[!!" in completed.stderr
    assert str(source) not in completed.stderr
    assert "private payload" not in completed.stderr
    assert "contour" not in completed.stderr.lower()
    assert not output.exists()
