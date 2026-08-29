"""Live CLI evidence for the explicit-jump two-circle signal."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("mode", ("strict_trajectory", "pen_up_rendering"))
def test_two_circle_signal_reaches_png_in_both_modes(tmp_path: Path, mode: str) -> None:
    output = tmp_path / f"{mode}.png"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fourier_sketch.cli.discontinuous",
            "--mode",
            mode,
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert f"mode={mode}" in completed.stdout
    assert "samples=128; boundaries=2" in completed.stdout
    with Image.open(output) as rendered:
        assert rendered.width >= 1000
