"""FS-029 deterministic better-single-stroke routing contracts."""

import pytest

from fourier_sketch.imaging import RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult
from fourier_sketch.routing import (
    ForcedRouteAlgorithm,
    ForcedRouteStatus,
    RouteStepKind,
    build_forced_route,
)

pytestmark = pytest.mark.unit

_ASYMMETRIC_PIXELS = {
    (5, 8), (6, 8), (7, 6), (7, 7), (7, 8), (7, 9), (7, 10),
    (8, 8), (8, 10), (8, 11), (9, 8), (9, 10), (10, 8),
    (10, 9), (10, 10), (11, 7), (11, 8), (11, 10), (12, 8),
    (12, 9), (12, 10), (13, 7), (13, 8), (13, 10),
}


def _graph(  # type: ignore[no-untyped-def]
    points: set[tuple[int, int]], width: int = 16, height: int = 16
):
    pixels = bytearray(width * height)
    for column, row in points:
        pixels[row * width + column] = 255
    raster = RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    return build_skeleton_graph(
        SkeletonizationResult(
            raster,
            raster,
            SkeletonAlgorithm.LEE,
            "scikit-image/0.26.0",
            (width, height),
            len(points),
            len(points),
        )
    )


def test_default_preserves_versioned_baseline_and_improved_lowers_fixture_cost() -> None:
    graph = _graph(_ASYMMETRIC_PIXELS)

    default = build_forced_route(graph)
    baseline = build_forced_route(
        graph, algorithm=ForcedRouteAlgorithm.BASELINE_TREE_T_JOIN_V1
    )
    improved = build_forced_route(
        graph, algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
    )

    assert default == baseline
    assert baseline.status is improved.status is ForcedRouteStatus.READY
    assert baseline.metrics is not None and improved.metrics is not None
    assert improved.metrics.duplicated_length < baseline.metrics.duplicated_length
    assert improved.metrics.bridge_length == baseline.metrics.bridge_length
    assert improved.optimization_expansions > 0


def test_improved_route_is_deterministic_and_covers_every_original_link_once() -> None:
    graph = _graph(_ASYMMETRIC_PIXELS)
    first = build_forced_route(
        graph, algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
    )
    second = build_forced_route(
        graph, algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
    )

    assert first == second
    assert first.curve is not None and first.curve.closed
    originals = [step for step in first.steps if step.kind is RouteStepKind.ORIGINAL]
    assert first.metrics is not None
    assert len(originals) == first.metrics.covered_links
    assert len({frozenset((step.start, step.end)) for step in originals}) == len(originals)


def test_improved_route_has_explicit_budget_and_cancellation_failures() -> None:
    graph = _graph(_ASYMMETRIC_PIXELS)

    limited = build_forced_route(
        graph,
        algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1,
        max_optimization_expansions=1,
    )
    cancelled = build_forced_route(
        graph,
        algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1,
        cancellation_check=lambda: True,
    )

    assert limited.status is ForcedRouteStatus.RESOURCE_LIMIT
    assert limited.reason == "optimization_limit"
    assert limited.curve is None and limited.metrics is None
    assert limited.algorithm is ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
    assert cancelled.status is ForcedRouteStatus.CANCELLED
    assert cancelled.curve is None


def test_optimization_budget_is_shared_across_disconnected_components() -> None:
    shifted = {(column + 20, row) for column, row in _ASYMMETRIC_PIXELS}
    graph = _graph(_ASYMMETRIC_PIXELS | shifted, width=40)

    result = build_forced_route(
        graph,
        algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1,
        max_optimization_expansions=27,
    )

    assert result.status is ForcedRouteStatus.RESOURCE_LIMIT
    assert result.reason == "optimization_limit"
    assert result.optimization_expansions == 28
