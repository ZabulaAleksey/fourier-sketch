"""FS-017 local image to forced-route Fourier composition."""

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from time import perf_counter

from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.imaging import ImagePreprocessingOptions
from fourier_sketch.math import resample_curve_by_arc_length
from fourier_sketch.routing import (
    DEFAULT_MAX_OPTIMIZATION_EXPANSIONS,
    ForcedRouteAlgorithm,
    ForcedRouteResult,
    ForcedRouteStatus,
    build_forced_route,
)

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


@dataclass(frozen=True, slots=True)
class ForcedRouteOptimizationComparison:
    """One immutable graph routed through baseline and selected improved policy."""

    skeleton_graph: LocalSkeletonGraphResult
    baseline: LocalForcedRouteResult
    improved: LocalForcedRouteResult
    baseline_routing_seconds: float
    improved_routing_seconds: float
    optimization_budget: int

    def __post_init__(self) -> None:
        if not isinstance(self.skeleton_graph, LocalSkeletonGraphResult):
            raise DomainValidationError("route comparison requires a local skeleton graph")
        if not isinstance(self.baseline, LocalForcedRouteResult) or not isinstance(
            self.improved, LocalForcedRouteResult
        ):
            raise DomainValidationError("route comparison requires typed route results")
        if (
            self.baseline.skeleton_graph != self.skeleton_graph
            or self.improved.skeleton_graph != self.skeleton_graph
            or self.baseline.routing.algorithm
            is not ForcedRouteAlgorithm.BASELINE_TREE_T_JOIN_V1
            or self.improved.routing.algorithm
            is not ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1
        ):
            raise DomainValidationError("route comparison provenance is inconsistent")
        timings = (self.baseline_routing_seconds, self.improved_routing_seconds)
        if any(
            type(value) is not float or not isfinite(value) or value < 0.0
            for value in timings
        ):
            raise DomainValidationError(
                "route comparison timings must be finite non-negative floats"
            )
        if type(self.optimization_budget) is not int or self.optimization_budget < 1:
            raise DomainValidationError("route comparison budget is invalid")

    @property
    def added_length_delta(self) -> float | None:
        baseline = self.baseline.routing.metrics
        improved = self.improved.routing.metrics
        if baseline is None or improved is None:
            return None
        return improved.added_length - baseline.added_length


def build_local_forced_route(
    path: str | Path,
    preprocessing: ImagePreprocessingOptions | None = None,
    *,
    sample_count: int = DEFAULT_ROUTE_SAMPLES,
    harmonic_count: int = DEFAULT_ROUTE_HARMONICS,
    route_algorithm: ForcedRouteAlgorithm = ForcedRouteAlgorithm.BASELINE_TREE_T_JOIN_V1,
    max_optimization_expansions: int = DEFAULT_MAX_OPTIMIZATION_EXPANSIONS,
    cancellation_check: Callable[[], bool] | None = None,
) -> LocalForcedRouteResult:
    if type(sample_count) is not int or not 2 <= sample_count <= 4096:
        raise DomainValidationError("route sample_count must be between 2 and 4096")
    if type(harmonic_count) is not int or not 1 <= harmonic_count <= sample_count:
        raise DomainValidationError("route harmonic_count must be between 1 and sample_count")
    graph = build_local_skeleton_graph(
        path, preprocessing, cancellation_check=cancellation_check
    )
    return _build_from_graph(
        graph,
        sample_count=sample_count,
        harmonic_count=harmonic_count,
        route_algorithm=route_algorithm,
        max_optimization_expansions=max_optimization_expansions,
        cancellation_check=cancellation_check,
    )


def compare_local_forced_routes(
    path: str | Path,
    preprocessing: ImagePreprocessingOptions | None = None,
    *,
    sample_count: int = DEFAULT_ROUTE_SAMPLES,
    harmonic_count: int = DEFAULT_ROUTE_HARMONICS,
    max_optimization_expansions: int = DEFAULT_MAX_OPTIMIZATION_EXPANSIONS,
    cancellation_check: Callable[[], bool] | None = None,
) -> ForcedRouteOptimizationComparison:
    """Compare measured routing work over one graph without silent fallback."""

    if type(sample_count) is not int or not 2 <= sample_count <= 4096:
        raise DomainValidationError("route sample_count must be between 2 and 4096")
    if type(harmonic_count) is not int or not 1 <= harmonic_count <= sample_count:
        raise DomainValidationError("route harmonic_count must be between 1 and sample_count")
    graph = build_local_skeleton_graph(
        path, preprocessing, cancellation_check=cancellation_check
    )
    started = perf_counter()
    baseline_routing = build_forced_route(
        graph.graph,
        algorithm=ForcedRouteAlgorithm.BASELINE_TREE_T_JOIN_V1,
        max_optimization_expansions=max_optimization_expansions,
        cancellation_check=cancellation_check,
    )
    baseline_seconds = perf_counter() - started
    started = perf_counter()
    improved_routing = build_forced_route(
        graph.graph,
        algorithm=ForcedRouteAlgorithm.GREEDY_SHORTEST_ODD_PAIRING_V1,
        max_optimization_expansions=max_optimization_expansions,
        cancellation_check=cancellation_check,
    )
    improved_seconds = perf_counter() - started
    baseline = _materialize_route(graph, baseline_routing, sample_count, harmonic_count)
    improved = _materialize_route(graph, improved_routing, sample_count, harmonic_count)
    return ForcedRouteOptimizationComparison(
        graph,
        baseline,
        improved,
        float(baseline_seconds),
        float(improved_seconds),
        max_optimization_expansions,
    )


def _build_from_graph(
    graph: LocalSkeletonGraphResult,
    *,
    sample_count: int,
    harmonic_count: int,
    route_algorithm: ForcedRouteAlgorithm,
    max_optimization_expansions: int,
    cancellation_check: Callable[[], bool] | None,
) -> LocalForcedRouteResult:
    routing = build_forced_route(
        graph.graph,
        algorithm=route_algorithm,
        max_optimization_expansions=max_optimization_expansions,
        cancellation_check=cancellation_check,
    )
    return _materialize_route(graph, routing, sample_count, harmonic_count)


def _materialize_route(
    graph: LocalSkeletonGraphResult,
    routing: ForcedRouteResult,
    sample_count: int,
    harmonic_count: int,
) -> LocalForcedRouteResult:
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
