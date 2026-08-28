"""In-process localized FS-012 contour CLI contracts."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.cli.contours import main

pytestmark = pytest.mark.component


@pytest.mark.parametrize("algorithm", ("threshold_boundary", "canny"))
def test_cli_component_renders_selected_contour_timeline(
    algorithm: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / f"{algorithm}.png"
    image = Image.new("L", (32, 24), 0)
    ImageDraw.Draw(image).rectangle((7, 5, 24, 18), fill=255)
    image.save(source)

    code = main(
        [
            str(source),
            "--output",
            str(output),
            "--algorithm",
            algorithm,
            "--samples",
            "32",
            "--harmonics",
            "8",
            "--frames",
            "3",
            "--canny-low",
            "40",
            "--canny-high",
            "120",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert algorithm in captured.out
    assert "32 samples" in captured.out
    assert "4 trace points" in captured.out


def test_cli_component_reports_valid_empty_result_without_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "blank.png"
    output = tmp_path / "must-not-exist.png"
    Image.new("L", (8, 8), 0).save(source)

    code = main([str(source), "--output", str(output)])

    captured = capsys.readouterr()
    assert code == 0
    assert "No usable contour" in captured.out
    assert "No curve or trace was created" in captured.out
    assert not output.exists()


def test_cli_component_localizes_invalid_timeline_parameters(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "private-shape.png"
    Image.new("L", (8, 8), 255).save(source)

    code = main([str(source), "--frames", "0", "--locale", "pseudo"])

    captured = capsys.readouterr()
    assert code == 2
    assert "[!!" in captured.err
    assert str(source) not in captured.err
    assert "frames must" not in captured.err


def test_inactive_canny_options_do_not_block_boundary_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "trace.png"
    image = Image.new("L", (12, 12), 0)
    ImageDraw.Draw(image).rectangle((2, 2, 9, 9), fill=255)
    image.save(source)

    code = main(
        [
            str(source),
            "--output",
            str(output),
            "--frames",
            "1",
            "--canny-low",
            "255",
            "--canny-high",
            "0",
        ]
    )

    assert code == 0, capsys.readouterr().err
    assert output.exists()


def test_cli_component_preserves_existing_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "existing.png"
    image = Image.new("L", (12, 12), 0)
    ImageDraw.Draw(image).rectangle((2, 2, 9, 9), fill=255)
    image.save(source)
    output.write_bytes(b"user-owned")

    code = main([str(source), "--output", str(output), "--frames", "1"])

    captured = capsys.readouterr()
    assert code == 2
    assert output.read_bytes() == b"user-owned"
    assert "already exists" in captured.err
