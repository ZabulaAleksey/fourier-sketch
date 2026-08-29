"""Analytical topology contracts for the FS-015 skeleton graph."""

import json

import pytest

from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import PixelPoint, RasterImage, RasterStage, SkeletonAlgorithm
from fourier_sketch.imaging.skeleton_graph import (
    _build_adjacency,
    _edge_drafts,
    _node_drafts,
    _row_major_key,
    build_skeleton_graph,
)
from fourier_sketch.imaging.skeleton_graph_model import (
    SKELETON_GRAPH_ADJACENCY_POLICY,
    SKELETON_GRAPH_SCHEMA,
    SkeletonGraphError,
    SkeletonGraphFailureCode,
    SkeletonGraphResult,
    SkeletonNodeKind,
)
from fourier_sketch.imaging.skeleton_model import SkeletonizationResult

pytestmark = pytest.mark.unit


def _source(width: int, height: int, points: set[tuple[int, int]]) -> SkeletonizationResult:
    pixels = bytearray(width * height)
    for column, row in points:
        pixels[row * width + column] = 255
    raster = RasterImage(width, height, bytes(pixels), RasterStage.BINARY)
    return SkeletonizationResult(
        source=raster,
        skeleton=raster,
        algorithm=SkeletonAlgorithm.LEE,
        backend="scikit-image/0.26.0",
        source_dimensions=(width, height),
        source_foreground_pixels=len(points),
        skeleton_foreground_pixels=len(points),
    )


def test_line_compresses_to_two_endpoints_and_one_edge() -> None:
    graph = build_skeleton_graph(_source(5, 3, {(column, 1) for column in range(5)}))

    assert graph.endpoint_count == 2
    assert graph.junction_count == 0
    assert len(graph.components) == 1
    assert len(graph.edges) == 1
    assert len(graph.edges[0].interior_pixels) == 3
    assert graph.components[0].has_loop is False


@pytest.mark.parametrize(
    ("points", "endpoints", "branches"),
    (
        (
            {(column, 1) for column in range(5)} | {(2, row) for row in range(1, 4)},
            3,
            3,
        ),
        (
            {(column, 2) for column in range(5)} | {(2, row) for row in range(5)},
            4,
            4,
        ),
    ),
)
def test_t_and_cross_have_one_compressed_junction_region(
    points: set[tuple[int, int]],
    endpoints: int,
    branches: int,
) -> None:
    graph = build_skeleton_graph(_source(5, 5, points))

    junctions = [node for node in graph.nodes if node.kind is SkeletonNodeKind.JUNCTION_REGION]
    assert graph.endpoint_count == endpoints
    assert len(junctions) == 1
    assert junctions[0].incidence_degree == branches
    assert len(graph.edges) == branches


def test_pure_loop_has_anchor_and_one_canonical_self_loop() -> None:
    points = (
        {(column, row) for column in range(5) for row in (0, 4)}
        | {(column, row) for column in (0, 4) for row in range(1, 4)}
    )

    graph = build_skeleton_graph(_source(5, 5, points))

    assert graph.endpoint_count == 0
    assert graph.loop_count == 1
    assert len(graph.nodes) == 1
    assert graph.nodes[0].kind is SkeletonNodeKind.LOOP_ANCHOR
    assert graph.nodes[0].anchor.column == 0
    assert graph.nodes[0].anchor.row == 0
    assert len(graph.edges) == 1
    assert graph.edges[0].is_self_loop
    assert len(graph.edges[0].interior_pixels) == len(points) - 1


def test_cycle_inside_compressed_junction_region_is_retained_in_component_provenance() -> None:
    points = {(0, 2), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 2)}

    graph = build_skeleton_graph(_source(5, 5, points))

    assert len(graph.components) == 1
    assert graph.components[0].has_loop
    assert graph.loop_count == 1


def test_components_are_explicit_and_never_bridged() -> None:
    points = {(0, 0), (1, 0), (2, 0), (5, 3)}

    graph = build_skeleton_graph(_source(6, 4, points))

    assert len(graph.components) == 2
    assert [component.pixel_count for component in graph.components] == [3, 1]
    assert all(edge.start_node_id != 2 and edge.end_node_id != 2 for edge in graph.edges)
    assert any(node.kind is SkeletonNodeKind.ISOLATED for node in graph.nodes)


