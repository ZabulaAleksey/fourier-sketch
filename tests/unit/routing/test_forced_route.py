"""Analytical FS-017 forced-route contracts."""

import pytest

from fourier_sketch.imaging import RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import build_skeleton_graph
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult
from fourier_sketch.routing import ForcedRouteStatus, RouteStepKind, build_forced_route

pytestmark = pytest.mark.unit


def _graph(width: int, height: int, points: set[tuple[int, int]]):  # type: ignore[no-untyped-def]
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


def test_euler_loop_routes_each_original_link_once_without_added_cost() -> None:
    points = (
        {(column, row) for column in range(5) for row in (0, 4)}
        | {(column, row) for column in (0, 4) for row in range(1, 4)}
    )

    result = build_forced_route(_graph(5, 5, points))

    assert result.status is ForcedRouteStatus.READY
    assert result.curve is not None and result.curve.closed
    assert result.metrics is not None
    assert result.metrics.original_steps == len(points)
    assert result.metrics.duplicated_steps == result.metrics.bridge_steps == 0
    assert result.metrics.added_length == 0.0


def test_two_odd_path_uses_exact_trail_and_explicit_closing_bridge() -> None:
    result = build_forced_route(_graph(5, 1, {(column, 0) for column in range(5)}))

    assert result.status is ForcedRouteStatus.READY
    assert result.metrics is not None
    assert result.metrics.original_steps == 4
    assert result.metrics.duplicated_steps == 0
    assert result.metrics.bridge_steps == 1
    assert result.steps[-1].kind is RouteStepKind.BRIDGE


def test_cross_uses_tree_t_join_and_covers_original_links_once() -> None:
    points = {(column, 2) for column in range(5)} | {(2, row) for row in range(5)}

    first = build_forced_route(_graph(5, 5, points))
    second = build_forced_route(_graph(5, 5, points))

    assert first == second
    assert first.status is ForcedRouteStatus.READY
    assert first.metrics is not None
    assert first.metrics.original_steps == 8
    assert 0 < first.metrics.duplicated_steps <= len(points) - 1
    assert first.metrics.bridge_steps == 0
    assert all(
        step.source_node_id is not None or step.source_edge_id is not None
        for step in first.steps
        if step.kind is not RouteStepKind.BRIDGE
    )


def test_disconnected_components_have_explicit_cyclic_bridges() -> None:
    points = {(0, 0), (1, 0), (2, 0), (7, 3), (8, 3), (9, 3)}

    result = build_forced_route(_graph(10, 4, points))

    assert result.status is ForcedRouteStatus.READY
    assert result.metrics is not None
    assert result.component_order == (0, 1)
    assert result.metrics.bridge_steps == 2
    assert result.steps[-1].end == result.steps[0].start
    assert all(
        step.source_node_id is None and step.source_edge_id is None
        for step in result.steps
        if step.kind is RouteStepKind.BRIDGE
    )


def test_isolated_empty_and_cancelled_are_explicit() -> None:
    isolated = build_forced_route(_graph(1, 1, {(0, 0)}))
    empty = build_forced_route(_graph(1, 1, set()))
    cancelled = build_forced_route(
        _graph(5000, 1, {(column, 0) for column in range(5000)}),
        cancellation_check=lambda: True,
    )

    assert isolated.status is ForcedRouteStatus.READY
    assert isolated.curve is not None and isolated.curve.sample_count == 1
    assert isolated.steps == ()
    assert empty.status is ForcedRouteStatus.EMPTY
    assert cancelled.status is ForcedRouteStatus.CANCELLED
    assert cancelled.curve is None


def test_singleton_route_honors_immediate_cancellation() -> None:
    result = build_forced_route(
        _graph(1, 1, {(0, 0)}), cancellation_check=lambda: True
    )

    assert result.status is ForcedRouteStatus.CANCELLED
    assert result.curve is None
