"""FS-017 forced-route provenance and Fourier diagnostic renderer."""

import os
import tempfile
from pathlib import Path
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from fourier_sketch.application.forced_route import LocalForcedRouteResult
from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.presentation import Translator
from fourier_sketch.routing import ForcedRouteStatus, RouteStepKind

from .matplotlib_epicycles import draw_frame

_COLORS = {
    RouteStepKind.ORIGINAL: "#1565c0",
    RouteStepKind.DUPLICATED: "#ef6c00",
    RouteStepKind.BRIDGE: "#d50000",
}


def draw_forced_route_overlay(
    figure: Figure,
    axes: tuple[Axes, Axes],
    result: LocalForcedRouteResult,
    translator: Translator,
) -> None:
    if not isinstance(figure, Figure) or not isinstance(result, LocalForcedRouteResult):
        raise DomainValidationError("forced route overlay requires typed figure and result")
    if not isinstance(axes, tuple) or len(axes) != 2 or any(
        not isinstance(axis, Axes) for axis in axes
    ):
        raise DomainValidationError("forced route overlay requires exactly two axes")
    if not isinstance(translator, Translator):
        raise DomainValidationError("forced route overlay requires a translator")
    route_axis, fourier_axis = axes
    route_axis.clear()
    routing = result.routing
    if routing.status is not ForcedRouteStatus.READY:
        route_axis.text(
            0.5,
            0.5,
            translator.text(f"forced_route.status.{routing.status.value}"),
            ha="center",
            va="center",
            transform=route_axis.transAxes,
        )
        fourier_axis.clear()
        fourier_axis.set_axis_off()
        return
    transform = routing.curve
    assert transform is not None and routing.metrics is not None and result.timeline is not None
    for kind in RouteStepKind:
        segments = [
            ((transform.points[index].x, transform.points[index].y),
             (transform.points[(index + 1) % len(transform.points)].x,
              transform.points[(index + 1) % len(transform.points)].y))
            for index, step in enumerate(routing.steps)
            if step.kind is kind
        ]
        if segments:
            route_axis.add_collection(
                LineCollection(
                    segments,
                    colors=_COLORS[kind],
                    linewidths=2.4 if kind is RouteStepKind.BRIDGE else 1.7,
                    linestyles="--" if kind is RouteStepKind.BRIDGE else "-",
                    label=translator.text(f"forced_route.kind.{kind.value}"),
                )
            )
    route_axis.autoscale()
    route_axis.set_aspect("equal", adjustable="box")
    route_axis.grid(alpha=0.2)
    route_axis.set_title(translator.text("forced_route.panel.route"))
    route_axis.legend(loc="upper right", fontsize="x-small")
    draw_frame(fourier_axis, result.timeline.snapshot(), translator)
    figure.suptitle(translator.text("forced_route.preview.title"))
    figure.text(
        0.5,
        0.025,
        translator.text(
            "forced_route.preview.summary",
            original=routing.metrics.original_steps,
            duplicated=routing.metrics.duplicated_steps,
            bridges=routing.metrics.bridge_steps,
            added=routing.metrics.added_length,
        ),
        ha="center",
    )


def render_forced_route_overlay_png(
    result: LocalForcedRouteResult,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    if not isinstance(result, LocalForcedRouteResult) or not isinstance(output, Path):
        raise DomainValidationError("forced route PNG requires typed result and path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png" or type(dpi) is not int or not 72 <= dpi <= 600:
        raise DomainValidationError("forced route PNG options are invalid")
    if type(overwrite) is not bool or not output.parent.is_dir():
        raise DomainValidationError("forced route output options are invalid")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.", suffix=".tmp", dir=output.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        figure = Figure(figsize=(12.0, 5.5), dpi=dpi)
        canvas = FigureCanvasAgg(figure)
        axes_array = figure.subplots(1, 2)
        axes = tuple(cast(Axes, axis) for axis in np.asarray(axes_array, dtype=object).flat)
        draw_forced_route_overlay(figure, cast(tuple[Axes, Axes], axes), result, translator)
        figure.subplots_adjust(left=0.06, right=0.97, bottom=0.15, top=0.84, wspace=0.22)
        cast(Any, canvas).print_png(temporary_path)
        figure.clear()
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty forced route overlay")
        if overwrite:
            os.replace(temporary_path, output)
            temporary_path = None
        else:
            os.link(temporary_path, output)
        return output
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
