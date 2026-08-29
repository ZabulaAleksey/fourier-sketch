"""FS-016 conversion of simple skeleton graph components to curves."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from fourier_sketch.domain import Curve, DomainValidationError, PiecewiseCurve, Point2D
from fourier_sketch.imaging.contour_model import PixelPoint
from fourier_sketch.imaging.skeleton_graph_model import SkeletonGraphResult, SkeletonNodeKind

from .raster_coordinates import COORDINATE_TRANSFORM_ID, RasterCoordinateTransform


class PiecewiseBuildStatus(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    UNSUPPORTED = "unsupported"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class PiecewiseSegmentProvenance:
    component_id: int
    node_ids: tuple[int, ...]
    edge_ids: tuple[int, ...]
    raster_pixels: tuple[PixelPoint, ...]
    topology: str
    coordinate_transform: str
    scale: float

    def __post_init__(self) -> None:
        if type(self.component_id) is not int or self.component_id < 0:
            raise DomainValidationError("piecewise component identifier must be non-negative")
        for values, label in ((self.node_ids, "node"), (self.edge_ids, "edge")):
            if (
                not isinstance(values, tuple)
                or any(type(value) is not int or value < 0 for value in values)
                or tuple(sorted(values)) != values
                or len(set(values)) != len(values)
            ):
                raise DomainValidationError(
                    f"piecewise {label} identifiers must be sorted and unique"
                )
        if (
            not isinstance(self.raster_pixels, tuple)
            or not self.raster_pixels
            or any(not isinstance(pixel, PixelPoint) for pixel in self.raster_pixels)
            or len(set(self.raster_pixels)) != len(self.raster_pixels)
        ):
            raise DomainValidationError("piecewise raster provenance must be unique and non-empty")
        if self.topology not in {"path", "loop", "isolated"}:
            raise DomainValidationError("piecewise topology must be explicit")
        if self.coordinate_transform != COORDINATE_TRANSFORM_ID:
            raise DomainValidationError("piecewise coordinate transform is unsupported")
        if type(self.scale) is not float or not isfinite(self.scale) or self.scale <= 0.0:
            raise DomainValidationError("piecewise coordinate scale must be finite and positive")


@dataclass(frozen=True, slots=True)
class PiecewiseSegment:
    curve: Curve
    provenance: PiecewiseSegmentProvenance
    boundary_after: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.curve, Curve) or not isinstance(
            self.provenance, PiecewiseSegmentProvenance
        ):
            raise DomainValidationError("piecewise segment requires typed curve and provenance")
        if type(self.boundary_after) is not bool:
            raise DomainValidationError("piecewise segment boundary flag must be boolean")


@dataclass(frozen=True, slots=True)
class PiecewiseComponentResult:
    graph: SkeletonGraphResult
    status: PiecewiseBuildStatus
    piecewise: PiecewiseCurve | None = None
    segments: tuple[PiecewiseSegment, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.graph, SkeletonGraphResult):
            raise DomainValidationError("piecewise result requires source graph provenance")
        if not isinstance(self.status, PiecewiseBuildStatus):
            raise DomainValidationError("piecewise result status must be explicit")
        if not isinstance(self.segments, tuple) or any(
            not isinstance(segment, PiecewiseSegment) for segment in self.segments
        ):
            raise DomainValidationError(
                "piecewise result segments must be an immutable typed tuple"
            )
        if self.status is PiecewiseBuildStatus.READY:
            if self.piecewise is None or not self.segments or self.reason is not None:
                raise DomainValidationError("ready result requires piecewise segments")
            if self.piecewise.segments != tuple(segment.curve for segment in self.segments):
                raise DomainValidationError("piecewise segments must match the published curve")
            if tuple(segment.provenance.component_id for segment in self.segments) != tuple(
                component.id for component in self.graph.components
            ):
                raise DomainValidationError("piecewise segments must match all graph components")
            node_by_id = {node.id: node for node in self.graph.nodes}
            edge_by_id = {edge.id: edge for edge in self.graph.edges}
            transform = RasterCoordinateTransform.for_dimensions(
                self.graph.source.source_dimensions
            )
            for segment, component in zip(
                self.segments, self.graph.components, strict=True
            ):
                if (
                    segment.provenance.node_ids != component.node_ids
                    or segment.provenance.edge_ids != component.edge_ids
                    or len(segment.provenance.raster_pixels) != component.pixel_count
                ):
                    raise DomainValidationError(
                        "piecewise segment provenance must match its graph component"
                    )
                expected_pixels = {
                    pixel
                    for node_id in component.node_ids
                    for pixel in node_by_id[node_id].owned_pixels
                }.union(
                    pixel
                    for edge_id in component.edge_ids
                    for pixel in edge_by_id[edge_id].interior_pixels
                )
                if set(segment.provenance.raster_pixels) != expected_pixels:
                    raise DomainValidationError(
                        "piecewise raster provenance must exactly cover its graph component"
                    )
                if not component.edge_ids:
                    expected_order = node_by_id[component.node_ids[0]].owned_pixels
                else:
                    edge = edge_by_id[component.edge_ids[0]]
                    expected_order = (
                        (edge.start_contact, *edge.interior_pixels)
                        if component.has_loop
                        else (edge.start_contact, *edge.interior_pixels, edge.end_contact)
                    )
                if segment.provenance.raster_pixels != expected_order:
                    raise DomainValidationError(
                        "piecewise raster provenance must follow canonical graph order"
                    )
                if segment.provenance.scale != transform.scale:
                    raise DomainValidationError(
                        "piecewise provenance scale must match source dimensions"
                    )
                if segment.curve.points != transform.points(
                    segment.provenance.raster_pixels
                ):
                    raise DomainValidationError(
                        "piecewise curve coordinates must match raster provenance"
                    )
                expected_topology = (
                    "isolated"
                    if not component.edge_ids
                    else "loop"
                    if component.has_loop
                    else "path"
                )
                if (
                    segment.provenance.topology != expected_topology
                    or segment.curve.closed != (expected_topology == "loop")
                ):
                    raise DomainValidationError(
                        "piecewise topology must match graph component semantics"
                    )
            expected_boundaries = tuple(
                index < len(self.segments) - 1 for index in range(len(self.segments))
            )
            if tuple(segment.boundary_after for segment in self.segments) != expected_boundaries:
                raise DomainValidationError(
                    "piecewise boundaries must separate consecutive segments"
                )
        elif (
            self.piecewise is not None
            or self.segments
            or not isinstance(self.reason, str)
            or not self.reason
        ):
            raise DomainValidationError(
                "non-ready result requires only a stable reason without partial curves"
            )


def build_piecewise_components(
    graph: SkeletonGraphResult,
    *,
    cancellation_check: Callable[[], bool] | None = None,
) -> PiecewiseComponentResult:
    """Convert only independently representable graph components, all-or-nothing."""
    if not isinstance(graph, SkeletonGraphResult):
        raise DomainValidationError("piecewise conversion requires a skeleton graph")
    if graph.is_empty:
        return PiecewiseComponentResult(graph, PiecewiseBuildStatus.EMPTY, reason="empty_graph")
    transform = RasterCoordinateTransform.for_dimensions(graph.source.source_dimensions)
    nodes = {node.id: node for node in graph.nodes}
    edges = {edge.id: edge for edge in graph.edges}
    converted: list[PiecewiseSegment] = []
    for component in graph.components:
        if cancellation_check is not None and cancellation_check():
            return PiecewiseComponentResult(
                graph, PiecewiseBuildStatus.CANCELLED, reason="cancelled"
            )
        component_nodes = [nodes[i] for i in component.node_ids]
        component_edges = [edges[i] for i in component.edge_ids]
        if len(component_nodes) == 1 and component_nodes[0].kind is SkeletonNodeKind.ISOLATED:
            pixels = component_nodes[0].owned_pixels
            topology = "isolated"
            domain_points = _transform_points(transform, pixels, cancellation_check)
            if domain_points is None:
                return PiecewiseComponentResult(
                    graph, PiecewiseBuildStatus.CANCELLED, reason="cancelled"
                )
            curve = Curve(domain_points)
            node_ids, edge_ids = component.node_ids, component.edge_ids
        elif (
            component.has_loop
            and len(component_nodes) == 1
            and len(component_edges) == 1
            and component_edges[0].is_self_loop
        ):
            edge = component_edges[0]
            pixels = (edge.start_contact, *edge.interior_pixels)
            topology = "loop"
            domain_points = _transform_points(transform, pixels, cancellation_check)
            if domain_points is None:
                return PiecewiseComponentResult(
                    graph, PiecewiseBuildStatus.CANCELLED, reason="cancelled"
                )
            curve = Curve(domain_points, closed=True)
            node_ids, edge_ids = component.node_ids, component.edge_ids
        elif not component.has_loop and len(component_nodes) == 2 and len(component_edges) == 1:
            edge = component_edges[0]
            pixels = (edge.start_contact, *edge.interior_pixels, edge.end_contact)
            topology = "path"
            domain_points = _transform_points(transform, pixels, cancellation_check)
            if domain_points is None:
                return PiecewiseComponentResult(
                    graph, PiecewiseBuildStatus.CANCELLED, reason="cancelled"
                )
            curve = Curve(domain_points)
            node_ids, edge_ids = component.node_ids, component.edge_ids
        else:
            return PiecewiseComponentResult(
                graph, PiecewiseBuildStatus.UNSUPPORTED, reason="branched_or_complex"
            )
        provenance = PiecewiseSegmentProvenance(
            component.id,
            node_ids,
            edge_ids,
            pixels,
            topology,
            COORDINATE_TRANSFORM_ID,
            transform.scale,
        )
        converted.append(PiecewiseSegment(curve, provenance, True))
    converted[-1] = PiecewiseSegment(converted[-1].curve, converted[-1].provenance, False)
    piecewise = PiecewiseCurve(tuple(segment.curve for segment in converted))
    return PiecewiseComponentResult(graph, PiecewiseBuildStatus.READY, piecewise, tuple(converted))


def _transform_points(
    transform: RasterCoordinateTransform,
    pixels: tuple[PixelPoint, ...],
    cancellation_check: Callable[[], bool] | None,
) -> tuple[Point2D, ...] | None:
    points: list[Point2D] = []
    for index, pixel in enumerate(pixels):
        if index % 4096 == 0 and cancellation_check is not None and cancellation_check():
            return None
        points.append(transform.point(pixel))
    return tuple(points)
