"""Real FS-010 -> FS-016 multi-component pipeline evidence."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from fourier_sketch.application import build_local_piecewise
from fourier_sketch.routing import PiecewiseBuildStatus

pytestmark = pytest.mark.integration


def _two_rings(path: Path) -> None:
    image = Image.new("L", (80, 44), 0)
    draw = ImageDraw.Draw(image)
    draw.ellipse((7, 7, 33, 35), outline=255, width=5)
    draw.ellipse((48, 10, 72, 34), outline=255, width=5)
    image.save(path)


def test_two_disconnected_rings_reach_two_closed_piecewise_segments(tmp_path: Path) -> None:
    source = tmp_path / "rings.png"
    _two_rings(source)

    result = build_local_piecewise(source)

    assert result.conversion.status is PiecewiseBuildStatus.READY
    assert result.conversion.piecewise is not None
    assert result.conversion.piecewise.segment_count == 2
    assert all(segment.closed for segment in result.conversion.piecewise.segments)
    assert [segment.boundary_after for segment in result.conversion.segments] == [True, False]
    assert len(result.skeleton_graph.graph.components) == 2
