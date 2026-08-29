"""Immutable raster-topology contracts for the FS-015 skeleton graph."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from fourier_sketch.domain import DomainValidationError

from .contour_model import PixelPoint
from .skeleton_model import SkeletonizationResult

SKELETON_GRAPH_ADJACENCY_POLICY = "corner-suppressed-8-v1"
SKELETON_GRAPH_SCHEMA = "fourier-sketch/skeleton-graph-v1"
SKELETON_GRAPH_BUILDER = "fourier-sketch/linear-chain-compression-v1"
MAX_SKELETON_GRAPH_FOREGROUND_PIXELS = 250_000
MAX_SKELETON_GRAPH_RECORDS = 500_000
MAX_SKELETON_GRAPH_JSON_BYTES = 32 * 1024 * 1024


class SkeletonGraphFailureCode(StrEnum):
    """Stable fail-closed graph failure categories."""

    INVALID_INPUT = "invalid_input"
    RESOURCE_LIMIT = "resource_limit"
    MALFORMED_TOPOLOGY = "malformed_topology"
    CANCELLED = "cancelled"


class SkeletonGraphError(DomainValidationError):
    """Typed graph failure without source payload or path disclosure."""

    def __init__(self, code: SkeletonGraphFailureCode, message: str) -> None:
        if (
            not isinstance(code, SkeletonGraphFailureCode)
            or not isinstance(message, str)
            or not message
        ):
            raise DomainValidationError("skeleton graph error requires a typed code and message")
        self.code = code
        super().__init__(message)


class SkeletonNodeKind(StrEnum):
    """Compressed node role, distinct from a raw raster pixel degree."""

    ENDPOINT = "endpoint"
    JUNCTION_REGION = "junction_region"
    LOOP_ANCHOR = "loop_anchor"
    ISOLATED = "isolated"


@dataclass(frozen=True, slots=True)
class SkeletonGraphNode:
    """One compressed node and the skeleton pixels it exclusively owns."""

    id: int
    component_id: int
    kind: SkeletonNodeKind
    owned_pixels: tuple[PixelPoint, ...]
    incidence_degree: int

    def __post_init__(self) -> None:
        _validate_identifier(self.id, "node")
        _validate_identifier(self.component_id, "component")
        if not isinstance(self.kind, SkeletonNodeKind):
            raise DomainValidationError("graph node kind must be explicit")
        _validate_points(
            self.owned_pixels,
            "node-owned",
            allow_empty=False,
            require_row_major=True,
        )
        if type(self.incidence_degree) is not int or self.incidence_degree < 0:
            raise DomainValidationError("node incidence degree must be non-negative")
        if self.kind is SkeletonNodeKind.ISOLATED and self.incidence_degree != 0:
            raise DomainValidationError("isolated node must have zero incidence")
        if self.kind is SkeletonNodeKind.ENDPOINT and self.incidence_degree != 1:
            raise DomainValidationError("endpoint node must have one incidence")
        if self.kind is SkeletonNodeKind.LOOP_ANCHOR and self.incidence_degree != 2:
            raise DomainValidationError("loop anchor must have self-loop incidence two")

    @property
    def anchor(self) -> PixelPoint:
        return min(self.owned_pixels, key=_row_major_key)


@dataclass(frozen=True, slots=True)
class SkeletonGraphEdge:
    """One undirected compressed chain with explicit node contacts."""

    id: int
    component_id: int
    start_node_id: int
    end_node_id: int
    start_contact: PixelPoint
    end_contact: PixelPoint
    interior_pixels: tuple[PixelPoint, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.id, "edge"),
            (self.component_id, "component"),
            (self.start_node_id, "start node"),
            (self.end_node_id, "end node"),
        ):
            _validate_identifier(value, label)
        if not isinstance(self.start_contact, PixelPoint) or not isinstance(
            self.end_contact, PixelPoint
        ):
            raise DomainValidationError("edge contacts must be raster PixelPoint values")
        _validate_points(
            self.interior_pixels,
            "edge-interior",
            allow_empty=True,
            require_row_major=False,
        )

    @property
    def is_self_loop(self) -> bool:
        return self.start_node_id == self.end_node_id


@dataclass(frozen=True, slots=True)
class SkeletonGraphComponent:
    """Explicit connected-component membership without an implicit bridge."""

    id: int
    pixel_count: int
    node_ids: tuple[int, ...]
    edge_ids: tuple[int, ...]
    has_loop: bool

    def __post_init__(self) -> None:
        _validate_identifier(self.id, "component")
        if type(self.pixel_count) is not int or self.pixel_count < 1:
            raise DomainValidationError("component pixel count must be positive")
        _validate_ids(self.node_ids, "component node")
        _validate_ids(self.edge_ids, "component edge")
        if type(self.has_loop) is not bool:
            raise DomainValidationError("component loop flag must be boolean")


@dataclass(frozen=True, slots=True)
class SkeletonGraphResult:
    """Complete deterministic topology plus FS-014 source provenance."""

    source: SkeletonizationResult
    nodes: tuple[SkeletonGraphNode, ...]
    edges: tuple[SkeletonGraphEdge, ...]
    components: tuple[SkeletonGraphComponent, ...]
    adjacency_policy: str = SKELETON_GRAPH_ADJACENCY_POLICY
    builder: str = SKELETON_GRAPH_BUILDER
    schema: str = SKELETON_GRAPH_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.source, SkeletonizationResult):
            raise DomainValidationError("skeleton graph requires a typed skeletonization source")
        if self.source.skeleton_pixel_count > MAX_SKELETON_GRAPH_FOREGROUND_PIXELS:
            raise DomainValidationError("skeleton graph source exceeds the foreground budget")
        if self.adjacency_policy != SKELETON_GRAPH_ADJACENCY_POLICY:
            raise DomainValidationError("unsupported skeleton graph adjacency policy")
        if self.builder != SKELETON_GRAPH_BUILDER or self.schema != SKELETON_GRAPH_SCHEMA:
            raise DomainValidationError("unsupported skeleton graph provenance")
        if not isinstance(self.nodes, tuple) or any(
            not isinstance(node, SkeletonGraphNode) for node in self.nodes
        ):
            raise DomainValidationError("graph nodes must be an immutable typed tuple")
        if not isinstance(self.edges, tuple) or any(
            not isinstance(edge, SkeletonGraphEdge) for edge in self.edges
        ):
            raise DomainValidationError("graph edges must be an immutable typed tuple")
        if not isinstance(self.components, tuple) or any(
            not isinstance(component, SkeletonGraphComponent) for component in self.components
        ):
            raise DomainValidationError("graph components must be an immutable typed tuple")
        self._validate_topology()

    @property
    def foreground_pixel_count(self) -> int:
        return self.source.skeleton_pixel_count

    @property
    def endpoint_count(self) -> int:
        return sum(node.kind is SkeletonNodeKind.ENDPOINT for node in self.nodes)

    @property
    def junction_count(self) -> int:
        return sum(node.kind is SkeletonNodeKind.JUNCTION_REGION for node in self.nodes)

    @property
    def loop_count(self) -> int:
        return sum(component.has_loop for component in self.components)

    @property
    def is_empty(self) -> bool:
        return self.foreground_pixel_count == 0

    def to_dict(self) -> dict[str, object]:
        """Return canonical storage data; sequence order is not a route."""
        skeleton = self.source.skeleton
        return {
            "schema": self.schema,
            "builder": self.builder,
            "adjacency_policy": self.adjacency_policy,
            "width": skeleton.width,
            "height": skeleton.height,
            "foreground_pixels": self.foreground_pixel_count,
            "skeleton_algorithm": self.source.algorithm.value,
            "skeleton_backend": self.source.backend,
            "nodes": [
                {
                    "id": node.id,
                    "component_id": node.component_id,
                    "kind": node.kind.value,
                    "incidence_degree": node.incidence_degree,
                    "owned_pixels": [_point_dict(point) for point in node.owned_pixels],
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "component_id": edge.component_id,
                    "start_node_id": edge.start_node_id,
                    "end_node_id": edge.end_node_id,
                    "start_contact": _point_dict(edge.start_contact),
                    "end_contact": _point_dict(edge.end_contact),
                    "interior_pixels": [_point_dict(point) for point in edge.interior_pixels],
                }
                for edge in self.edges
            ],
            "components": [
                {
                    "id": component.id,
                    "pixel_count": component.pixel_count,
                    "node_ids": list(component.node_ids),
                    "edge_ids": list(component.edge_ids),
                    "has_loop": component.has_loop,
                }
                for component in self.components
            ],
        }

    def to_json_bytes(self) -> bytes:
        """Serialize byte-stably and enforce the diagnostic artifact budget."""
        payload = json.dumps(
            self.to_dict(), ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        if len(payload) + 1 > MAX_SKELETON_GRAPH_JSON_BYTES:
            raise SkeletonGraphError(
                SkeletonGraphFailureCode.RESOURCE_LIMIT,
                "skeleton graph JSON exceeds the diagnostic budget",
            )
        return payload + b"\n"

    def _validate_topology(self) -> None:
        if tuple(node.id for node in self.nodes) != tuple(range(len(self.nodes))):
            raise DomainValidationError("graph node IDs must be canonical and contiguous")
        if tuple(edge.id for edge in self.edges) != tuple(range(len(self.edges))):
            raise DomainValidationError("graph edge IDs must be canonical and contiguous")
        if tuple(component.id for component in self.components) != tuple(
            range(len(self.components))
        ):
            raise DomainValidationError("graph component IDs must be canonical and contiguous")
        if len(self.nodes) + len(self.edges) > MAX_SKELETON_GRAPH_RECORDS:
            raise DomainValidationError("graph exceeds the node and edge record budget")
        if self.is_empty:
            if self.nodes or self.edges or self.components:
                raise DomainValidationError("empty skeleton must produce an empty graph")
            return
        if not self.components:
            raise DomainValidationError("non-empty skeleton requires explicit components")

        node_by_id = {node.id: node for node in self.nodes}
        edge_by_id = {edge.id: edge for edge in self.edges}
        nodes_by_component: list[list[SkeletonGraphNode]] = [
            [] for _ in self.components
        ]
        edges_by_component: list[list[SkeletonGraphEdge]] = [
            [] for _ in self.components
        ]
        for node in self.nodes:
            if node.component_id >= len(nodes_by_component):
                raise DomainValidationError("node references an unknown component")
            nodes_by_component[node.component_id].append(node)
        for edge in self.edges:
            if edge.component_id >= len(edges_by_component):
                raise DomainValidationError("edge references an unknown component")
            edges_by_component[edge.component_id].append(edge)
        owned: set[PixelPoint] = set()
        for node in self.nodes:
            _add_disjoint(owned, node.owned_pixels)
        for edge in self.edges:
            _add_disjoint(owned, edge.interior_pixels)
            start = node_by_id.get(edge.start_node_id)
            end = node_by_id.get(edge.end_node_id)
            if start is None or end is None:
                raise DomainValidationError("edge references an unknown node")
            if (
                edge.start_contact not in start.owned_pixels
                or edge.end_contact not in end.owned_pixels
            ):
                raise DomainValidationError("edge contact must belong to its referenced node")
            if start.component_id != edge.component_id or end.component_id != edge.component_id:
                raise DomainValidationError("edge cannot cross graph components")

        skeleton = self.source.skeleton
        expected = {
            PixelPoint(column=index % skeleton.width, row=index // skeleton.width)
            for index, value in enumerate(skeleton.pixels)
            if value == 255
        }
        if owned != expected:
            raise DomainValidationError("node and edge ownership must exactly partition skeleton")

        adjacency = {point: _policy_neighbors(point, expected) for point in expected}
        actual_component_pixels: list[frozenset[PixelPoint]] = []

        for component in self.components:
            component_nodes = tuple(node.id for node in nodes_by_component[component.id])
            component_edges = tuple(edge.id for edge in edges_by_component[component.id])
            if component.node_ids != component_nodes or component.edge_ids != component_edges:
                raise DomainValidationError("component membership must match graph records")
            pixels = sum(len(node_by_id[node_id].owned_pixels) for node_id in component.node_ids)
            pixels += sum(
                len(edge_by_id[edge_id].interior_pixels)
                for edge_id in component.edge_ids
            )
            if pixels != component.pixel_count:
                raise DomainValidationError("component pixel count must match ownership")
            component_pixels = frozenset(
                point
                for node_id in component.node_ids
                for point in node_by_id[node_id].owned_pixels
            ).union(
                point
                for edge_id in component.edge_ids
                for point in edge_by_id[edge_id].interior_pixels
            )
            actual_component_pixels.append(component_pixels)
            undirected_links = sum(len(adjacency[point]) for point in component_pixels) // 2
            expected_loop = undirected_links - len(component_pixels) + 1 > 0
            if component.has_loop is not expected_loop:
                raise DomainValidationError("component loop flag must match cycle rank")

        expected_components = _connected_components(expected, adjacency)
        if tuple(actual_component_pixels) != expected_components:
            raise DomainValidationError("graph components must match skeleton connectivity")
        self._validate_roles_and_edges(adjacency, node_by_id)

    def _validate_roles_and_edges(
        self,
        adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
        node_by_id: dict[int, SkeletonGraphNode],
    ) -> None:
        incidence = [0] * len(self.nodes)
        for edge in self.edges:
            incidence[edge.start_node_id] += 1
            incidence[edge.end_node_id] += 1
            path = (edge.start_contact, *edge.interior_pixels, edge.end_contact)
            if any(
                right not in adjacency[left]
                for left, right in pairwise(path)
            ):
                raise DomainValidationError("edge chain must follow the fixed adjacency policy")
            if any(len(adjacency[point]) != 2 for point in edge.interior_pixels):
                raise DomainValidationError("edge interiors must contain only degree-two pixels")
        for node in self.nodes:
            if node.incidence_degree != incidence[node.id]:
                raise DomainValidationError("node incidence must match referenced graph edges")
            raw_degrees = tuple(len(adjacency[point]) for point in node.owned_pixels)
            if node.kind is SkeletonNodeKind.ENDPOINT and raw_degrees != (1,):
                raise DomainValidationError("endpoint node must own one raw degree-one pixel")
            if node.kind is SkeletonNodeKind.ISOLATED and raw_degrees != (0,):
                raise DomainValidationError("isolated node must own one raw degree-zero pixel")
            if node.kind is SkeletonNodeKind.LOOP_ANCHOR and raw_degrees != (2,):
                raise DomainValidationError("loop anchor must own one raw degree-two pixel")
            if node.kind is SkeletonNodeKind.JUNCTION_REGION:
                if any(degree < 3 for degree in raw_degrees):
                    raise DomainValidationError("junction region must own only raw junction pixels")
                if not _is_connected(frozenset(node.owned_pixels), adjacency):
                    raise DomainValidationError("junction region pixels must be connected")


def _point_dict(point: PixelPoint) -> dict[str, int]:
    return {"column": point.column, "row": point.row}


def _row_major_key(point: PixelPoint) -> tuple[int, int]:
    return point.row, point.column


def _validate_identifier(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise DomainValidationError(f"{label} identifier must be a non-negative integer")


def _validate_ids(values: tuple[int, ...], label: str) -> None:
    if not isinstance(values, tuple) or any(
        type(value) is not int or value < 0 for value in values
    ):
        raise DomainValidationError(f"{label} identifiers must be an immutable integer tuple")
    if tuple(sorted(values)) != values or len(set(values)) != len(values):
        raise DomainValidationError(f"{label} identifiers must be sorted and unique")


def _validate_points(
    values: tuple[PixelPoint, ...],
    label: str,
    *,
    allow_empty: bool,
    require_row_major: bool,
) -> None:
    if not isinstance(values, tuple) or any(not isinstance(point, PixelPoint) for point in values):
        raise DomainValidationError(f"{label} pixels must be an immutable PixelPoint tuple")
    if not allow_empty and not values:
        raise DomainValidationError(f"{label} pixels cannot be empty")
    if len(set(values)) != len(values):
        raise DomainValidationError(f"{label} pixels must be unique")
    if require_row_major and tuple(sorted(values, key=_row_major_key)) != values:
        raise DomainValidationError(f"{label} pixels must be row-major")


def _add_disjoint(destination: set[PixelPoint], values: tuple[PixelPoint, ...]) -> None:
    if destination.intersection(values):
        raise DomainValidationError("graph pixel ownership must be disjoint")
    destination.update(values)


def _policy_neighbors(
    point: PixelPoint,
    points: set[PixelPoint],
) -> tuple[PixelPoint, ...]:
    neighbors: list[PixelPoint] = []
    for row_delta, column_delta in ((-1, 0), (0, -1), (0, 1), (1, 0)):
        candidate = _offset(point, row_delta, column_delta)
        if candidate is not None and candidate in points:
            neighbors.append(candidate)
    for row_delta, column_delta in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        candidate = _offset(point, row_delta, column_delta)
        if candidate is None or candidate not in points:
            continue
        horizontal = _offset(point, 0, column_delta)
        vertical = _offset(point, row_delta, 0)
        if horizontal not in points and vertical not in points:
            neighbors.append(candidate)
    return tuple(sorted(neighbors, key=_row_major_key))


def _connected_components(
    points: set[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
) -> tuple[frozenset[PixelPoint], ...]:
    visited: set[PixelPoint] = set()
    components: list[frozenset[PixelPoint]] = []
    for root in sorted(points, key=_row_major_key):
        if root in visited:
            continue
        stack = [root]
        visited.add(root)
        component = {root}
        while stack:
            for neighbor in adjacency[stack.pop()]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(frozenset(component))
    return tuple(components)


def _is_connected(
    points: frozenset[PixelPoint],
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
) -> bool:
    if not points:
        return False
    root = min(points, key=_row_major_key)
    reached = {root}
    stack = [root]
    while stack:
        for neighbor in adjacency[stack.pop()]:
            if neighbor in points and neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    return reached == set(points)


def _offset(point: PixelPoint, row_delta: int, column_delta: int) -> PixelPoint | None:
    row = point.row + row_delta
    column = point.column + column_delta
    if row < 0 or column < 0:
        return None
    return PixelPoint(column=column, row=row)