def test_corner_suppression_keeps_l_shape_without_diagonal_triangle() -> None:
    graph = build_skeleton_graph(_source(2, 2, {(0, 0), (1, 0), (1, 1)}))

    assert graph.adjacency_policy == SKELETON_GRAPH_ADJACENCY_POLICY
    assert graph.endpoint_count == 2
    assert graph.junction_count == 0
    assert len(graph.edges) == 1


def test_clean_diagonal_stroke_remains_connected() -> None:
    graph = build_skeleton_graph(_source(4, 4, {(0, 0), (1, 1), (2, 2), (3, 3)}))

    assert len(graph.components) == 1
    assert graph.endpoint_count == 2
    assert len(graph.edges) == 1


def test_empty_graph_and_canonical_json_are_explicit() -> None:
    graph = build_skeleton_graph(_source(3, 2, set()))

    assert graph.is_empty
    assert graph.nodes == ()
    assert graph.edges == ()
    assert graph.components == ()
    payload = graph.to_json_bytes()
    assert payload == graph.to_json_bytes()
    decoded = json.loads(payload)
    assert decoded["schema"] == SKELETON_GRAPH_SCHEMA
    assert decoded["components"] == []


def test_invalid_input_and_cancellation_fail_typed() -> None:
    with pytest.raises(SkeletonGraphError) as invalid:
        build_skeleton_graph(object())  # type: ignore[arg-type]
    assert invalid.value.code is SkeletonGraphFailureCode.INVALID_INPUT

    with pytest.raises(SkeletonGraphError) as cancelled:
        build_skeleton_graph(_source(3, 1, {(0, 0), (1, 0)}), cancellation_check=lambda: True)
    assert cancelled.value.code is SkeletonGraphFailureCode.CANCELLED


def test_foreground_budget_fails_before_graph_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fourier_sketch.imaging.skeleton_graph.MAX_SKELETON_GRAPH_FOREGROUND_PIXELS",
        2,
    )

    with pytest.raises(SkeletonGraphError) as captured:
        build_skeleton_graph(_source(3, 1, {(0, 0), (1, 0), (2, 0)}))

    assert captured.value.code is SkeletonGraphFailureCode.RESOURCE_LIMIT


def test_public_result_model_enforces_foreground_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fourier_sketch.imaging.skeleton_graph_model.MAX_SKELETON_GRAPH_FOREGROUND_PIXELS",
        2,
    )

    with pytest.raises(DomainValidationError, match="foreground budget"):
        SkeletonGraphResult(_source(3, 1, {(0, 0), (1, 0), (2, 0)}), (), (), ())


def test_many_isolated_components_use_one_canonical_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    points = {
        (column, row)
        for column in range(0, 200, 2)
        for row in range(0, 40, 2)
    }
    original_key = _row_major_key
    key_calls = 0

    def counted_key(point: PixelPoint) -> tuple[int, int]:
        nonlocal key_calls
        key_calls += 1
        return original_key(point)

    monkeypatch.setattr("fourier_sketch.imaging.skeleton_graph._row_major_key", counted_key)

    graph = build_skeleton_graph(_source(200, 40, points))

    assert len(graph.components) == len(points)
    assert key_calls < len(points) * 20


def test_cancellation_is_checked_inside_long_edge_compression() -> None:
    points = {PixelPoint(column=column, row=0) for column in range(9000)}
    adjacency = _build_adjacency(points, None)
    component = frozenset(points)
    nodes = _node_drafts(component, adjacency, None)
    owner_by_point = {
        point: draft_index
        for draft_index, draft in enumerate(nodes)
        for point in draft.pixels
    }
    calls = 0

    def cancel_during_chain_trace() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 2

    with pytest.raises(SkeletonGraphError) as captured:
        _edge_drafts(
            component,
            nodes,
            owner_by_point,
            adjacency,
            cancel_during_chain_trace,
        )

    assert captured.value.code is SkeletonGraphFailureCode.CANCELLED
    assert calls == 2
