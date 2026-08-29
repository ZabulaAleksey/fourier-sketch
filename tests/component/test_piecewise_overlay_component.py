"""Visible pen-up overlay contracts for FS-016."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure
from PIL import Image, ImageDraw

from fourier_sketch.application import build_local_piecewise
from fourier_sketch.presentation import Translator
from fourier_sketch.render import draw_piecewise_overlay, render_piecewise_overlay_png

pytestmark = pytest.mark.component


def _result(tmp_path: Path):  # type: ignore[no-untyped-def]
    source = tmp_path / "separate.png"
    image = Image.new("L", (64, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 8, 25, 8), fill=255, width=5)
    draw.line((38, 23, 58, 23), fill=255, width=5)
    image.save(source)
    return build_local_piecewise(source)


def test_each_component_is_drawn_as_a_separate_artist(tmp_path: Path) -> None:
    result = _result(tmp_path)
    figure = Figure(figsize=(10, 5))
    axes = tuple(figure.subplots(1, 2))

    draw_piecewise_overlay(figure, axes, result, Translator("en"))

    assert len(axes[1].lines) == len(result.conversion.segments) == 2
    assert all(len(line.get_xdata()) == segment.curve.sample_count for line, segment in zip(
        axes[1].lines, result.conversion.segments, strict=True
    ))
    assert "explicit pen-up boundaries: 1" in "\n".join(
        text.get_text() for text in figure.texts
    )


def test_piecewise_png_is_a_real_atomic_artifact(tmp_path: Path) -> None:
    output = tmp_path / "piecewise.png"

    render_piecewise_overlay_png(_result(tmp_path), output, Translator("pseudo"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as rendered:
        assert rendered.width >= 1000
        assert rendered.height >= 500


def test_piecewise_png_preserves_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "piecewise.png"
    output.write_bytes(b"user-owned")

    with pytest.raises(FileExistsError):
        render_piecewise_overlay_png(_result(tmp_path), output, Translator("en"))

    assert output.read_bytes() == b"user-owned"
