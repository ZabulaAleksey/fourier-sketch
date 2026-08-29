"""Generative pixel-ownership and determinism evidence for FS-015."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from fourier_sketch.imaging import PixelPoint, RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult

pytestmark = pytest.mark.property


def _source(points: set[tuple[int, int]]) -> SkeletonizationResult:
    width = height = 8
    pixels = bytearray(width * height)
    for column, row in points:
        pixels[row * width + column] = 255
    raster = RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    return SkeletonizationResult(
        raster,
        raster,
        SkeletonAlgorithm.LEE,
        "scikit-image/0.26.0",
        (width, height),
        len(points),
        len(points),
    )


def _has_solid_two_by_two(points: set[tuple[int, int]]) -> bool:
    return any(
        {(column, row), (column + 1, row), (column, row + 1), (column + 1, row + 1)}
        <= points
        for column in range(7)
        for row in range(7)
    )


@given(
    st.sets(
        st.tuples(st.integers(min_value=0, max_value=7), st.integers(min_value=0, max_value=7)),
        max_size=32,
    )
)
def test_every_accepted_skeleton_pixel_is_owned_once_and_serialization_is_stable(
    points: set[tuple[int, int]],
) -> None:
    assume(not _has_solid_two_by_two(points))

    graph = build_skeleton_graph(_source(points))
    owned = [point for node in graph.nodes for point in node.owned_pixels] + [
        point for edge in graph.edges for point in edge.interior_pixels
    ]

    expected = {PixelPoint(column=column, row=row) for column, row in points}
    assert len(owned) == len(set(owned))
    assert set(owned) == expected
    assert graph.to_json_bytes() == build_skeleton_graph(_source(points)).to_json_bytes()
    assert sum(component.pixel_count for component in graph.components) == len(points)
