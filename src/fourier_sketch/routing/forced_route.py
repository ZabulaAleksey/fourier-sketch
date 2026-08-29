"""Bounded deterministic STRICT_SINGLE_CURVE routing (FS-017)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from math import hypot, isclose, isfinite

from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.imaging import PixelPoint, SkeletonGraphResult, SkeletonNodeKind, raw_adjacency

from .raster_coordinates import RasterCoordinateTransform

MAX_FORCED_ROUTE_COMPONENTS = 1024
MAX_FORCED_ROUTE_SAMPLES = 262_144
_CANCELLATION_BATCH = 4096


class ForcedRouteStatus(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    CANCELLED = "cancelled"
    RESOURCE_LIMIT = "resource_limit"
    MALFORMED_TOPOLOGY = "malformed_topology"


class RouteStepKind(StrEnum):
    ORIGINAL = "original"
    DUPLICATED = "duplicated"
    BRIDGE = "bridge"


@dataclass(frozen=True, slots=True)
class ForcedRouteStep:
    start: PixelPoint
    end: PixelPoint
    kind: RouteStepKind
    from_component_id: int
    to_component_id: int
    length: float
    source_node_id: int | None = None
    source_edge_id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.start, PixelPoint) or not isinstance(self.end, PixelPoint):
            raise DomainValidationError("route step endpoints must be raster pixels")
        if not isinstance(self.kind, RouteStepKind):
            raise DomainValidationError("route step kind must be explicit")
        if any(
            type(value) is not int or value < 0
            for value in (self.from_component_id, self.to_component_id)
        ):
            raise DomainValidationError("route step component IDs must be non-negative")
        if type(self.length) is not float or self.length < 0.0:
            raise DomainValidationError("route step length must be a non-negative float")
        sources = int(self.source_node_id is not None) + int(self.source_edge_id is not None)
        if self.kind is RouteStepKind.BRIDGE:
            if sources or self.start == self.end:
                raise DomainValidationError("bridge step provenance is invalid")
        elif sources != 1 or self.from_component_id != self.to_component_id:
            raise DomainValidationError("skeleton step requires exactly one source owner")


@dataclass(frozen=True, slots=True)
class ForcedRouteMetrics:
    original_steps: int
    duplicated_steps: int
    bridge_steps: int
    original_length: float
    duplicated_length: float
    bridge_length: float
    covered_pixels: int
    covered_links: int

    def __post_init__(self) -> None:
        counts = (
            self.original_steps,
            self.duplicated_steps,
            self.bridge_steps,
            self.covered_pixels,
            self.covered_links,
        )
        lengths = (self.original_length, self.duplicated_length, self.bridge_length)
        if any(type(value) is not int or value < 0 for value in counts):
            raise DomainValidationError("forced route metric counts must be non-negative integers")
        if any(
            type(value) is not float or not isfinite(value) or value < 0.0
            for value in lengths
        ):
            raise DomainValidationError(
                "forced route metric lengths must be finite and non-negative"
            )

    @property
    def added_length(self) -> float:
        return self.duplicated_length + self.bridge_length

    @property
    def total_length(self) -> float:
        return self.original_length + self.added_length


@dataclass(frozen=True, slots=True)
class ForcedRouteResult:
    graph: SkeletonGraphResult
    status: ForcedRouteStatus
    curve: Curve | None = None
    raster_points: tuple[PixelPoint, ...] = ()
    steps: tuple[ForcedRouteStep, ...] = ()
    component_order: tuple[int, ...] = ()
    metrics: ForcedRouteMetrics | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.graph, SkeletonGraphResult) or not isinstance(
            self.status, ForcedRouteStatus
        ):
            raise DomainValidationError("forced route result requires typed graph and status")
        if self.status is not ForcedRouteStatus.READY:
            if any(
                (self.curve, self.raster_points, self.steps, self.component_order, self.metrics)
            ):
                raise DomainValidationError("non-ready route cannot publish partial values")
            if not isinstance(self.reason, str) or not self.reason:
                raise DomainValidationError("non-ready route requires a stable reason")
            return
        if (
            not isinstance(self.curve, Curve)
            or not self.curve.closed
            or not isinstance(self.metrics, ForcedRouteMetrics)
            or self.reason is not None
        ):
            raise DomainValidationError("ready route requires a closed curve and metrics")
        if len(self.component_order) != len(self.graph.components) or set(
            self.component_order
        ) != set(range(len(self.graph.components))):
            raise DomainValidationError("route component order must cover every component")
        if len(self.raster_points) != self.curve.sample_count:
            raise DomainValidationError("route raster/domain samples must align")
        if self.steps:
            if len(self.steps) != len(self.raster_points):
                raise DomainValidationError("closed route requires one step per sample")
            for index, step in enumerate(self.steps):
                if step.start != self.raster_points[index] or step.end != self.raster_points[
                    (index + 1) % len(self.raster_points)
                ]:
                    raise DomainValidationError("route steps must form one cyclic sequence")


class _Abort(Exception):
    def __init__(self, status: ForcedRouteStatus, reason: str) -> None:
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _EdgeInstance:
    start: PixelPoint
    end: PixelPoint
    kind: RouteStepKind
    source_node_id: int | None
    source_edge_id: int | None


def build_forced_route(
    graph: SkeletonGraphResult,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> ForcedRouteResult:
    if not isinstance(graph, SkeletonGraphResult):
        raise DomainValidationError("forced route requires a typed skeleton graph")
    if cancellation_check is not None and cancellation_check():
        return ForcedRouteResult(graph, ForcedRouteStatus.CANCELLED, reason="cancelled")
    if graph.is_empty:
        return ForcedRouteResult(graph, ForcedRouteStatus.EMPTY, reason="empty_graph")
    if len(graph.components) > MAX_FORCED_ROUTE_COMPONENTS:
        return ForcedRouteResult(graph, ForcedRouteStatus.RESOURCE_LIMIT, reason="component_limit")
    try:
        transform = RasterCoordinateTransform.for_dimensions(graph.source.source_dimensions)
        ownership = _source_ownership(graph)
        component_routes = [
            _component_route(graph, component.id, ownership, cancellation_check)
            for component in graph.components
        ]
        ordered = _order_components(component_routes, transform)
        steps = _combine_routes(ordered, transform)
        raster_points = tuple(step.start for step in steps) if steps else component_routes[0][1]
        if len(raster_points) > MAX_FORCED_ROUTE_SAMPLES:
            raise _Abort(ForcedRouteStatus.RESOURCE_LIMIT, "sample_limit")
        return ForcedRouteResult(
            graph,
            ForcedRouteStatus.READY,
            Curve(transform.points(raster_points), closed=True),
            raster_points,
            steps,
            tuple(component_id for component_id, _points, _steps in ordered),
            _metrics(graph, steps),
        )
    except _Abort as error:
        return ForcedRouteResult(graph, error.status, reason=error.reason)
    except DomainValidationError:
        if cancellation_check is not None and cancellation_check():
            return ForcedRouteResult(graph, ForcedRouteStatus.CANCELLED, reason="cancelled")
        return ForcedRouteResult(
            graph, ForcedRouteStatus.MALFORMED_TOPOLOGY, reason="malformed_topology"
        )


def _component_route(
    graph: SkeletonGraphResult,
    component_id: int,
    ownership: dict[frozenset[PixelPoint], tuple[int | None, int | None]],
    cancellation_check: Callable[[], bool] | None,
) -> tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]]:
    component = graph.components[component_id]
    pixels = {
        pixel for node_id in component.node_ids for pixel in graph.nodes[node_id].owned_pixels
    }.union(
        pixel for edge_id in component.edge_ids for pixel in graph.edges[edge_id].interior_pixels
    )
    if len(pixels) == 1:
        return component_id, (next(iter(pixels)),), ()
    adjacency = raw_adjacency(pixels, cancellation_check=cancellation_check)
    original = [
        (left, right)
        for left in sorted(adjacency, key=_key)
        for right in adjacency[left]
        if _key(left) < _key(right)
    ]
    if len(original) > MAX_FORCED_ROUTE_SAMPLES:
        raise _Abort(ForcedRouteStatus.RESOURCE_LIMIT, "sample_limit")
    odd = tuple(point for point in sorted(pixels, key=_key) if len(adjacency[point]) % 2)
    instances: list[_EdgeInstance] = []
    for left, right in original:
        owner = ownership.get(frozenset((left, right)))
        if owner is None:
            raise _Abort(ForcedRouteStatus.MALFORMED_TOPOLOGY, "unowned_raw_link")
        instances.append(_EdgeInstance(left, right, RouteStepKind.ORIGINAL, *owner))
    if len(odd) > 2:
        parent, order = _spanning_tree(adjacency, min(pixels, key=_key), cancellation_check)
        parity = {point: int(point in odd) for point in pixels}
        owners = {
            frozenset((edge.start, edge.end)): (edge.source_node_id, edge.source_edge_id)
            for edge in instances
        }
        for index, point in enumerate(reversed(order[1:])):
            _check_cancelled(cancellation_check, index)
            parent_point = parent[point]
            if parity[point]:
                instances.append(
                    _EdgeInstance(
                        point,
                        parent_point,
                        RouteStepKind.DUPLICATED,
                        *owners[frozenset((point, parent_point))],
                    )
                )
                parity[parent_point] ^= 1
                parity[point] = 0
                if len(instances) > MAX_FORCED_ROUTE_SAMPLES:
                    raise _Abort(ForcedRouteStatus.RESOURCE_LIMIT, "sample_limit")
        if any(parity.values()):
            raise _Abort(ForcedRouteStatus.MALFORMED_TOPOLOGY, "invalid_t_join")
    start = odd[0] if len(odd) == 2 else min(pixels, key=_key)
    traversed = _hierholzer(instances, start, cancellation_check)
    transform = RasterCoordinateTransform.for_dimensions(graph.source.source_dimensions)
    steps = tuple(
        _make_step(instance, left, right, component_id, transform)
        for instance, left, right in traversed
    )
    points = (steps[0].start, *(step.end for step in steps))
    return component_id, points, steps


def _source_ownership(
    graph: SkeletonGraphResult,
) -> dict[frozenset[PixelPoint], tuple[int | None, int | None]]:
    ownership: dict[frozenset[PixelPoint], tuple[int | None, int | None]] = {}
    for edge in graph.edges:
        path = (edge.start_contact, *edge.interior_pixels, edge.end_contact)
        for left, right in pairwise(path):
            ownership[frozenset((left, right))] = (None, edge.id)
    for node in graph.nodes:
        if node.kind is SkeletonNodeKind.JUNCTION_REGION:
            adjacency = raw_adjacency(node.owned_pixels)
            for left in adjacency:
                for right in adjacency[left]:
                    ownership[frozenset((left, right))] = (node.id, None)
    return ownership


def _spanning_tree(
    adjacency: dict[PixelPoint, tuple[PixelPoint, ...]],
    root: PixelPoint,
    cancellation_check: Callable[[], bool] | None,
) -> tuple[dict[PixelPoint, PixelPoint], tuple[PixelPoint, ...]]:
    parent: dict[PixelPoint, PixelPoint] = {}
    visited = {root}
    order = [root]
    stack = [root]
    while stack:
        current = stack.pop()
        for neighbor in reversed(adjacency[current]):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                order.append(neighbor)
                stack.append(neighbor)
                _check_cancelled(cancellation_check, len(order))
    return parent, tuple(order)


def _hierholzer(
    instances: list[_EdgeInstance],
    start: PixelPoint,
    cancellation_check: Callable[[], bool] | None,
) -> tuple[tuple[_EdgeInstance, PixelPoint, PixelPoint], ...]:
    incidence: dict[PixelPoint, list[tuple[int, PixelPoint]]] = defaultdict(list)
    for identifier, edge in enumerate(instances):
        incidence[edge.start].append((identifier, edge.end))
        incidence[edge.end].append((identifier, edge.start))
    for values in incidence.values():
        values.sort(key=lambda item: (_key(item[1]), item[0]), reverse=True)
    used: set[int] = set()
    stack: list[tuple[PixelPoint, int | None, PixelPoint | None]] = [(start, None, None)]
    reverse_walk: list[tuple[_EdgeInstance, PixelPoint, PixelPoint]] = []
    while stack:
        point = stack[-1][0]
        while incidence[point] and incidence[point][-1][0] in used:
            incidence[point].pop()
        if not incidence[point]:
            vertex, incoming_id, previous = stack.pop()
            if incoming_id is not None and previous is not None:
                reverse_walk.append((instances[incoming_id], previous, vertex))
            continue
        identifier, neighbor = incidence[point].pop()
        used.add(identifier)
        stack.append((neighbor, identifier, point))
        _check_cancelled(cancellation_check, len(used))
    if len(used) != len(instances):
        raise _Abort(ForcedRouteStatus.MALFORMED_TOPOLOGY, "incomplete_euler_walk")
    return tuple(reversed(reverse_walk))


def _order_components(
    routes: list[tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]]],
    transform: RasterCoordinateTransform,
) -> list[tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]]]:
    ordered = [routes[0]]
    remaining = routes[1:]
    while remaining:
        current = ordered[-1][1][-1]
        candidates = []
        for route in remaining:
            orientations = (
                (route, _reverse_route(route))
                if route[1][0] != route[1][-1]
                else (route,)
            )
            for orientation_index, oriented in enumerate(orientations):
                candidates.append(
                    (
                        _distance(transform, current, oriented[1][0]),
                        oriented[0],
                        _key(oriented[1][0]),
                        orientation_index,
                        oriented,
                    )
                )
        selected = min(candidates, key=lambda item: item[:4])[4]
        ordered.append(selected)
        remaining = [route for route in remaining if route[0] != selected[0]]
    return ordered


def _reverse_route(
    route: tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]],
) -> tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]]:
    component_id, points, steps = route
    reversed_steps = tuple(
        ForcedRouteStep(
            step.end,
            step.start,
            step.kind,
            step.to_component_id,
            step.from_component_id,
            step.length,
            step.source_node_id,
            step.source_edge_id,
        )
        for step in reversed(steps)
    )
    return component_id, tuple(reversed(points)), reversed_steps


def _combine_routes(
    routes: list[tuple[int, tuple[PixelPoint, ...], tuple[ForcedRouteStep, ...]]],
    transform: RasterCoordinateTransform,
) -> tuple[ForcedRouteStep, ...]:
    combined: list[ForcedRouteStep] = []
    first = routes[0][1][0]
    current = first
    current_component = routes[0][0]
    for component_id, points, steps in routes:
        if current != points[0]:
            combined.append(_bridge(current, points[0], current_component, component_id, transform))
        combined.extend(steps)
        current = points[-1]
        current_component = component_id
    if current != first:
        combined.append(_bridge(current, first, current_component, routes[0][0], transform))
    return tuple(combined)


def _make_step(
    instance: _EdgeInstance,
    start: PixelPoint,
    end: PixelPoint,
    component: int,
    transform: RasterCoordinateTransform,
) -> ForcedRouteStep:
    return ForcedRouteStep(
        start,
        end,
        instance.kind,
        component,
        component,
        _distance(transform, start, end),
        instance.source_node_id,
        instance.source_edge_id,
    )


def _bridge(
    start: PixelPoint,
    end: PixelPoint,
    from_component: int,
    to_component: int,
    transform: RasterCoordinateTransform,
) -> ForcedRouteStep:
    return ForcedRouteStep(
        start,
        end,
        RouteStepKind.BRIDGE,
        from_component,
        to_component,
        _distance(transform, start, end),
    )


def _metrics(graph: SkeletonGraphResult, steps: tuple[ForcedRouteStep, ...]) -> ForcedRouteMetrics:
    by_kind = {kind: tuple(step for step in steps if step.kind is kind) for kind in RouteStepKind}
    metrics = ForcedRouteMetrics(
        len(by_kind[RouteStepKind.ORIGINAL]),
        len(by_kind[RouteStepKind.DUPLICATED]),
        len(by_kind[RouteStepKind.BRIDGE]),
        float(sum(step.length for step in by_kind[RouteStepKind.ORIGINAL])),
        float(sum(step.length for step in by_kind[RouteStepKind.DUPLICATED])),
        float(sum(step.length for step in by_kind[RouteStepKind.BRIDGE])),
        graph.foreground_pixel_count,
        len(by_kind[RouteStepKind.ORIGINAL]),
    )
    if not isclose(metrics.total_length, sum(step.length for step in steps), abs_tol=1e-12):
        raise DomainValidationError("forced route metrics do not match route steps")
    return metrics


def _distance(
    transform: RasterCoordinateTransform, left: PixelPoint, right: PixelPoint
) -> float:
    left_point = transform.point(left)
    right_point = transform.point(right)
    return float(hypot(right_point.x - left_point.x, right_point.y - left_point.y))


def _check_cancelled(
    cancellation_check: Callable[[], bool] | None, progress: int
) -> None:
    if (
        progress % _CANCELLATION_BATCH == 0
        and cancellation_check is not None
        and cancellation_check()
    ):
        raise _Abort(ForcedRouteStatus.CANCELLED, "cancelled")


def _key(point: PixelPoint) -> tuple[int, int]:
    return point.row, point.column


__all__ = [
    "MAX_FORCED_ROUTE_COMPONENTS",
    "MAX_FORCED_ROUTE_SAMPLES",
    "ForcedRouteMetrics",
    "ForcedRouteResult",
    "ForcedRouteStatus",
    "ForcedRouteStep",
    "RouteStepKind",
    "build_forced_route",
]
