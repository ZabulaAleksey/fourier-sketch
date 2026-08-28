"""Live local file → CLI → Pillow/application → diagnostic PNG FS-010 path."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

pytestmark = pytest.mark.e2e


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.image", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_local_jpeg_to_binary_png_live_path(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    output = tmp_path / "threshold.png"
    Image.linear_gradient("L").resize((16, 12)).save(source, format="JPEG")

    completed = run_cli(
        str(source),
        "--output",
        str(output),
        "--threshold",
        "120",
        "--autocontrast",
        "--denoise",
        "median_3",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as result:
        assert result.size == (16, 12)
        assert set(result.get_flattened_data()) <= {0, 255}
    assert "JPEG" in completed.stdout
    assert "binary" in completed.stdout


def test_corrupt_input_fails_without_path_or_payload_leak(tmp_path: Path) -> None:
    source = tmp_path / "private-scan.png"
    output = tmp_path / "must-not-exist.png"
    source.write_bytes(b"private payload that is not an image")

    completed = run_cli(str(source), "--output", str(output), "--locale", "pseudo")

    assert completed.returncode == 2
    assert "[!!" in completed.stderr
    assert str(source) not in completed.stderr
    assert "private payload" not in completed.stderr
    assert not output.exists()


def test_existing_destination_requires_explicit_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "existing.png"
    Image.new("L", (2, 2), 255).save(source)
    output.write_bytes(b"original")

    rejected = run_cli(str(source), "--output", str(output))
    accepted = run_cli(str(source), "--output", str(output), "--overwrite")

    assert rejected.returncode == 2
    assert accepted.returncode == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
