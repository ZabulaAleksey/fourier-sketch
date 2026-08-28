"""In-process localized FS-011 edge CLI contracts."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.cli.edges import main

pytestmark = pytest.mark.component


@pytest.mark.parametrize("algorithm", ("threshold_boundary", "canny"))
def test_cli_component_exports_selected_algorithm(
    algorithm: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / f"{algorithm}.png"
    image = Image.new("L", (16, 12), 0)
    ImageDraw.Draw(image).rectangle((4, 3, 11, 8), fill=255)
    image.save(source)

    code = main([str(source), "--output", str(output), "--algorithm", algorithm])

    captured = capsys.readouterr()
    assert code == 0
    assert output.exists()
    assert algorithm in captured.out
    assert "16x12" in captured.out


def test_cli_component_localizes_invalid_canny_parameters(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.png"
    Image.new("L", (2, 2), 100).save(source)

    code = main(
        [
            str(source),
            "--algorithm",
            "canny",
            "--canny-low",
            "200",
            "--canny-high",
            "100",
            "--locale",
            "pseudo",
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "[!!" in captured.err
    assert "thresholds must" not in captured.err


def test_inactive_canny_parameters_do_not_block_threshold_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "boundary.png"
    Image.new("L", (3, 3), 255).save(source)

    code = main(
        [
            str(source),
            "--output",
            str(output),
            "--algorithm",
            "threshold_boundary",
            "--canny-low",
            "255",
            "--canny-high",
            "0",
            "--canny-aperture",
            "9",
            "--canny-gradient",
            "invalid",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert output.exists()
    assert "threshold_boundary" in captured.out


def test_cli_component_preserves_existing_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "existing.png"
    Image.new("L", (3, 3), 255).save(source)
    output.write_bytes(b"user-owned")

    code = main([str(source), "--output", str(output)])

    captured = capsys.readouterr()
    assert code == 2
    assert output.read_bytes() == b"user-owned"
    assert "already exists" in captured.err


def test_cli_component_hides_native_backend_initialization_detail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.png"
    Image.new("L", (3, 3), 100).save(source)

    def fail_initialization(name: str) -> None:
        assert name == "cv2"
        raise RuntimeError("native init leaked detail")

    monkeypatch.setattr(
        "fourier_sketch.imaging.edge_detection.importlib.import_module",
        fail_initialization,
    )

    code = main([str(source), "--algorithm", "canny"])

    captured = capsys.readouterr()
    assert code == 2
    assert "unavailable" in captured.err
    assert "native init leaked detail" not in captured.err
    assert "Traceback" not in captured.err
