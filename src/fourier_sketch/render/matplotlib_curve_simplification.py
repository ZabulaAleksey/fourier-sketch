"""FS-027 visual comparison of original and simplified curves."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, cast

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from fourier_sketch.application.curve_simplification import CurveSimplificationComparison
from fourier_sketch.application.exporting import atomic_publish_bytes
from fourier_sketch.domain import Curve, DomainValidationError
from fourier_sketch.presentation import Translator

from .matplotlib_epicycles import draw_frame


def render_curve_simplification_png(
    comparison: CurveSimplificationComparison,
    output: Path,
    translator: Translator,
    *,
    overwrite: bool = False,
) -> Path:
    """Render geometry and matching current frames as one atomic PNG."""
    if not isinstance(comparison, CurveSimplificationComparison):
        raise DomainValidationError("curve simplification comparison is required")
    if not isinstance(translator, Translator):
        raise DomainValidationError("translator is required")
    figure = Figure(figsize=(12.0, 9.0), layout="constrained")
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2)
    _draw_curve(axes[0, 0], comparison.simplification.source, "#2a9d8f")
    axes[0, 0].set_title(translator.text("simplification.original"))
    _draw_curve(axes[0, 1], comparison.simplification.curve, "#e76f51")
    axes[0, 1].set_title(translator.text("simplification.simplified"))
    draw_frame(axes[1, 0], comparison.baseline_timeline.snapshot(), translator)
    axes[1, 0].set_title(translator.text("simplification.baseline_frame"))
    draw_frame(axes[1, 1], comparison.simplified_timeline.snapshot(), translator)
    axes[1, 1].set_title(translator.text("simplification.simplified_frame"))
    figure.suptitle(
        translator.text(
            "simplification.summary",
            tolerance=comparison.simplification.tolerance,
            algorithm=comparison.simplification.algorithm,
            source_points=comparison.simplification.metrics.source_point_count,
            simplified_points=comparison.simplification.metrics.simplified_point_count,
            maximum_deviation=comparison.simplification.metrics.maximum_segment_deviation,
            rms_deviation=comparison.simplification.metrics.rms_segment_deviation,
            length_delta=comparison.simplification.metrics.absolute_length_delta,
            sampled_rmse=comparison.sampled_metrics.rmse,
            baseline_rmse=comparison.baseline_reconstruction_metrics.rmse,
            simplified_rmse=comparison.simplified_reconstruction_metrics.rmse,
        )
    )
    encoded = BytesIO()
    cast(Any, canvas).print_png(encoded)
    return atomic_publish_bytes(output, encoded.getvalue(), suffix=".png", overwrite=overwrite)


def _draw_curve(axis: Any, curve: Curve, color: str) -> None:
    points = curve.points + ((curve.start,) if curve.closed else ())
    axis.plot(tuple(point.x for point in points), tuple(point.y for point in points), color=color)
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True, linewidth=0.4, alpha=0.3)
