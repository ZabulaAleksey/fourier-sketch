"""FS-028 visual comparison of uniform and adaptive sampling."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, cast

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from fourier_sketch.application.adaptive_sampling import AdaptiveSamplingComparison
from fourier_sketch.application.exporting import atomic_publish_bytes
from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.math import CurveSpacingMetrics
from fourier_sketch.presentation import Translator

from .matplotlib_epicycles import draw_frame


def render_adaptive_sampling_png(
    comparison: AdaptiveSamplingComparison,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    """Render two sampled geometries and matching current frames atomically."""

    if not isinstance(comparison, AdaptiveSamplingComparison):
        raise DomainValidationError("adaptive sampling comparison is required")
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator is required")
    figure = Figure(figsize=(12.0, 9.0), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2)
    _draw_samples(axes[0, 0], comparison.uniform_sampled, "#2a9d8f")
    axes[0, 0].set_title(translator.text("adaptive.uniform_samples"))
    _draw_samples(axes[0, 1], comparison.adaptive.curve, "#e76f51")
    axes[0, 1].set_title(translator.text("adaptive.weighted_samples"))
    draw_frame(axes[1, 0], comparison.uniform_timeline.snapshot(), translator)
    axes[1, 0].set_title(translator.text("adaptive.uniform_frame"))
    draw_frame(axes[1, 1], comparison.adaptive_timeline.snapshot(), translator)
    axes[1, 1].set_title(translator.text("adaptive.weighted_frame"))
    curvatures = comparison.adaptive.vertex_curvatures
    densities = comparison.adaptive.segment_densities
    figure.suptitle(
        translator.text(
            "adaptive.summary",
            algorithm=comparison.adaptive.algorithm,
            policy=comparison.adaptive.policy,
            weight=comparison.adaptive.curvature_weight,
            minimum_curvature=min(curvatures),
            maximum_curvature=max(curvatures),
            minimum_density=min(densities),
            maximum_density=max(densities),
            uniform_cv=_spacing_cv(comparison.uniform_spacing),
            adaptive_cv=_spacing_cv(comparison.adaptive_spacing),
            sampled_rmse=comparison.sampled_metrics.rmse,
            uniform_rmse=comparison.uniform_reconstruction_metrics.rmse,
            adaptive_rmse=comparison.adaptive_reconstruction_metrics.rmse,
        )
    )
    encoded = BytesIO()
    cast(Any, canvas).print_png(encoded)
    return atomic_publish_bytes(output, encoded.getvalue(), suffix=".png", overwrite=overwrite)


def _draw_samples(axis: Any, curve: Curve, color: str) -> None:
    points = curve.points + ((curve.start,) if curve.closed else ())
    x_values = tuple(point.x for point in points)
    y_values = tuple(point.y for point in points)
    axis.plot(x_values, y_values, color=color, linewidth=1.0)
    scatter_x = x_values[:-1] if curve.closed else x_values
    scatter_y = y_values[:-1] if curve.closed else y_values
    axis.scatter(scatter_x, scatter_y, color=color, s=10)
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True, linewidth=0.4, alpha=0.3)


def _spacing_cv(metrics: CurveSpacingMetrics | None) -> str:
    if metrics is None:
        return "n/a"
    return f"{metrics.coefficient_of_variation:.6g}"
