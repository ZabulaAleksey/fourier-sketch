"""Matplotlib/Agg topology overlay for the FS-015 skeleton graph."""

import os
import tempfile
import textwrap
from pathlib import Path
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.application.skeleton_graph import LocalSkeletonGraphResult
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import RasterImage
from fourier_sketch.imaging.skeleton_graph_model import SkeletonNodeKind
from fourier_sketch.presentation import Translator

_COMPONENT_COLORS = ("#1565c0", "#ef6c00", "#2e7d32", "#6a1b9a", "#00838f")
_NODE_STYLES = {
    SkeletonNodeKind.ENDPOINT: ("o", "#00c853"),
    SkeletonNodeKind.JUNCTION_REGION: ("X", "#d50000"),
    SkeletonNodeKind.LOOP_ANCHOR: ("s", "#aa00ff"),
    SkeletonNodeKind.ISOLATED: ("D", "#ffab00"),
}


def draw_skeleton_graph_overlay(
    figure: Figure,
    axes: tuple[Axes, Axes],
    result: LocalSkeletonGraphResult,
    translator: Translator,
) -> None:
    """Draw source skeleton and component topology without selecting a route."""
    if not isinstance(figure, Figure) or not isinstance(result, LocalSkeletonGraphResult):
        raise DomainValidationError("skeleton graph overlay requires typed figure and result")
    if (
        not isinstance(axes, tuple)
        or len(axes) != 2
        or any(not isinstance(axis, Axes) for axis in axes)
    ):
        raise DomainValidationError("skeleton graph overlay requires exactly two axes")
    if not isinstance(translator, Translator):
        raise DomainValidationError("skeleton graph overlay requires a translator")

    skeleton_axis, graph_axis = axes
    raster = result.skeleton.skeletonization.skeleton
    array = _raster_array(raster)
    skeleton_axis.clear()
    skeleton_axis.imshow(array, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    skeleton_axis.set_title(
        textwrap.fill(translator.text("skeleton_graph.panel.skeleton"), width=42),
        fontsize=10,
    )
    skeleton_axis.set_axis_off()

    graph_axis.clear()
    graph_axis.imshow(array, cmap="gray", vmin=0, vmax=255, interpolation="nearest", alpha=0.25)
    for edge in result.graph.edges:
        points = (edge.start_contact, *edge.interior_pixels, edge.end_contact)
        graph_axis.plot(
            [point.column for point in points],
            [point.row for point in points],
            color=_COMPONENT_COLORS[edge.component_id % len(_COMPONENT_COLORS)],
            linewidth=2.2,
            alpha=0.9,
        )
    for kind, (marker, color) in _NODE_STYLES.items():
        nodes = [node for node in result.graph.nodes if node.kind is kind]
        if nodes:
            graph_axis.scatter(
                [node.anchor.column for node in nodes],
                [node.anchor.row for node in nodes],
                marker=marker,
                c=color,
                s=55,
                edgecolors="white",
                linewidths=0.7,
                label=translator.text(f"skeleton_graph.node.{kind.value}"),
                zorder=3,
            )
    graph_axis.set_title(
        textwrap.fill(translator.text("skeleton_graph.panel.topology"), width=42),
        fontsize=10,
    )
    graph_axis.set_axis_off()
    if result.graph.nodes:
        graph_axis.legend(loc="upper right", fontsize="x-small")
    figure.suptitle(
        translator.text(
            "skeleton_graph.preview.title",
            policy=result.graph.adjacency_policy,
        )
    )
    figure.text(
        0.5,
        0.035,
        translator.text(
            "skeleton_graph.preview.summary",
            components=len(result.graph.components),
            nodes=len(result.graph.nodes),
            edges=len(result.graph.edges),
            endpoints=result.graph.endpoint_count,
            junctions=result.graph.junction_count,
            loops=result.graph.loop_count,
        ),
        ha="center",
    )


def render_skeleton_graph_overlay_png(
    result: LocalSkeletonGraphResult,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    """Render and atomically publish one graph diagnostic PNG."""
    if not isinstance(result, LocalSkeletonGraphResult):
        raise DomainValidationError("skeleton graph PNG requires a typed result")
    if not isinstance(output, Path):
        raise DomainValidationError("skeleton graph output must be a pathlib.Path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("skeleton graph overlay output must use .png")
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise DomainValidationError("skeleton graph dpi must be between 72 and 600")
    if type(overwrite) is not bool or not output.parent.is_dir():
        raise DomainValidationError("skeleton graph output options are invalid")
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
        draw_skeleton_graph_overlay(
            figure, cast(tuple[Axes, Axes], axes), result, translator
        )
        figure.subplots_adjust(left=0.04, right=0.96, bottom=0.14, top=0.82, wspace=0.18)
        cast(Any, canvas).print_png(temporary_path)
        figure.clear()
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty skeleton graph overlay")
        if overwrite:
            os.replace(temporary_path, output)
            temporary_path = None
        else:
            os.link(temporary_path, output)
        return output
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _raster_array(raster: RasterImage) -> np.ndarray:
    return np.frombuffer(raster.pixels, dtype=np.uint8).reshape(raster.height, raster.width)
