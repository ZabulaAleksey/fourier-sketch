"""Linear raster skeleton to compressed topology transform for FS-015."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fourier_sketch.domain import DomainValidationError

from .contour_model import PixelPoint
from .skeleton_graph_model import (
    MAX_SKELETON_GRAPH_FOREGROUND_PIXELS,
    MAX_SKELETON_GRAPH_RECORDS,
    SkeletonGraphComponent,
    SkeletonGraphEdge,
    SkeletonGraphError,
    SkeletonGraphFailureCode,
    SkeletonGraphNode,
    SkeletonGraphResult,
    SkeletonNodeKind,
)
from .skeleton_model import SkeletonizationResult

CancellationCheck = Callable[[], bool]
_ORTHOGONAL = ((-1, 0), (0, -1), (0, 1), (1, 0))
_DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_CANCELLATION_BATCH = 4096


@dataclass(frozen=True, slots=True)
class _NodeDraft:
    kind: SkeletonNodeKind
    pixels: tuple[PixelPoint, ...]


@dataclass(frozen=True, slots=True)
class _EdgeDraft:
    start_draft: int
    end_draft: int
    path: tuple[PixelPoint, ...]


def build_skeleton_graph(
    source: SkeletonizationResult,
    *,
    cancellation_check: CancellationCheck | None = None,
) -> SkeletonGraphResult:
    """Build a deterministic undirected pseudomultigraph without routing semantics."""
    if not isinstance(source, SkeletonizationResult):
        raise SkeletonGraphError(
            SkeletonGraphFailureCode.INVALID_INPUT,
            "skeleton graph requires a typed skeletonization result",
        )
    _check_cancelled(cancellation_check)
    points = _foreground_points(source, cancellation_check)
    if not points:
        return SkeletonGraphResult(source, (), (), ())
    adjacency = _build_adjacency(points, cancellation_check)
    components = _connected_components(points, adjacency, cancellation_check)
    all_nodes: list[SkeletonGraphNode] = []
    all_edges: list[SkeletonGraphEdge] = []
    graph_components: list[SkeletonGraphComponent] = []

    for component_id, component_points in enumerate(components):
        drafts = _node_drafts(component_points, adjacency, cancellation_check)
        owner_by_point = {
            point: draft_index
            for draft_index, draft in enumerate(drafts)
            for point in draft.pixels
        }
        edge_drafts = _edge_drafts(
            component_points, drafts, owner_by_point, adjacency, cancellation_check
        )
        degrees = [0] * len(drafts)
        for edge in edge_drafts:
            degrees[edge.start_draft] += 1
            degrees[edge.end_draft] += 1

        node_offset = len(all_nodes)
        edge_offset = len(all_edges)
        for draft_index, draft in enumerate(drafts):
            all_nodes.append(
                SkeletonGraphNode(
                    id=node_offset + draft_index,
                    component_id=component_id,
                    kind=draft.kind,
                    owned_pixels=draft.pixels,
                    incidence_degree=degrees[draft_index],
                )
            )
        canonical_edges = sorted(edge_drafts, key=_edge_draft_key)
        for edge_index, edge_draft in enumerate(canonical_edges):
            all_edges.append(
                SkeletonGraphEdge(
                    id=edge_offset + edge_index,
                    component_id=component_id,
                    start_node_id=node_offset + edge_draft.start_draft,
                    end_node_id=node_offset + edge_draft.end_draft,
                    start_contact=edge_draft.path[0],
                    end_contact=edge_draft.path[-1],
                    interior_pixels=edge_draft.path[1:-1],
                )
            )
        node_ids = tuple(range(node_offset, len(all_nodes)))
        edge_ids = tuple(range(edge_offset, len(all_edges)))
        graph_components.append(
            SkeletonGraphComponent(
                id=component_id,
                pixel_count=len(component_points),
                node_ids=node_ids,
                edge_ids=edge_ids,
                has_loop=_has_raw_cycle(component_points, adjacency),
            )
        )
        if len(all_nodes) + len(all_edges) > MAX_SKELETON_GRAPH_RECORDS:
            raise SkeletonGraphError(
                SkeletonGraphFailureCode.RESOURCE_LIMIT,
                "skeleton graph record limit exceeded",
            )
        _check_cancelled(cancellation_check)

    try:
        return SkeletonGraphResult(
            source=source,
            nodes=tuple(all_nodes),
            edges=tuple(all_edges),
            components=tuple(graph_components),
        )
    except DomainValidationError as error:
        raise SkeletonGraphError(
            SkeletonGraphFailureCode.MALFORMED_TOPOLOGY,
            "skeleton graph failed its topology contract",
        ) from error


def _foreground_points(
    source: SkeletonizationResult,
    cancellation_check: CancellationCheck | None,
) -> set[PixelPoint]:
    raster = source.skeleton
    points: set[PixelPoint] = set()
    for index, value in enumerate(raster.pixels):
        if index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        if value == 255:
            points.add(PixelPoint(column=index % raster.width, row=index // raster.width))
            if len(points) > MAX_SKELETON_GRAPH_FOREGROUND_PIXELS:
                raise SkeletonGraphError(
                    SkeletonGraphFailureCode.RESOURCE_LIMIT,
                    "skeleton graph foreground limit exceeded",
                )
    return points


def _adjacent_points(point: PixelPoint, points: set[PixelPoint]) -> tuple[PixelPoint, ...]:
    adjacent: list[PixelPoint] = []
    for row_delta, column_delta in _ORTHOGONAL:
        candidate = _offset(point, row_delta, column_delta)
        if candidate is not None and candidate in points:
            adjacent.append(candidate)
    for row_delta, column_delta in _DIAGONAL:
        candidate = _offset(point, row_delta, column_delta)
        if candidate is None or candidate not in points:
            continue
        bridge_horizontal = _offset(point, 0, column_delta)
        bridge_vertical = _offset(point, row_delta, 0)
        if bridge_horizontal not in points and bridge_vertical not in points:
            adjacent.append(candidate)
    return tuple(sorted(adjacent, key=_row_major_key))


def _build_adjacency(
    points: set[PixelPoint],
    cancellation_check: CancellationCheck | None,
) -> dict[PixelPoint, tuple[PixelPoint, ...]]:
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]] = {}
    for index, point in enumerate(sorted(points, key=_row_major_key)):
        if index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        adjacency[point] = _adjacent_points(point, points)
    return adjacency


def _connected_components(
    points: set[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
    cancellation_check: CancellationCheck | None,
) -> tuple[frozenset[PixelPoint], ...]:
    visited: set[PixelPoint] = set()
    components: list[frozenset[PixelPoint]] = []
    for root_index, root in enumerate(sorted(points, key=_row_major_key)):
        if root in visited:
            continue
        if root_index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        visited.add(root)
        stack = [root]
        component = {root}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
            if len(component) % _CANCELLATION_BATCH == 0:
                _check_cancelled(cancellation_check)
        components.append(frozenset(component))
    return tuple(components)


def _node_drafts(
    component: frozenset[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
    cancellation_check: CancellationCheck | None,
) -> tuple[_NodeDraft, ...]:
    junctions: set[PixelPoint] = set()
    ordered_component = sorted(component, key=_row_major_key)
    for index, point in enumerate(ordered_component):
        if index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        if len(adjacency[point]) >= 3:
            junctions.add(point)
    regions = _junction_regions(junctions, adjacency, cancellation_check)
    drafts = [
        _NodeDraft(SkeletonNodeKind.JUNCTION_REGION, tuple(sorted(region, key=_row_major_key)))
        for region in regions
    ]
    for index, point in enumerate(ordered_component):
        if index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        degree = len(adjacency[point])
        if degree == 0:
            drafts.append(_NodeDraft(SkeletonNodeKind.ISOLATED, (point,)))
        elif degree == 1:
            drafts.append(_NodeDraft(SkeletonNodeKind.ENDPOINT, (point,)))
    if not drafts:
        anchor = min(component, key=_row_major_key)
        drafts.append(_NodeDraft(SkeletonNodeKind.LOOP_ANCHOR, (anchor,)))
    return tuple(sorted(drafts, key=_node_draft_key))


def _junction_regions(
    junctions: set[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
    cancellation_check: CancellationCheck | None,
) -> tuple[frozenset[PixelPoint], ...]:
    visited: set[PixelPoint] = set()
    regions: list[frozenset[PixelPoint]] = []
    for root_index, root in enumerate(sorted(junctions, key=_row_major_key)):
        if root in visited:
            continue
        if root_index % _CANCELLATION_BATCH == 0:
            _check_cancelled(cancellation_check)
        visited.add(root)
        stack = [root]
        region = {root}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in junctions and neighbor not in visited:
                    visited.add(neighbor)
                    region.add(neighbor)
                    stack.append(neighbor)
            if len(region) % _CANCELLATION_BATCH == 0:
                _check_cancelled(cancellation_check)
        regions.append(frozenset(region))
    return tuple(regions)


def _edge_drafts(
    component: frozenset[PixelPoint],
    nodes: tuple[_NodeDraft, ...],
    owner_by_point: dict[PixelPoint, int],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
    cancellation_check: CancellationCheck | None,
) -> tuple[_EdgeDraft, ...]:
    visited_links: set[frozenset[PixelPoint]] = set()
    edges: list[_EdgeDraft] = []
    processed_contacts = 0
    for start_index, node in enumerate(nodes):
        for start_contact in node.pixels:
            if processed_contacts % _CANCELLATION_BATCH == 0:
                _check_cancelled(cancellation_check)
            processed_contacts += 1
            for neighbor in adjacency[start_contact]:
                if owner_by_point.get(neighbor) == start_index:
                    continue
                link = frozenset((start_contact, neighbor))
                if link in visited_links:
                    continue
                path = [start_contact, neighbor]
                visited_links.add(link)
                previous = start_contact
                current = neighbor
                while current not in owner_by_point:
                    choices = [
                        candidate
                        for candidate in adjacency[current]
                        if candidate != previous
                    ]
                    if len(choices) != 1:
                        raise SkeletonGraphError(
                            SkeletonGraphFailureCode.MALFORMED_TOPOLOGY,
                            "compressed chain encountered a non-continuation pixel",
                        )
                    following = choices[0]
                    visited_links.add(frozenset((current, following)))
                    path.append(following)
                    previous, current = current, following
                    if len(path) % _CANCELLATION_BATCH == 0:
                        _check_cancelled(cancellation_check)
                end_index = owner_by_point[current]
                canonical_path = _canonical_path(tuple(path))
                if canonical_path == tuple(path):
                    canonical_start, canonical_end = start_index, end_index
                else:
                    canonical_start, canonical_end = end_index, start_index
                edges.append(_EdgeDraft(canonical_start, canonical_end, canonical_path))

    continuation = component.difference(owner_by_point)
    owned_interiors = {point for edge in edges for point in edge.path[1:-1]}
    if owned_interiors != continuation:
        raise SkeletonGraphError(
            SkeletonGraphFailureCode.MALFORMED_TOPOLOGY,
            "compressed chains do not partition continuation pixels",
        )
    return tuple(edges)


def _canonical_path(path: tuple[PixelPoint, ...]) -> tuple[PixelPoint, ...]:
    reverse = tuple(reversed(path))
    return min(path, reverse, key=lambda value: tuple(_row_major_key(point) for point in value))


def _has_raw_cycle(
    component: frozenset[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
) -> bool:
    undirected_edges = sum(len(adjacency[point]) for point in component) // 2
    return undirected_edges - len(component) + 1 > 0


def _node_draft_key(node: _NodeDraft) -> tuple[tuple[int, int], str, tuple[tuple[int, int], ...]]:
    return (
        _row_major_key(node.pixels[0]),
        node.kind.value,
        tuple(_row_major_key(point) for point in node.pixels),
    )


def _edge_draft_key(edge: _EdgeDraft) -> tuple[int, int, tuple[tuple[int, int], ...]]:
    return (
        edge.start_draft,
        edge.end_draft,
        tuple(_row_major_key(point) for point in edge.path),
    )


def _offset(point: PixelPoint, row_delta: int, column_delta: int) -> PixelPoint | None:
    row = point.row + row_delta
    column = point.column + column_delta
    if row < 0 or column < 0:
        return None
    return PixelPoint(column=column, row=row)


def _row_major_key(point: PixelPoint) -> tuple[int, int]:
    return point.row, point.column


def _check_cancelled(cancellation_check: CancellationCheck | None) -> None:
    if cancellation_check is not None and cancellation_check():
        raise SkeletonGraphError(
            SkeletonGraphFailureCode.CANCELLED,
            "skeleton graph build cancelled",
        )
