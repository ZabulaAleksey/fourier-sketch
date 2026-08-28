"""In-process localized FS-010 CLI component contracts."""

from pathlib import Path

import pytest
from PIL import Image

from fourier_sketch.cli.image import main

pytestmark = pytest.mark.component


def test_cli_component_exports_selected_intermediate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "result.png"
    Image.new("L", (3, 2), 200).save(source)

    code = main([str(source), "--output", str(output), "--stage", "grayscale"])

    captured = capsys.readouterr()
    assert code == 0
    assert output.exists()
    assert "PNG" in captured.out
    assert "3x2" in captured.out


def test_cli_component_preserves_existing_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "existing.png"
    Image.new("L", (2, 2), 100).save(source)
    output.write_bytes(b"user-owned")

    code = main([str(source), "--output", str(output)])

    captured = capsys.readouterr()
    assert code == 2
    assert output.read_bytes() == b"user-owned"
    assert "already exists" in captured.err


def test_cli_component_localizes_invalid_options(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.png"
    Image.new("L", (2, 2), 100).save(source)

    code = main([str(source), "--threshold", "999", "--locale", "pseudo"])

    captured = capsys.readouterr()
    assert code == 2
    assert "[!!" in captured.err
    assert "threshold must" not in captured.err
