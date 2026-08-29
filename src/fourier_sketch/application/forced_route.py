"""FS-017 local image to forced-route Fourier composition."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.math import resample_curve_by_arc_length
from fourier_sketch.routing import ForcedRouteResult, ForcedRouteStatus, build_forced_route

from .diagnostic_epicycles import EpicycleTimeline
from .freehand import build_freehand_timeline
from .skeleton_graph import LocalSkeletonGraphResult, build_local_skeleton_graph

DEFAULT_ROUTE_SAMPLES = 256
DEFAULT_ROUTE_HARMONICS = 25


@dataclass(frozen=True, slots=True)
class LocalForcedRouteResult:
    skeleton_graph: LocalSkeletonGraphResult
    routing: ForcedRouteResult
    sampled_curve: Curve | None = None
    timeline: EpicycleTimeline | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.skeleton_graph, LocalSkeletonGraphResult) or not isinstance(
            self.routing, ForcedRouteResult
        ):
            raise DomainValidationError("local forced route requires typed pipeline values")
        if self.routing.graph != self.skeleton_graph.graph:
            raise DomainValidationError("forced route must retain its local graph")
        if self.routing.status is ForcedRouteStatus.READY:
            if not isinstance(self.sampled_curve, Curve) or not isinstance(
                self.timeline, EpicycleTimeline
            ):
                raise DomainValidationError("ready forced route requires sampled timeline")
            if self.timeline.snapshot().original != self.sampled_curve:
                raise DomainValidationError("forced route timeline must use the sampled route")
        elif self.sampled_curve is not None or self.timeline is not None:
            raise DomainValidationError("non-ready forced route cannot publish a timeline")


def build_local_forced_route(
    path: str | Path,
    preprocessing: ImagePreprocessingOptions | None = None,
    *,
    sample_count: int = DEFAULT_ROUTE_SAMPLES,
    harmonic_count: int = DEFAULT_ROUTE_HARMONICS,
    cancellation_check: Callable[[], bool] | None = None,
) -> LocalForcedRouteResult:
    if type(sample_count) is not int or not 2 <= sample_count <= 4096:
        raise DomainValidationError("route sample_count must be between 2 and 4096")
    if type(harmonic_count) is not int or not 1 <= harmonic_count <= sample_count:
        raise DomainValidationError("route harmonic_count must be between 1 and sample_count")
    graph = build_local_skeleton_graph(
        path, preprocessing, cancellation_check=cancellation_check
    )
    routing = build_forced_route(graph.graph, cancellation_check=cancellation_check)
    if routing.status is not ForcedRouteStatus.READY:
        return LocalForcedRouteResult(graph, routing)
    assert routing.curve is not None
    if routing.curve.sample_count == 1:
        sampled = routing.curve
        harmonics = 1
    else:
        sampled = resample_curve_by_arc_length(routing.curve, sample_count)
        harmonics = harmonic_count
    timeline = build_freehand_timeline(sampled, harmonic_count=harmonics)
    return LocalForcedRouteResult(graph, routing, sampled, timeline)
