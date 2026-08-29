"""Matplotlib/Agg pen-up diagnostic for FS-016 piecewise components."""

import os
import tempfile
from pathlib import Path
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.application.piecewise_skeleton import LocalPiecewiseResult
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.presentation import Translator
from fourier_sketch.routing import PiecewiseBuildStatus

_SEGMENT_COLORS = ("#1565c0", "#ef6c00", "#2e7d32", "#6a1b9a", "#00838f")


def draw_piecewise_overlay(
    figure: Figure,
    axes: tuple[Axes, Axes],
    result: LocalPiecewiseResult,
    translator: Translator,
) -> None:
    """Draw source skeleton and every curve segment as a separate artist."""
    if not isinstance(figure, Figure) or not isinstance(result, LocalPiecewiseResult):
        raise DomainValidationError("piecewise overlay requires typed figure and result")
    if not isinstance(axes, tuple) or len(axes) != 2 or any(
        not isinstance(axis, Axes) for axis in axes
    ):
        raise DomainValidationError("piecewise overlay requires exactly two axes")
    if not isinstance(translator, Translator):
        raise DomainValidationError("piecewise overlay requires a translator")

    skeleton_axis, curve_axis = axes
    raster = result.skeleton_graph.skeleton.skeletonization.skeleton
    array = np.frombuffer(raster.pixels, dtype=np.uint8).reshape(raster.height, raster.width)
    skeleton_axis.clear()
    skeleton_axis.imshow(array, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    skeleton_axis.set_title(translator.text("piecewise.panel.skeleton"))
    skeleton_axis.set_axis_off()

    curve_axis.clear()
    conversion = result.conversion
    if conversion.status is PiecewiseBuildStatus.READY:
        for index, segment in enumerate(conversion.segments):
            points = segment.curve.points
            color = _SEGMENT_COLORS[index % len(_SEGMENT_COLORS)]
            if len(points) == 1:
                curve_axis.scatter([points[0].x], [points[0].y], color=color, s=42)
            else:
                plotted = (*points, points[0]) if segment.curve.closed else points
                curve_axis.plot(
                    [point.x for point in plotted],
                    [point.y for point in plotted],
                    color=color,
                    linewidth=2.2,
                    label=translator.text(
                        "piecewise.segment.label",
                        component=segment.provenance.component_id,
                    ),
                )
        if curve_axis.lines:
            curve_axis.legend(loc="upper right", fontsize="x-small")
    else:
        curve_axis.text(
            0.5,
            0.5,
            translator.text(f"piecewise.status.{conversion.status.value}"),
            ha="center",
            va="center",
            transform=curve_axis.transAxes,
            wrap=True,
        )
    curve_axis.set_aspect("equal", adjustable="box")
    curve_axis.set_title(translator.text("piecewise.panel.curves"))
    curve_axis.set_xlabel(translator.text("axis.x"))
    curve_axis.set_ylabel(translator.text("axis.y"))
    curve_axis.grid(alpha=0.2)

    segment_count = len(conversion.segments)
    boundary_count = max(0, segment_count - 1)
    figure.suptitle(translator.text("piecewise.preview.title"))
    figure.text(
        0.5,
        0.035,
        translator.text(
            "piecewise.preview.summary",
            status=conversion.status.value,
            segments=segment_count,
            boundaries=boundary_count,
        ),
        ha="center",
    )


def render_piecewise_overlay_png(
    result: LocalPiecewiseResult,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    """Render and atomically publish one pen-up diagnostic PNG."""
    if not isinstance(result, LocalPiecewiseResult):
        raise DomainValidationError("piecewise PNG requires a typed result")
    if not isinstance(output, Path):
        raise DomainValidationError("piecewise output must be a pathlib.Path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("piecewise overlay output must use .png")
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise DomainValidationError("piecewise dpi must be between 72 and 600")
    if type(overwrite) is not bool or not output.parent.is_dir():
        raise DomainValidationError("piecewise output options are invalid")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.", suffix=".tmp", dir=output.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        figure = Figure(figsize=(11.0, 5.1), dpi=dpi)
        canvas = FigureCanvasAgg(figure)
        axes_array = figure.subplots(1, 2)
        axes = tuple(cast(Axes, axis) for axis in np.asarray(axes_array, dtype=object).flat)
        draw_piecewise_overlay(figure, cast(tuple[Axes, Axes], axes), result, translator)
        figure.subplots_adjust(left=0.06, right=0.96, bottom=0.16, top=0.84, wspace=0.22)
        cast(Any, canvas).print_png(temporary_path)
        figure.clear()
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty piecewise overlay")
        if overwrite:
            os.replace(temporary_path, output)
            temporary_path = None
        else:
            os.link(temporary_path, output)
        return output
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
