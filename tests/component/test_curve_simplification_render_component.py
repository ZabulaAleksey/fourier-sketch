"""Renderer and in-process contour CLI contracts for FS-027."""

from math import cos, pi, sin
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import (
    CurveSimplificationComparison,
    CurveSimplificationConfig,
    compare_curve_simplification,
)
from fourier_sketch.cli.contours import main
from fourier_sketch.domain import Curve, Point2D
from fourier_sketch.presentation import Translator
from fourier_sketch.render import render_curve_simplification_png

pytestmark = pytest.mark.component


def _comparison() -> CurveSimplificationComparison:
    source = Curve(
        tuple(
            Point2D(cos(2.0 * pi * index / 64), sin(2.0 * pi * index / 64))
            for index in range(64)
        ),
        closed=True,
    )
    return compare_curve_simplification(
        source,
        CurveSimplificationConfig(tolerance=0.02, sample_count=32, harmonic_count=8),
    )


def test_renderer_writes_readable_atomic_comparison_and_preserves_existing(
    tmp_path: Path,
) -> None:
    comparison = _comparison()
    output = tmp_path / "comparison.png"

    render_curve_simplification_png(comparison, output, Translator("pseudo"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width > 500
        assert rendered.height > 500
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        render_curve_simplification_png(comparison, output, Translator("en"))
    assert output.read_bytes() == before


def test_contour_cli_opt_in_renders_metrics_and_legacy_path_remains_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "shape.png"
    simplified_output = tmp_path / "simplification.png"
    legacy_output = tmp_path / "legacy.png"
    image = Image.new("L", (48, 36), 0)
    ImageDraw.Draw(image).rectangle((8, 6, 39, 29), fill=255)
    image.save(source)

    simplified_code = main(
        [
            str(source),
            "--output",
            str(simplified_output),
            "--samples",
            "32",
            "--harmonics",
            "8",
            "--frames",
            "2",
            "--simplify-tolerance",
            "0.01",
        ]
    )
    simplified_capture = capsys.readouterr()
    legacy_code = main(
        [
            str(source),
            "--output",
            str(legacy_output),
            "--samples",
            "32",
            "--harmonics",
            "8",
            "--frames",
            "2",
        ]
    )
    legacy_capture = capsys.readouterr()

    assert simplified_code == 0, simplified_capture.err
    assert "points" in simplified_capture.out
    assert "sampled RMSE" in simplified_capture.out
    assert simplified_output.exists()
    assert legacy_code == 0, legacy_capture.err
    assert "Contour trace written" in legacy_capture.out
    assert legacy_output.exists()


def test_simplification_budget_failure_is_localized_and_preserves_destination(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "shape.png"
    output = tmp_path / "owned.png"
    image = Image.new("L", (48, 36), 0)
    ImageDraw.Draw(image).ellipse((5, 4, 42, 31), fill=255)
    image.save(source)
    output.write_bytes(b"user-owned")

    code = main(
        [
            str(source),
            "--output",
            str(output),
            "--simplify-tolerance",
            "0.01",
            "--simplification-budget",
            "1",
            "--locale",
            "pseudo",
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    assert "[!!" in captured.err
    assert output.read_bytes() == b"user-owned"
    assert str(source) not in captured.err
