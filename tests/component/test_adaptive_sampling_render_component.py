"""Renderer and in-process contour CLI contracts for FS-028."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    AdaptiveSamplingComparison,
    AdaptiveSamplingConfig,
    compare_adaptive_sampling,
)
from fourier_sketch.cli.contours import main
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_adaptive_sampling_png

pytestmark = pytest.mark.component


def _comparison() -> AdaptiveSamplingComparison:
    source = Curve(
        (
            Point2D(0.0, 0.0),
            Point2D(3.0, 0.0),
            Point2D(3.0, 1.0),
            Point2D(4.0, 1.0),
            Point2D(4.0, 4.0),
        )
    )
    return compare_adaptive_sampling(
        source,
        AdaptiveSamplingConfig(curvature_weight=12.0, sample_count=32, harmonic_count=8),
    )


def test_renderer_writes_atomic_adaptive_comparison(tmp_path: Path) -> None:
    comparison = _comparison()
    output = tmp_path / "adaptive.png"

    render_adaptive_sampling_png(comparison, output, Translator("pseudo"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width > 500
        assert rendered.height > 500
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        render_adaptive_sampling_png(comparison, output, Translator("en"))
    assert output.read_bytes() == before


def test_contour_cli_adaptive_option_and_conflict_are_explicit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "adaptive.png"
    image = Image.new("L", (48, 36), 0)
    ImageDraw.Draw(image).rectangle((8, 6, 39, 29), fill=255)
    image.save(source)

    code = main(
        [
            str(source),
            "--output",
            str(output),
            "--samples",
            "32",
            "--harmonics",
            "8",
            "--frames",
            "2",
            "--adaptive-curvature-weight",
            "15",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0, captured.err
    assert "Adaptive sampling comparison written" in captured.out
    assert "adaptive-weighted-arc-length-v1" in captured.out
    assert output.exists()

    conflict = main(
        [
            str(source),
            "--output",
            str(tmp_path / "conflict.png"),
            "--simplify-tolerance",
            "0.01",
            "--adaptive-curvature-weight",
            "5",
        ]
    )
    conflict_capture = capsys.readouterr()
    assert conflict == 2
    assert "Contour diagnostic failed" in conflict_capture.err
    assert not (tmp_path / "conflict.png").exists()
