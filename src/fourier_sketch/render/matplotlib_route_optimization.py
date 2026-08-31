"""FS-029 baseline/improved route comparison renderer."""

from io import BytesIO
from pathlib import Path
from typing import Any, cast

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from fourier_sketch.application.exporting import atomic_publish_bytes
from fourier_sketch.application.forced_route import (
    ForcedRouteOptimizationComparison,
    LocalForcedRouteResult,
)
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.presentation import Translator
from fourier_sketch.routing import ForcedRouteStatus, RouteStepKind

from .matplotlib_epicycles import draw_frame

_COLORS = {
    RouteStepKind.ORIGINAL: "#1565c0",
    RouteStepKind.DUPLICATED: "#ef6c00",
    RouteStepKind.BRIDGE: "#d50000",
}


def render_route_optimization_png(
    comparison: ForcedRouteOptimizationComparison,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    """Render both valid routes and Fourier frames as one atomic artifact."""

    if not isinstance(comparison, ForcedRouteOptimizationComparison):
        raise DomainValidationError("route optimization comparison is required")
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator is required")
    baseline = comparison.baseline
    improved = comparison.improved
    if (
        baseline.routing.status is not ForcedRouteStatus.READY
        or improved.routing.status is not ForcedRouteStatus.READY
        or baseline.timeline is None
        or improved.timeline is None
        or baseline.routing.metrics is None
        or improved.routing.metrics is None
    ):
        raise DomainValidationError("route optimization comparison requires two ready routes")

    figure = Figure(figsize=(13.0, 9.0), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2)
    _draw_route(axes[0, 0], baseline)
    axes[0, 0].set_title(translator.text("route_optimization.baseline"))
    _draw_route(axes[0, 1], improved)
    axes[0, 1].set_title(translator.text("route_optimization.improved"))
    draw_frame(axes[1, 0], baseline.timeline.snapshot(), translator)
    draw_frame(axes[1, 1], improved.timeline.snapshot(), translator)
    axes[1, 0].set_title(translator.text("route_optimization.baseline_frame"))
    axes[1, 1].set_title(translator.text("route_optimization.improved_frame"))
    figure.suptitle(
        translator.text(
            "route_optimization.summary",
            baseline=baseline.routing.algorithm.value,
            improved=improved.routing.algorithm.value,
            budget=comparison.optimization_budget,
            baseline_duplicated=baseline.routing.metrics.duplicated_length,
            improved_duplicated=improved.routing.metrics.duplicated_length,
            baseline_bridges=baseline.routing.metrics.bridge_length,
            improved_bridges=improved.routing.metrics.bridge_length,
            baseline_bridge_count=baseline.routing.metrics.bridge_steps,
            improved_bridge_count=improved.routing.metrics.bridge_steps,
            baseline_added=baseline.routing.metrics.added_length,
            improved_added=improved.routing.metrics.added_length,
            delta=comparison.added_length_delta,
            baseline_seconds=comparison.baseline_routing_seconds,
            improved_seconds=comparison.improved_routing_seconds,
        )
    )
    encoded = BytesIO()
    cast(Any, canvas).print_png(encoded)
    return atomic_publish_bytes(output, encoded.getvalue(), suffix=".png", overwrite=overwrite)


def _draw_route(axis: Any, result: LocalForcedRouteResult) -> None:
    route = result.routing
    curve = route.curve
    assert curve is not None
    for kind in RouteStepKind:
        segments = [
            (
                (curve.points[index].x, curve.points[index].y),
                (
                    curve.points[(index + 1) % len(curve.points)].x,
                    curve.points[(index + 1) % len(curve.points)].y,
                ),
            )
            for index, step in enumerate(route.steps)
            if step.kind is kind
        ]
        if segments:
            axis.add_collection(
                LineCollection(
                    segments,
                    colors=_COLORS[kind],
                    linewidths=2.4 if kind is RouteStepKind.BRIDGE else 1.7,
                    linestyles="--" if kind is RouteStepKind.BRIDGE else "-",
                )
            )
    axis.autoscale()
    axis.set_aspect("equal", adjustable="box")
    axis.grid(alpha=0.2)
