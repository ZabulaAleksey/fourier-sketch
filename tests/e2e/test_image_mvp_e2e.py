"""Live subprocess evidence for the complete FS-013 image MVP."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.image_mvp", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_user_selected_image_reaches_four_panel_endpoint_trace(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "image-mvp.png"
    image = Image.new("L", (48, 32), 0)
    ImageDraw.Draw(image).ellipse((10, 5, 37, 26), fill=255)
    image.save(source)

    completed = _run_cli(
        str(source),
        "--headless",
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
        assert rendered.width >= 1000
        assert rendered.height >= 800
    assert "64 samples" in completed.stdout
    assert "12 harmonics" in completed.stdout
    assert "6 trace points" in completed.stdout


def test_no_contour_writes_explicit_recovery_view(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    output = tmp_path / "recovery.png"
    Image.new("L", (16, 12), 0).save(source)

    completed = _run_cli(
        str(source),
        "--headless",
        "--output",
        str(output),
        "--locale",
        "pseudo",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "[!!" in completed.stdout


def test_corrupt_input_fails_without_output_or_private_path(tmp_path: Path) -> None:
    source = tmp_path / "private-corrupt.png"
    output = tmp_path / "must-not-exist.png"
    source.write_bytes(b"not an image")

    completed = _run_cli(str(source), "--headless", "--output", str(output))

    assert completed.returncode == 2
    assert not output.exists()
    assert str(source) not in completed.stderr
    assert "safely decoded" in completed.stderr


def test_existing_output_is_preserved_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "existing.png"
    image = Image.new("L", (24, 20), 0)
    ImageDraw.Draw(image).rectangle((5, 4, 18, 15), fill=255)
    image.save(source)
    output.write_bytes(b"user-owned")

    completed = _run_cli(
        str(source),
        "--headless",
        "--output",
        str(output),
        "--frames",
        "1",
    )

    assert completed.returncode == 2
    assert output.read_bytes() == b"user-owned"
    assert "already exists" in completed.stderr


def test_unc_input_is_rejected_before_network_filesystem_access() -> None:
    source = r"\\server\share\private.png"

    completed = _run_cli(source, "--headless")

    assert completed.returncode == 2
    assert source not in completed.stderr
    assert "path forms are rejected" in completed.stderr


def test_output_line_separator_is_escaped_in_success_summary(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "trace\u2028spoof.png"
    image = Image.new("L", (24, 20), 0)
    ImageDraw.Draw(image).rectangle((5, 4, 18, 15), fill=255)
    image.save(source)

    completed = _run_cli(
        str(source),
        "--headless",
        "--output",
        str(output),
        "--frames",
        "1",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.exists()
    assert "\u2028" not in completed.stdout
    assert "\\u2028" in completed.stdout
