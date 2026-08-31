"""FS-017 route provenance overlay contracts."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure
from PIL import Image, ImageDraw

from fourier_sketch.application import build_local_forced_route, compare_local_forced_routes
from fourier_sketch.presentation import Translator
from fourier_sketch.render import (
    draw_forced_route_overlay,
    render_forced_route_overlay_png,
    render_route_optimization_png,
)

pytestmark = pytest.mark.component


def _result(tmp_path: Path):  # type: ignore[no-untyped-def]
    source = tmp_path / "route.png"
    image = Image.new("L", (60, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 8, 24, 8), fill=255, width=5)
    draw.line((36, 24, 55, 24), fill=255, width=5)
    image.save(source)
    return build_local_forced_route(source, sample_count=32, harmonic_count=8)


def test_overlay_exposes_original_links_bridges_cost_and_fourier(tmp_path: Path) -> None:
    result = _result(tmp_path)
    figure = Figure(figsize=(12, 5))
    axes = tuple(figure.subplots(1, 2))

    draw_forced_route_overlay(figure, axes, result, Translator("en"))

    labels = {collection.get_label() for collection in axes[0].collections}
    assert "Original skeleton links" in labels
    assert "Explicit bridges" in labels
    assert axes[1].lines
    assert "bridges: 2" in "\n".join(text.get_text() for text in figure.texts)


def test_forced_route_png_is_atomic_and_readable(tmp_path: Path) -> None:
    output = tmp_path / "forced.png"
    render_forced_route_overlay_png(_result(tmp_path), output, Translator("pseudo"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(FileExistsError):
        render_forced_route_overlay_png(_result(tmp_path), output, Translator("en"))


def test_optimization_comparison_renders_both_routes_and_fourier_frames(
    tmp_path: Path,
) -> None:
    source = tmp_path / "route-comparison.png"
    image = Image.new("L", (60, 32), 0)
    draw = ImageDraw.Draw(image)
    draw.line((5, 8, 24, 8), fill=255, width=5)
    draw.line((36, 24, 55, 24), fill=255, width=5)
    image.save(source)
    comparison = compare_local_forced_routes(source, sample_count=32, harmonic_count=8)
    output = tmp_path / "comparison-output.png"

    render_route_optimization_png(comparison, output, Translator("en"))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(FileExistsError):
        render_route_optimization_png(comparison, output, Translator("en"))
