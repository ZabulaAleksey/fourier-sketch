"""Generated deterministic coverage contracts for FS-017."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fourier_sketch.imaging import RasterImage, RasterStage, SkeletonAlgorithm, raw_adjacency
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult
from fourier_sketch.routing import ForcedRouteStatus, RouteStepKind, build_forced_route

pytestmark = pytest.mark.property


@given(st.integers(min_value=2, max_value=200))
def test_generated_path_covers_every_original_link_once_and_is_deterministic(
    length: int,
) -> None:
    pixels = bytes([255]) * length
    raster = RasterImage(length, 1, pixels, RasterStage.BINARY)
    graph = build_skeleton_graph(
        SkeletonizationResult(
            raster,
            raster,
            SkeletonAlgorithm.LEE,
            "scikit-image/0.26.0",
            (length, 1),
            length,
            length,
        )
    )

    first = build_forced_route(graph)
    second = build_forced_route(graph)

    assert first == second
    assert first.status is ForcedRouteStatus.READY
    originals = [step for step in first.steps if step.kind is RouteStepKind.ORIGINAL]
    graph_pixels = {
        pixel for node in graph.nodes for pixel in node.owned_pixels
    }.union(pixel for edge in graph.edges for pixel in edge.interior_pixels)
    assert len(originals) == sum(
        len(values) for values in raw_adjacency(graph_pixels).values()
    ) // 2
    assert len({frozenset((step.start, step.end)) for step in originals}) == len(originals)
