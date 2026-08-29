"""Generative invariants for deterministic simple component conversion."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.imaging import RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult
from fourier_sketch.routing import PiecewiseBuildStatus, build_piecewise_components

pytestmark = pytest.mark.property


@given(st.integers(min_value=2, max_value=200), st.integers(min_value=1, max_value=25))
def test_horizontal_path_conversion_is_deterministic_and_exact(length: int, row: int) -> None:
    width = length + 2
    height = row + 2
    points = {(column, row) for column in range(1, length + 1)}
    pixels = bytearray(width * height)
    for column, point_row in points:
        pixels[point_row * width + column] = 255
    raster = RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    source = SkeletonizationResult(
        raster,
        raster,
        SkeletonAlgorithm.LEE,
        "scikit-image/0.26.0",
        (width, height),
        length,
        length,
    )
    graph = build_skeleton_graph(source)

    first = build_piecewise_components(graph)
    second = build_piecewise_components(graph)

    assert first == second
    assert first.status is PiecewiseBuildStatus.READY
    assert first.segments[0].provenance.raster_pixels == tuple(
        sorted(first.segments[0].provenance.raster_pixels, key=lambda point: point.column)
    )
    assert set(first.segments[0].provenance.raster_pixels) == {
        point for node in graph.nodes for point in node.owned_pixels
    }.union(point for edge in graph.edges for point in edge.interior_pixels)
