"""Live explicit-jump analysis export."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

pytestmark = pytest.mark.e2e


def test_explicit_jump_reaches_measured_chart(tmp_path: Path) -> None:
    output = tmp_path / "analysis.png"
    completed = subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.spectrum_analysis", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "measured_only=true" in completed.stdout
    assert "comparison=discontinuous_vs_continuous" in completed.stdout
    with Image.open(output) as rendered:
        assert rendered.width >= 1500
