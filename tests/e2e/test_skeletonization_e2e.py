"""Live subprocess evidence for the complete FS-014 skeleton diagnostic."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.e2e


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fourier_sketch.cli.skeleton", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _shape(path: Path) -> None:
    image = Image.new("L", (48, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((8, 16, 39, 16), fill=255, width=7)
    draw.line((24, 5, 24, 27), fill=255, width=7)
    image.save(path)


def test_local_image_reaches_real_skeleton_export(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "skeleton.png"
    _shape(source)

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    with Image.open(output) as rendered:
        assert rendered.size == (48, 32)
        assert set(rendered.convert("L").tobytes()) <= {0, 255}
    assert "lee" in completed.stdout
    assert "scikit-image/0.26." in completed.stdout


def test_local_image_reaches_two_panel_preview(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "preview.png"
    _shape(source)

    completed = _run_cli(
        str(source),
        "--mode",
        "preview",
        "--output",
        str(output),
        "--locale",
        "pseudo",
    )

    assert completed.returncode == 0, completed.stderr
    with Image.open(output) as rendered:
        assert rendered.width >= 1000
        assert rendered.height >= 500
    assert "[!!" in completed.stdout


def test_empty_input_exports_valid_empty_skeleton(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    output = tmp_path / "empty-skeleton.png"
    Image.new("L", (16, 12), 0).save(source)

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    with Image.open(output) as rendered:
        assert rendered.size == (16, 12)
        assert rendered.convert("L").getbbox() is None
    assert "0 source pixels -> 0 skeleton pixels" in completed.stdout


def test_corrupt_input_fails_without_output_or_private_path(tmp_path: Path) -> None:
    source = tmp_path / "private-corrupt.png"
    output = tmp_path / "must-not-exist.png"
    source.write_bytes(b"not an image")

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 2
    assert not output.exists()
    assert str(source) not in completed.stderr
    assert "safely decoded" in completed.stderr


def test_existing_output_is_preserved_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "existing.png"
    _shape(source)
    output.write_bytes(b"user-owned")

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 2
    assert output.read_bytes() == b"user-owned"
    assert "already exists" in completed.stderr


def test_output_line_separator_is_escaped_in_success_summary(tmp_path: Path) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "skeleton\u2028spoof.png"
    _shape(source)

    completed = _run_cli(str(source), "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    assert output.exists()
    assert "\u2028" not in completed.stdout
    assert "\\u2028" in completed.stdout
