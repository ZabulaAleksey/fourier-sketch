"""Matplotlib/Agg preview adapter for an FS-014 skeleton result."""

import os
import tempfile
from pathlib import Path
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from fourier_sketch.application.local_paths import validate_local_path
from fourier_sketch.application.skeletonization import LocalSkeletonResult
from fourier_sketch.domain import DomainValidationError
from fourier_sketch.imaging import RasterImage
from fourier_sketch.presentation import Translator


def draw_skeleton_preview(
    figure: Figure,
    axes: tuple[Axes, Axes],
    result: LocalSkeletonResult,
    translator: Translator,
) -> None:
    """Draw source binary and actual skeleton without deriving graph topology."""
    if not isinstance(figure, Figure) or not isinstance(result, LocalSkeletonResult):
        raise DomainValidationError("skeleton preview requires typed figure and result")
    if (
        not isinstance(axes, tuple)
        or len(axes) != 2
        or any(not isinstance(axis, Axes) for axis in axes)
    ):
        raise DomainValidationError("skeleton preview requires exactly two axes")
    if not isinstance(translator, Translator):
        raise DomainValidationError("skeleton preview requires a translator")

    source_axes, skeleton_axes = axes
    for axis, raster, title_key in (
        (source_axes, result.preprocessing.binary, "skeleton.panel.source"),
        (skeleton_axes, result.skeletonization.skeleton, "skeleton.panel.result"),
    ):
        axis.clear()
        axis.imshow(_raster_array(raster), cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        axis.set_title(translator.text(title_key))
        axis.set_axis_off()
    figure.suptitle(
        translator.text(
            "skeleton.preview.title",
            algorithm=result.skeletonization.algorithm.value,
            backend=result.skeletonization.backend,
        )
    )
    figure.text(
        0.5,
        0.04,
        translator.text(
            "skeleton.preview.summary",
            source=result.skeletonization.source_foreground_pixels,
            skeleton=result.skeletonization.skeleton_pixel_count,
        ),
        ha="center",
    )


def render_skeleton_preview_png(
    result: LocalSkeletonResult,
    output: Path,
    translator: Translator,
    *,
    dpi: int = 120,
    overwrite: bool = False,
) -> Path:
    """Render a two-panel preview and publish it atomically without implicit overwrite."""
    if not isinstance(result, LocalSkeletonResult):
        raise DomainValidationError("skeleton PNG requires a typed result")
    if not isinstance(output, Path):
        raise DomainValidationError("skeleton preview output must be a pathlib.Path")
    output = validate_local_path(output, field_name="output")
    if output.suffix.lower() != ".png":
        raise DomainValidationError("skeleton preview output must use .png")
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise DomainValidationError("skeleton preview dpi must be between 72 and 600")
    if type(overwrite) is not bool or not output.parent.is_dir():
        raise DomainValidationError("skeleton preview output options are invalid")
    if output.exists() and not overwrite:
        raise FileExistsError(output.name)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        figure = Figure(figsize=(9.0, 4.8), dpi=dpi)
        canvas = FigureCanvasAgg(figure)
        axes_array = figure.subplots(1, 2)
        axes = tuple(cast(Axes, axis) for axis in np.asarray(axes_array, dtype=object).flat)
        draw_skeleton_preview(figure, cast(tuple[Axes, Axes], axes), result, translator)
        figure.subplots_adjust(left=0.04, right=0.96, bottom=0.13, top=0.86, wspace=0.10)
        cast(Any, canvas).print_png(temporary_path)
        figure.clear()
        if temporary_path.stat().st_size == 0:
            raise OSError("renderer produced an empty skeleton preview")
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
